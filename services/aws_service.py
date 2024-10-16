import json
import logging
import sys
import uuid

import boto3
import os
import requests
from botocore.exceptions import NoCredentialsError, ClientError

from dotenv import load_dotenv, find_dotenv

from requests_aws4auth import AWS4Auth

from utils.enum.role import AppRole
from utils.exceptions import ItemNotFoundError
from utils.time import get_current_hour, get_month_dates

from utils.custom import handle_highlight_open_search
from utils.url import is_url

load_dotenv(find_dotenv())

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_PRIVATE_BUCKET_NAME = os.getenv('AWS_PRIVATE_BUCKET_NAME')
AWS_PUBLIC_BUCKET_NAME = os.getenv('AWS_PUBLIC_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')
MESSAGE_TABLE_NAME = os.getenv('MESSAGE_TABLE_NAME')
TEXT_COUNT_CACHE_TABLE_NAME = os.getenv('TEXT_COUNT_CACHE_TABLE_NAME')
IMAGE_COUNT_CACHE_TABLE_NAME = os.getenv('IMAGE_COUNT_CACHE_TABLE_NAME')
COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
COGNITO_ISSUER = f'https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}'
OPENSEARCH_DOMAIN_ENDPOINT = os.getenv('OPENSEARCH_DOMAIN_ENDPOINT')
LAMBDA_FUNCTION_NAME = os.getenv('LAMBDA_FUNCTION_NAME')
SES_ASK_PARENT_APPROVE_TEMPLATE_NAME = os.getenv('SES_ASK_PARENT_APPROVE_TEMPLATE_NAME')
SES_EMAIL_SOURCE = os.getenv('SES_EMAIL_SOURCE')
SES_CONFIGURATION_SET = os.getenv('SES_CONFIGURATION_SET')
PROMPT_VERSION = os.getenv("PROMPT_VERSION")
PROMPT_BUCKET_NAME = os.getenv("PROMPT_BUCKET_NAME")
RETRIES_TO_ACCESS_OPENSEARCH = 3

session = boto3.Session(region_name=AWS_REGION)
credentials = session.get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    AWS_REGION,
    'es',
    session_token=credentials.token
)


def regenerate_session():
    global session, credentials, awsauth
    session = boto3.Session(region_name=AWS_REGION)
    credentials = session.get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        AWS_REGION,
        'es',
        session_token=credentials.token
    )


def generate_presigned_url(object_name, expiration=6800, bucket_name=AWS_PRIVATE_BUCKET_NAME, action='put_object'):
    """Generate a pre-signed URL for uploading a photo or message to S3"""
    s3_client = session.client('s3')

    try:
        presigned_url = s3_client.generate_presigned_url(
            action,
            Params={
                'Bucket': bucket_name,
                'Key': object_name
                # 'ContentType': "image/jpeg"
            },
            ExpiresIn=expiration
        )
        return presigned_url

    except NoCredentialsError:
        logging.info("AWS credentials not found.")
        return None


def upload_image_to_s3(image_data, presigned_url):
    res = requests.put(presigned_url, data=image_data)
    return res


def save_message_history_to_s3(message_history, presigned_url):
    """Save message history to AWS S3 bucket. Note that the function can only be used if the
    bucket is publicly available.

    Args:
        message_history (List[Dict]):  Message history
        presigned_url (str): URL to the json file that stores the message history

    Returns:
        Response: Response of the upload request.
    """
    res = requests.put(
        presigned_url,
        data=json.dumps(message_history)
    )
    return res


def get_image_from_s3(image_key):
    """Retrieve image from a private S3 bucket.
    The strategy is to request S3 bucket to generate a presigned URL, then make a get request from the URL."""
    # Check if image_key is a URL, this is experimental for dev environment.
    if is_url(image_key):
        presigned_url = image_key
    else:
        presigned_url = generate_presigned_url(image_key, action='get_object')
    res = requests.get(presigned_url)
    if res.status_code == 200:
        return res.content
    else:
        raise ConnectionError(f"Cannot retrieve image. Status code: {res.status_code} - Details: {res.content}")


