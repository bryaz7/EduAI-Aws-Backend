import uuid
import os
import time

import PIL
import boto3.exceptions
import flask_socketio
import openai

import logging
import logging.config

from typing import Dict
from apiflask import APIFlask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room

from db.extension import db
from services.chat import reformat_chat, ChatFactory
from services.elevenlabs import voice_stream
from services.openai_services import generate_text
from services import pickle, openai_services, api_service, aws_service

from PIL import Image

from services.stable_diffusion import create_image, create_image_with_stability_ai

from services.aws_service import invoke_progress_tracking, register_image

from dotenv import load_dotenv, find_dotenv

from utils.auth import validate_token
from utils.chat_config import generate_config_object
from utils.enum.action import Action
from utils.enum.role import ChatRole, AppRole
from utils.exceptions import (
    ConversationNotFoundError,
    get_default_openai_error_message,
    StabilityAIRequestError,
    get_default_stability_ai_error_message,
    get_default_error_message,
    get_default_boto3_error_message,
    get_default_wrong_image_format_message,
    OutOfQuotaError,
    LanguageIncompatibleError,
    get_default_language_incompatible_message,
    InvalidImageInput,
    get_default_small_image_message,
)
from utils.image import resize_image
from utils.template_responses import get_welcome_message
from utils.encoder import CustomJSONEncoder

load_dotenv(find_dotenv())

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")


def create_app():
    a = APIFlask(__name__)
    return a


app = create_app()
cors = CORS(app, origins="*")
app.config["CORS_HEADERS"] = "Content-Type"
migrate = Migrate(app, db)
chat_factory = ChatFactory()

# Configure the SQLite database, relative to the app instance folder
app.config["SPEC_FORMAT"] = "yaml"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATION"] = False

# Logs configurations
logging.config.fileConfig("logging_config.ini")
logger = logging.getLogger(__name__)

# Logs configurations
logging.config.fileConfig("logging_config.ini")
logger = logging.getLogger(__name__)

# Configure app's json encoder
app.json = CustomJSONEncoder(app)

with app.app_context():
    db.init_app(app)


def handle_update_message_history(data):
    user_id = data.get("user_id")
    message_history = data.get("message_history")
    pickle.update_pickle(user_id, "message_history", message_history)


def process_handle_image(user_id, user_question, uuid_request, message_history):
    image_data = create_image(user_question)
    image_key = f"chat_history/{user_id}/{uuid.uuid4()}.jpg"
    presigned_url = aws_service.generate_presigned_url(image_key)
    upload_res = aws_service.upload_image_to_s3(image_data, presigned_url)

    if upload_res.status_code == 200:
        image_url = f"https://edugenie.s3.ap-southeast-1.amazonaws.com/{image_key}"

        message_history.append({"role": "image", "content": image_url})
        data = {"user_id": user_id, "message_history": message_history}
        handle_update_message_history(data)
        return api_service.server_success(payload=image_url, uuid_request=uuid_request, image=True)

    return api_service.server_failed()


@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({"message": "success"})


@app.route("/api/reset_pickle", methods=["GET"])
def reset_pickle():
    logging.info("start /reset_pickle")
    pickle.reset_pickle()
    return "success"


@app.route("/api/load_message_by_timestamp", methods=["POST"])
def load_message_by_timestamp():
    try:
        # Parsing request
        args = api_service.get_args(request)

        user_id = args.get("user_id")
        person_ai_id = args.get("person_ai_id")
        limit = args.get("limit", 10)
        timestamp = args.get("timestamp")

        user_person_ai_id = UserPersonAI.get_user_person_ai_by_user(user_id, person_ai_id)
        history_message = HistoryMessage.get_by_user_person_ai_id(user_person_ai_id)

        chat_history = aws_service.get_message_by_search_key_timestamp(history_message.id, limit, timestamp)
        return chat_history
    except Exception as e:
        return api_service.server_failed(f"Fail with error {e}")


@app.route("/api/v1/get_chat_history", methods=["POST"])
def get_chat_history():
    try:
        # Parsing request
        args = api_service.get_args(request)
        uuid_request = args.get("uuid_request")
        user_id = args.get("user_id")
        person_ai_id = args.get("person_ai_id")
        limit = args.get("limit", 10)
        from_timestamp = args.get("from_timestamp")
        last_timestamp = args.get("last_timestamp")

        user_person_ai_id = UserPersonAI.get_user_person_ai_by_user(user_id, person_ai_id)
        history_message = HistoryMessage.get_by_user_person_ai_id(user_person_ai_id)

        chat_history = aws_service.get_message_record_from_dynamo_db(
            history_message.id, limit, last_timestamp, from_timestamp
        )
        return chat_history
    except Exception as e:
        return api_service.server_failed(f"Fail with error {e}")


# Websocket functionalities
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")
client_room_count = {}


@socketio.on("connect")
def handle_connect():
    logging.info("A client connected")


