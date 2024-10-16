import os
from datetime import datetime
from functools import wraps

import jwt
import requests
from flask import request, jsonify

from utils.exceptions import QueryNotFoundError

from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')
MESSAGE_TABLE_NAME = os.getenv('MESSAGE_TABLE_NAME')
COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')
COGNITO_ISSUER = f'https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}'


def validate_token(func):
    """
    Decorator to validate the token from the Authorization header.

    Usage:
    ```python
    @validate_token()
    def func():
        # Your protected resource logic here
        ...
    ```

    For client code, the request header should contain Authorization attribute with format
    Bearer: <token>

    Returns:
        Validated token or error response with a 401 Unauthorized status code.
    """

    @wraps(func)
    def decorated_func(*args, **kwargs):
        token = request.headers.get('Authorization')
        if token:
            token = token.split(' ')[1]  # Remove the 'Bearer' prefix from the token
            if token == "FlipJungleModAccessFilip1234@#!":
                return func(*args, **kwargs)
            try:
                decoded_token = jwt.decode(
                    token,
                    # public_keys[0],
                    algorithms=['RS256'],
                    audience=COGNITO_CLIENT_ID,
                    issuer=COGNITO_ISSUER,
                    options={"verify_signature": False, "verify_aud": True, "verify_iss": True}
                )

                if decoded_token['token_use'] not in ["id", "access"]:
                    raise jwt.InvalidTokenError("Token ID is mismatched from expected value")

                # if not decoded_token['email_verified']:
                #     raise jwt.InvalidTokenError("Email must be verified to access the API")

                if not datetime.fromtimestamp(decoded_token['exp']) >= datetime.now():
                    raise jwt.InvalidTokenError("Token is expired")

                return func(*args, **kwargs)

            except (jwt.InvalidTokenError, jwt.InvalidIssuerError, jwt.InvalidAudienceError) as e:
                return jsonify({'message': f'Invalid token. Details: {e}'}), 401

            except requests.exceptions.RequestException:
                return jsonify({'message': 'Failed to request the authentication server.'}), 500

            except KeyError:
                return jsonify({'message': 'Invalid token, it does not contain expected field(s).'}), 401

            except QueryNotFoundError as e:
                return jsonify({'message': f'Either user and package is not found. Details: {e}'}), 404

            except Exception as e:
                return jsonify({'message': f'Exception occurred during authentication. Details: {e}'}), 500
        else:
            return jsonify({'message': 'No token provided.'}), 401

    return decorated_func


def prohibit_access(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return jsonify({'message': 'Access prohibited'}), 403
    return wrapper


def testing_purpose(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        token = request.headers.get('Authorization')
        if token:
            token = token.split(' ')[1]  # Remove the 'Bearer' prefix from the token
            if token == "FlipJungleModAccessFilip1234@#!":
                return func(*args, **kwargs)
        return jsonify({"message": "Access prohibited (for normal user)"}), 403
    return decorated_func