def get_system_prompt(agent_name: str, user_age: int, username: str):
    agent_name = agent_name.lower()
    if user_age <= 11:
        age_range = '6-11'
    elif user_age <= 15:
        age_range = '12-15'
    else:
        age_range = '16-18'

    s3_client = session.client('s3')
    try:
        agent_key = '{}/agent/general/{}.md'.format(PROMPT_VERSION, agent_name)
        agent_prompt_response = s3_client.get_object(
            Bucket=PROMPT_BUCKET_NAME,
            Key=agent_key
        )
        if 'Body' in agent_prompt_response:
            agent_prompt = agent_prompt_response.get('Body').read().decode("utf-8")
        else:
            raise ItemNotFoundError("Customized agent prompt not found")

        age_key = '{}/age/{}.md'.format(PROMPT_VERSION, age_range)
        age_prompt_response = s3_client.get_object(
            Bucket=PROMPT_BUCKET_NAME,
            Key=age_key
        )
        if 'Body' in age_prompt_response:
            age_prompt = age_prompt_response.get('Body').read().decode("utf-8")
            age_prompt = age_prompt.format(age=user_age, name=username)
        else:
            raise ItemNotFoundError("Customized age prompt not found")

        full_system_prompt = agent_prompt + '\n\n' + age_prompt
        return full_system_prompt
    except ClientError as e:
        raise Exception(str(e))


def get_message_history(message_url):
    """
    Get Message History given the path to AWS S3 file

    Args:
        message_url (str): Path to the json file on AWS S3 bucket which stores the message history

    Returns:
        Dict: message history
    """
    try:
        res = requests.get(message_url)
        json_data = res.json()
        return json_data
    except Exception as e:
        logging.info(f"Error retrieving JSON content: {e}")
        return None


def register_image(image_data: bytes, id: int, des: str = "chat_history") -> object:
    """
    Register an image by assigning a URL to the image, then upload the image to S3 bucket.

    Args:
        image_data (bytes): Image data
        id (int): Depends on the dest:
            If des = "user_avatar", this will be user_id.
            If des = "parent", this will be parent_id
            If des = "app_report", this won't be considered.
            If des = "chat_history", this will be message_id.
        des (str): Define how the key format is generated.

    Returns:
        image_url (str): The link to assigned image url
        image_size (int): Image size
    """
    if des == "chat_history":
        image_key = f'chat_history/{id}/images/{uuid.uuid4()}.jpg'
        bucket_name = AWS_PUBLIC_BUCKET_NAME
    elif des == "app_report":
        image_key = f'reports/{uuid.uuid4()}.jpg'
        bucket_name = AWS_PUBLIC_BUCKET_NAME
    elif des == "user_avatar":
        image_key = f'avatar/user/{id}/{uuid.uuid4()}.jpg'
        bucket_name = AWS_PUBLIC_BUCKET_NAME
    elif des == "parent_avatar":
        image_key = f'avatar/parent/{id}/{uuid.uuid4()}.jpg'
        bucket_name = AWS_PUBLIC_BUCKET_NAME
    else:
        raise ValueError("Unavailable `dest` type, {} found".format(des))
    assigned_url = generate_presigned_url(object_name=image_key, bucket_name=bucket_name)
    upload_res = upload_image_to_s3(image_data, assigned_url)
    if upload_res.status_code == 200:
        image_url = f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{image_key}"
        image_size = sys.getsizeof(image_data)
        return image_url, image_size
    else:
        raise ConnectionError("Fail to generate or upload image")


def delete_message_history(message_url):
    """
    Delete message history given the path to AWS S3 file
    
    Args:
        message_url (str): Path to the json file on AWS S3 bucket which stores the message history
    """
    try:
        res = requests.delete(message_url)
        logging.info(res.json())
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logging.info(f"Error while delete message history on S3: {e}")
        return None


def delete_image(message_url):
    """Delete images given the path to AWS S3. The behavior is similar to delete images

    Args:
        message_url (str): Path to the json file on AWS s3 bucket which stores the images
    """
    try:
        return delete_message_history(message_url)
    except Exception as e:
        logging.info(f"Error while delete image on S3: {e}")
        return None


def get_cognito_public_keys():
    response = requests.get(f'{COGNITO_ISSUER}/.well-known/jwks.json')
    json_response = response.json()
    if 'keys' not in json_response:
        raise AttributeError("Connection to third-party services is incorrect.")
    return response.json()['keys']


def filter_json_response(json_response):
    """Convert JSON response queried from DynamoDB to suitable format.

    Args:
        json_response (Dict): JSON response queried from DynamoDB

    Returns:
        _type_: _description_
    """
    items = []
    for item in json_response["Items"]:
        filtered_item = {
            "content": item["content"]["S"],
            "history_message_id": int(item["history_message_id"]["N"]),
            "role": item["role"]["S"],
            "timestamp": item["timestamp"]["S"],
            "links": item["links"]["SS"] if "links" in item else [],
            "next_questions": item["next_questions"]["SS"] if "next_questions" in item else []
        }
        items.append(filtered_item)
    filtered_json_response = {
        "data": items[::-1],
        "count": json_response.get("Count"),
        "last_timestamp": json_response["LastEvaluatedKey"]["timestamp"][
            "S"] if "LastEvaluatedKey" in json_response else None
    }
    return filtered_json_response