@socketio.on("disconnect")
def handle_disconnect():
    # The only string in rooms is the request.sid, others are the history_message_id corresponding to the chat room
    rooms = [room for room in flask_socketio.rooms(request.sid) if isinstance(room, int)]
    for room in rooms:
        client_room_count[room]["count"] -= 1
        if client_room_count[room]["role"] == AppRole.USER and client_room_count[room]["count"] == 0:
            invoke_progress_tracking(
                history_message_id=room,
                start_time=client_room_count[room]["start_time"],
            )


from db.models import HistoryMessage, UserPersonAI, PersonAIs


@socketio.on("user_join")
def handle_user_join(chatter_id, person_ai_id, role="user"):
    try:
        role = AppRole.get_role(role)
        (
            history_message,
            message_id,
        ) = HistoryMessage.get_message_history_id_by_user_or_parent(person_ai_id, chatter_id, role, exc=False)

        welcome_message = None
        if not history_message:
            # Get conversation data, if exists
            user_person_ai_id = UserPersonAI.get_user_person_ai_by_chatter(chatter_id, person_ai_id, role)

            if not user_person_ai_id:
                # Add a new UserPersonAI and MessageHistory record to the database
                if role == AppRole.USER:
                    user_person_ai = UserPersonAI(person_ai_id=person_ai_id, user_id=chatter_id)
                else:
                    user_person_ai = UserPersonAI(person_ai_id=person_ai_id, parent_id=chatter_id)
                db.session.add(user_person_ai)
                db.session.commit()

            user_person_ai_id = UserPersonAI.get_user_person_ai_by_chatter(chatter_id, person_ai_id, role)
            history_message = HistoryMessage.get_by_user_person_ai_id(user_person_ai_id)

            if not history_message:
                history_message = HistoryMessage.from_dict(
                    {
                        "user_person_ai_id": user_person_ai_id,
                        "media": [],
                        "file": [],
                        "note": [],
                    }
                )
                db.session.add(history_message)
                db.session.commit()
                history_message = HistoryMessage.get_by_user_person_ai_id(user_person_ai_id)

                if role == AppRole.USER:
                    chatter = db.session.get(User, chatter_id)
                else:
                    chatter = db.session.get(Parent, chatter_id)

                person_ai = db.session.get(PersonAIs, person_ai_id)

                guideline_next_questions = person_ai.guideline_next_questions
                if guideline_next_questions:
                    next_questions = guideline_next_questions.get(chatter.display_language)
                else:
                    next_questions = None

                # Send the first welcome message
                welcome_message = reformat_chat(
                    role=ChatRole.ASSISTANT,
                    content=get_welcome_message(
                        language=chatter.display_language,
                        user_name=None,
                        person_ai=person_ai,
                    ),
                    uuid_request=None,
                    next_questions=next_questions,
                )
                emit("chat", welcome_message)

        history_message_id = history_message.id
        join_room(history_message_id, request.sid)

        # Add 1 to room count
        if history_message_id in client_room_count:
            if client_room_count[history_message_id]["count"] == 0:
                client_room_count[history_message_id]["start_time"] = datetime.utcnow().isoformat()
            client_room_count[history_message_id]["count"] += 1
        else:
            client_room_count[history_message_id] = {
                "start_time": datetime.utcnow().isoformat(),
                "count": 1,
                "role": role,
            }

        # TODO: Limit is hard-coded
        limit = 20
        message_history = aws_service.get_message_record_from_dynamo_db(history_message.id, limit, None)
        message_history.update({"message_id": history_message_id})
        emit("message_history", message_history)

        if welcome_message:
            aws_service.save_message_record(history_message.id, **welcome_message)
        logging.info("Request {} has joined room {}".format(request.sid, history_message_id))
    except Exception as e:
        emit("error", str(e))
        raise e