def save_message_record(history_message_id, role, content, timestamp,
                        links=None, next_questions=None, **kwargs):
    """Save message history to Amazon DynamoDB and Amazon OpenSearch.

    Args:
        history_message_id (int): The ID of history message conversation
        role (str): Either user, assistant, image, and user_image for OpenAI GPT API
        content (str): Content of the message
        links (List[str]): List of links for references
        next_questions (List[str]): List of possible next questions
        timestamp (str): Time that the message has been generated

    Return:
        item (Dict): Input item
    """
    try:
        item = store_message_record_to_dynamodb(content, history_message_id, links, next_questions, role, timestamp)
        store_message_record_to_opensearch(content, history_message_id, links, next_questions, role, timestamp)
        return item
    except ClientError as e:
        logging.info("An error occurred during insertion to DynamoDB: {}".format(e))
        raise e


def store_message_record_to_dynamodb(content, history_message_id, links, next_questions, role, timestamp):
    dynamodb_client = session.client('dynamodb')
    item = {
        "history_message_id": {"N": str(history_message_id)},
        "timestamp": {"S": timestamp},
        "role": {"S": role},
        "content": {"S": content}
    }
    if links:
        item.update({"links": {"SS": links}})
    if next_questions:
        item.update({"next_questions": {"SS": next_questions}})
    dynamodb_client.put_item(TableName=MESSAGE_TABLE_NAME, Item=item)
    return item


def store_message_record_to_opensearch(content, history_message_id, links, next_questions, role, timestamp):
    item = {
        "history_message_id": history_message_id,
        "timestamp": timestamp,
        "content": content,
        "role": role
    }
    url = OPENSEARCH_DOMAIN_ENDPOINT + '/' + str(history_message_id) + '/' + '_doc' + '/'
    headers = {"Content-Type": "application/json"}
    for i in range(RETRIES_TO_ACCESS_OPENSEARCH):
        response = requests.put(url + timestamp, auth=awsauth, json=item, headers=headers)
        if response.status_code == 403:
            regenerate_session()
        elif response.status_code == 200:
            return None


def query_message_record(history_message_id, q):
    url = OPENSEARCH_DOMAIN_ENDPOINT + '/' + str(history_message_id) + '/' + '_search' + '?sort=timestamp:desc'
    data = {
        "query": {
            "match_phrase_prefix": {
                "content": {
                    "query": q,
                    "analyzer": "simple"
                }
            }
        },
        "highlight": {
            "fields": {
                "content": {}
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    response = requests.get(url, auth=awsauth, json=data, headers=headers)
    for _ in range(RETRIES_TO_ACCESS_OPENSEARCH):
        if response.status_code == 404:
            return []
        elif response.status_code == 200:
            result = []
            for hit in response.json()["hits"]["hits"]:
                source = hit["_source"]
                # Check if highlighting exists for the content field
                if "highlight" in hit:
                    # Extract the highlighted content from the response
                    highlighted_content = hit["highlight"]["content"][0]
                    source["highlighted_content"] = highlighted_content
                result.append(source)
            for item in result:
                item['content'] = handle_highlight_open_search(item['content'], item['highlighted_content'])
            return result
        elif response.status_code == 403:
            regenerate_session()
        else:
            raise Exception(response.content.decode())


def get_message_record_from_dynamo_db(history_message_id, limit=None, last_timestamp=None, from_timestamp=None):
    """Get message history from Amazon DynamoDB.

    Args:
        history_message_id (int): The ID of history message conversation
        limit (int): Limit message from DynamoDB
        last_timestamp (datetime, optional): Last timestamp acts as the key for paging. Check boto3 query documentation
            for more details.
    """
    try:
        dynamodb_client = session.client('dynamodb')
        query = {
            "TableName": MESSAGE_TABLE_NAME,
            "KeyConditions": {
                "history_message_id": {
                    "AttributeValueList": [{"N": str(history_message_id)}],
                    "ComparisonOperator": "EQ"
                }
            },
            "ScanIndexForward": False
        }
        if limit is not None:
            query['Limit'] = limit
        if last_timestamp is not None:
            query['ExclusiveStartKey'] = {
                "history_message_id": {"N": str(history_message_id)},
                "timestamp": {"S": last_timestamp}
            }

        if from_timestamp is not None:
            query["ScanIndexForward"] = True
            query['ExclusiveStartKey'] = {
                "history_message_id": {"N": str(history_message_id)},
                "timestamp": {"S": from_timestamp}
            }

        query_result = dynamodb_client.query(**query)
        return filter_json_response(query_result)
    except ClientError as e:
        logging.info("An error occurred during query on DynamoDB: {}".format(e))
        raise e


def get_message_by_search_key_timestamp(history_message_id, limit=None, timestamp=None):
    """Get 10 previous and 10 next messages based on a provided timestamp.

    Args:
        history_message_id (int): The ID of the history message conversation.
        timestamp (str): The timestamp to find messages around.
        limit (int, optional): Limit the number of records to fetch for each direction. Default is 10.
    """

    dynamodb_client = session.client('dynamodb')
    query = {
        "TableName": MESSAGE_TABLE_NAME,
        "KeyConditions": {
            "history_message_id": {
                "AttributeValueList": [{"N": str(history_message_id)}],
                "ComparisonOperator": "EQ"
            }
        },
        "ScanIndexForward": False
    }
    if limit is not None:
        query['Limit'] = limit

    # Get 10 previous messages (older than the provided timestamp)
    query["ExclusiveStartKey"] = {
        "history_message_id": {"N": str(history_message_id)},
        "timestamp": {"S": timestamp}
    }
    prev_messages_result = dynamodb_client.query(**query)

    # Get 10 next messages (newer than the provided timestamp)
    query["ExclusiveStartKey"] = {
        "history_message_id": {"N": str(history_message_id)},
        "timestamp": {"S": timestamp}
    }
    query["ScanIndexForward"] = True  # Set to True for ascending order (oldest to newest)
    next_messages_result = dynamodb_client.query(**query)

    return {
        "prev_messages_result": filter_json_response(prev_messages_result),
        "next_messages_result": filter_json_response(next_messages_result)
    }


def delete_item_on_message_history(message_id, timestamp):
    """
    Delete a message record in the message history.

    Args:
        message_id (int): The ID of history message conversation
        timestamp (str): Timestamp of the message you would like to delete
    """
    try:
        dynamodb_client = session.client('dynamodb')
        response = dynamodb_client.delete_item(
            TableName=MESSAGE_TABLE_NAME,
            ReturnValues='ALL_OLD',
            ReturnConsumedCapacity='INDEXES',
            Key={
                "timestamp": {"S": timestamp},
                "history_message_id": {"N": str(message_id)},
            }
        )
        status_code = response['ResponseMetadata']['HTTPStatusCode']
        success = (status_code == 200) and ("Attributes" in response)
        return success
    except ClientError as e:
        logging.info("An error occurred during query on DynamoDB: {}".format(e))
        raise e


def update_text_to_text_counter(user_id: int):
    """Update text to text counter"""
    current_hour = get_current_hour().isoformat()
    try:
        dynamodb_client = session.client('dynamodb')
        response = dynamodb_client.update_item(
            TableName=TEXT_COUNT_CACHE_TABLE_NAME,
            Key={
                'user_id': {'N': str(user_id)},
                'hour': {'S': current_hour}
            },
            UpdateExpression='ADD message_count :incr',
            ExpressionAttributeValues={
                ':incr': {'N': '1'}
            },
            ReturnValues='UPDATED_NEW'
        )
        return int(response['Attributes']['message_count']['N'])
    except ClientError as e:
        logging.info("An error occurred during query on DynamoDB: {}".format(e))
        raise e


def get_text_to_text_counter(user_id: int, role: str):
    """Get text to text counter for a user"""
    if role == AppRole.PARENT:
        return 0

    current_hour = get_current_hour().isoformat()
    try:
        dynamodb_client = session.client('dynamodb')
        response = dynamodb_client.get_item(
            TableName=TEXT_COUNT_CACHE_TABLE_NAME,
            Key={
                'user_id': {'N': str(user_id)},
                'hour': {'S': current_hour}
            }
        )

        item = response.get('Item')
        if item:
            return int(item['message_count']['N'])
        else:
            return 0

    except ClientError as e:
        logging.info("An error occurred during query on DynamoDB: {}".format(e))
        raise e


def update_image_generation_counter(package_group_id: int, current_period_start):
    """Update text to text counter"""
    current_month_start = get_month_dates(current_period_start)
    try:
        dynamodb_client = session.client('dynamodb')
        response = dynamodb_client.update_item(
            TableName=IMAGE_COUNT_CACHE_TABLE_NAME,
            Key={
                'package_group_id': {'N': str(package_group_id)},
                'month_start': {'S': current_month_start.isoformat()},
            },
            UpdateExpression='ADD message_count :incr',
            ExpressionAttributeValues={
                ':incr': {'N': '1'}
            },
            ReturnValues='UPDATED_NEW'
        )

        return int(response['Attributes']['message_count']['N'])
    except ClientError as e:
        logging.info("An error occurred during query on DynamoDB: {}".format(e))
        raise e


def get_image_generation_counter(package_group_id: int, current_period_start):
    """Get text to text counter for a user"""
    current_month_start = get_month_dates(current_period_start)
    try:
        dynamodb_client = session.client('dynamodb')
        response = dynamodb_client.get_item(
            TableName=IMAGE_COUNT_CACHE_TABLE_NAME,
            Key={
                'package_group_id': {'N': str(package_group_id)},
                'month_start': {'S': current_month_start.isoformat()},
            }
        )

        item = response.get('Item')
        if item:
            return int(item['message_count']['N'])
        else:
            return 0

    except ClientError as e:
        logging.info("An error occurred during query on DynamoDB: {}".format(e))
        raise e


def admin_confirm_sign_up(username):
    client = session.client('cognito-idp')
    try:
        client.admin_confirm_sign_up(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username
        )
    except client.exceptions.UserNotFoundException as e:
        raise Exception(str(e))


def cognito_disable_user(username):
    """Disable a Cognito user"""
    client = session.client('cognito-idp')
    try:
        client.admin_disable_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username
        )
    except ClientError as e:
        raise Exception(str(e))


def cognito_delete_user(username):
    """Delete a Cognito user"""
    client = session.client('cognito-idp')
    try:
        client.admin_delete_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username
        )
    except ClientError as e:
        raise Exception(str(e))


def cognito_set_password(username, password):
    """Set a new password for the user"""
    client = session.client('cognito-idp')
    try:
        client.admin_set_user_password(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username,
            Password=password,
            Permanent=True
        )
    except ClientError as e:
        raise Exception(str(e))


def invoke_progress_tracking(history_message_id, start_time):
    """
    Invoke progress tracking evaluation from the chat history after the user leaves the chat room.
    The function asynchronously invokes an AWS Lambda function to perform evaluation.

    Args:
        history_message_id: History Message ID
        start_time: Timestamp that the user entered the room. This will be tracked from the websocket.
    """
    lambda_client = session.client('lambda')
    try:
        payload = {
            "history_message_id": history_message_id,
            "start_time": start_time
        }
        lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
    except ClientError as e:
        logging.info("Error occurred while triggering Lambda function for summarizing chats")
        raise e


def comprehend_detect_language(text: str, threshold: float = 0.2):
    """
    Detect language used in a document, using Amazon Comprehend.

    Args:
        text (str): Document
        threshold (float): Minimum score to be included as an existing language inferred from the prompt. Default is 0.2

    Returns:
        List[Languages]: The languages that are inferred from the text
    """
    comprehend_client = session.client('comprehend')
    try:
        response = comprehend_client.detect_dominant_language(Text=text)
        languages = response['Languages']
        return [lan["LanguageCode"] for lan in languages if lan["Score"] >= threshold]
    except ClientError as e:
        raise Exception(f"Could not detect languages. Details: {str(e)}")


def send_ses_email(recipient_email, template_name, template_data=None,
                   category="undefined", user_id="NULL", parent_id="NULL"):
    if template_data is None:
        template_data = {}
    ses_client = session.client('sesv2')
    try:
        response = ses_client.send_email(
            FromEmailAddress=SES_EMAIL_SOURCE,
            Destination={
                'ToAddresses': [recipient_email]
            },
            Content={
                "Template": {
                    "TemplateName": template_name,
                    "TemplateData": json.dumps(template_data)
                }
            },
            EmailTags=[
                {
                    'Name': 'category',
                    'Value': category
                },
                {
                    'Name': 'user_id',
                    'Value': str(user_id)
                },
                {
                    'Name': 'parent_id',
                    'Value': str(parent_id)
                }
            ],
            ConfigurationSetName=SES_CONFIGURATION_SET
        )
        return response
    except ClientError as e:
        raise Exception(f"Could not detect languages. Details: {str(e)}")


def send_approve_request_email(recipient_email, user_id):
    return send_ses_email(recipient_email,
                          template_name=SES_ASK_PARENT_APPROVE_TEMPLATE_NAME,
                          category="approve-request",
                          user_id=user_id)