@socketio.on("message-v2")
# @validate_token()
def handle_message(
    last_message: Dict[str, str],
    uuid_request: str,
    id: int,
    person_ai_id: int,
    action: Action = "text_to_text",
    role: str = "user",
):
    try:
        role = AppRole.get_role(role)
        (
            history_message,
            message_id,
        ) = HistoryMessage.get_message_history_id_by_user_or_parent(person_ai_id, id, role)
        configs = generate_config_object(id, message_id, person_ai_id, role, uuid_request)

    except Exception as e:
        emit("error", str(e))
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_error_message("English"),
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        raise e

    try:
        # Retrieve the agent base on action
        chat_service = chat_factory.get_chat_service(action)

        # Send the client message back (last in message history)
        user_message_str = last_message["content"]
        user_message = reformat_chat(role=ChatRole.USER, content=user_message_str, uuid_request=uuid_request)
        emit("chat", user_message, to=message_id)
        aws_service.save_message_record(message_id, **user_message)

        # Validate quote from user
        chat_service.validate(last_message, configs)

        # If image is in last_message payload, resize and emit the image
        if "image" in last_message:
            user_image_data = resize_image(last_message.get("image"))
            user_image_url, user_image_size = register_image(user_image_data, message_id)
            user_image_message = reformat_chat(
                role=ChatRole.USER_IMAGE,
                content=user_image_url,
                uuid_request=uuid_request,
            )
            emit("chat", user_image_message, to=message_id)
            item = aws_service.save_message_record(message_id, **user_image_message)
            timestamp = item["timestamp"]["S"]
            history_message.append_media(user_image_url, timestamp, user_image_size)
            last_message["image"] = user_image_data

        # Ask for the response
        assistant_response, metadata = chat_service.run(last_message, configs)

        # Emit audio streaming
        if assistant_response.get("role") == ChatRole.IMAGE:
            emit("chat", assistant_response, to=message_id)
            item = aws_service.save_message_record(message_id, **assistant_response)
            timestamp = item["timestamp"]["S"]
            history_message.append_media(
                assistant_response["content"], timestamp, metadata
            )  # Content here stores the image_url
        elif assistant_response.get("role") == ChatRole.ASSISTANT:
            stream = voice_stream(assistant_response.get("content"), configs.person_ai.voice)
            count = 0
            chunks = []
            concatenated_chunk = None
            start_time = time.time()
            for chunk in stream:
                if chunk:
                    if count == 0 and len(chunks) == 0:
                        emit("chat", assistant_response, to=message_id)

                    chunks.append(chunk)
                    if len(chunks) >= 10:
                        concatenated_chunk = b"".join(chunks)
                        chunks = []
                    else:
                        continue
                    audio_payload = {
                        "uuid": uuid_request,
                        "chunk": concatenated_chunk,
                        "count": count,
                    }
                    emit("audio", audio_payload, to=message_id)
                    count += 1

                    concatenated_chunk = None

            if len(chunks) > 0:
                concatenated_chunk = b"".join(chunks)
                audio_payload = {
                    "uuid": uuid_request,
                    "chunk": concatenated_chunk,
                    "count": count,
                }
                emit("audio", audio_payload, to=message_id)
                count += 1

            # Send stop message
            audio_final = {"uuid": uuid_request, "chunk": None, "count": -1}
            emit("audio", audio_final, to=message_id)

            end_time = time.time()
            execution_time = end_time - start_time

            print("execution_time: ", execution_time)
            aws_service.save_message_record(message_id, **assistant_response)
        else:
            emit("chat", assistant_response, to=message_id)
            aws_service.save_message_record(message_id, **assistant_response)

        # Update message count
        try:
            chat_service.check_quota(configs)
        except Exception as e:
            raise e
        finally:
            chat_service.update_counter(configs)

    # Exception handling
    except ConversationNotFoundError as e:
        emit("error", str(e))
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content="Hmm, can you refresh the page? I'll be right back then.",
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        raise e

    except openai.error.OpenAIError as e:
        emit("error", f"Error during calling chat API: {e.__class__} - {e}")
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_openai_error_message(configs.chatter.display_language),
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        raise e

    except StabilityAIRequestError as e:
        emit("error", f"Error during calling image generation API: {e.__class__} - {e}")
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_stability_ai_error_message(configs.chatter.display_language),
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        raise e

    except boto3.exceptions.Boto3Error as e:
        emit("error", f"Error during accessing AWS services: {e.__class__} - {e}")
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_boto3_error_message(configs.chatter.display_language),
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        raise e

    except PIL.UnidentifiedImageError as e:
        emit("error", f"Error during reading file/image: {e.__class__} - {e}")
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_wrong_image_format_message(configs.chatter.display_language),
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        raise e

    except OutOfQuotaError:
        dump_message = reformat_chat(role=ChatRole.SUBSCRIPTION_WARNING, content=None, uuid_request=uuid_request)
        emit("chat", dump_message)
        emit(
            "warning",
            "Out of available message quota for this feature, " "wait for a while or upgrade to a better package.",
        )

    except LanguageIncompatibleError:
        warning_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_language_incompatible_message(configs.chatter.chat_languages),
            uuid_request=uuid_request,
        )
        emit("chat", warning_message)
        emit(
            "warning",
            "Incorrect language identified. Retry with the correct language, "
            "change the language in settings, or upgrade to a better package.",
        )

    except InvalidImageInput:
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_small_image_message(configs.chatter.display_language),
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        emit("warning", "Image is too small")

    except Exception as e:
        emit("error", str(e))
        error_message = reformat_chat(
            role=ChatRole.ASSISTANT,
            content=get_default_error_message(configs.chatter.display_language),
            uuid_request=uuid_request,
        )
        emit("chat", error_message)
        raise e


# Import API (should be refactored in later versions)
from db.controllers import *
from services.payment_services import *
from utils.error_handler import *

if __name__ == "__main__":
    # Only for debugging while developing
    socketio.run(app=app, host="0.0.0.0", debug=True, port=5000, use_reloader=True)
