import base64
import json
import os
from abc import ABC
from datetime import datetime
from typing import Dict, List, Optional

import openai
import requests
import tiktoken

from services import aws_service
from services.aws_service import update_text_to_text_counter, get_text_to_text_counter, get_image_generation_counter, \
    update_image_generation_counter, comprehend_detect_language, get_system_prompt
from services.notification_service import generate_notification
from utils.chat_config import ChatConfig
from utils.enum.action import Action
from utils.enum.language import Language, get_language_name_from_code
from utils.enum.role import ChatRole, AppRole
from utils.enum.style import ImageGenerationStyle
from utils.exceptions import ActionNotFoundError, StabilityAIRequestError, OutOfQuotaError, LanguageIncompatibleError

DEFAULT_MODEL = "gpt-3.5-turbo"
STABILITY_TEXT_TO_IMAGE_URL = os.getenv('STABILITY_TEXT_TO_IMAGE_URL')
STABILITY_IMAGE_TO_IMAGE_URL = os.getenv('STABILITY_IMAGE_TO_IMAGE_URL')


def num_tokens_from_messages(messages):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(DEFAULT_MODEL)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if True:  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens


def reformat_chat(role: ChatRole, content: Optional[str], uuid_request: Optional[str], links=None, next_questions=None):
    if next_questions is None:
        next_questions = []
    if links is None:
        links = []
    return {
        "role": role.value,
        "content": content,
        "links": links,
        "next_questions": next_questions,
        "uuid_request": uuid_request,
        "timestamp": datetime.utcnow().isoformat()
    }


def format_system_prompt(configs: ChatConfig):
    agent_name = configs.person_ai.name
    user_age = configs.user_age
    username = configs.user_or_display_name
    system_prompt_formatted = get_system_prompt(agent_name, user_age, username)
    return [{
        "role": ChatRole.SYSTEM.value,
        "content": system_prompt_formatted
    }]


def filter_message_history(message_history: List[Dict]):
    return [{"role": record["role"], "content": record["content"]} for record in message_history
            if record["role"] in ["user", "assistant", "system"]]


def call_openai_request(messages: List[Dict], configs: ChatConfig = None,
                        function_call: Optional[Dict] = None,
                        functions: Optional[List] = None):
    call_configs = {
        "model": DEFAULT_MODEL,
        "messages": messages
        # "temperature": 0.2
    }
    if function_call:
        call_configs.update({"function_call": function_call})
    if functions:
        call_configs.update({"functions": functions})
    return openai.ChatCompletion.create(**call_configs)


class BaseChatService(ABC):
    """
    Base class for chat service
    """

    def __init__(self):
        # Language detection prompt
        self.language_detect_function_call = {"name": "detect_language"}
        self.language_detect_functions = [
            {
                "name": "detect_language",
                "description": "Detect the language of a prompt",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "language": {
                            "type": "string",
                            "enum": [e.value for e in Language],
                            "description": "Language of a prompt, output `other` if none of the list is "
                                           "satisfiable. Please provide the answer only from the list."
                        }
                    }
                },
                "required": ["language"]
            }
        ]

    def run(self, user_data: Dict, configs: ChatConfig):
        raise NotImplementedError

    def validate(self, user_data: Dict, configs: ChatConfig) -> bool:
        """Validate if user has enough quota based on package"""
        raise NotImplementedError

    @staticmethod
    def detect_language(message: Dict):
        """Detect the language of the message using AWS Comprehend"""
        text = message.get("content")
        languages = comprehend_detect_language(text)
        languages = [get_language_name_from_code(language) for language in languages]
        return languages

    def update_counter(self, configs: ChatConfig) -> int:
        """Update the number of request after a period for validation check"""
        raise NotImplementedError

    def check_quota(self, configs: ChatConfig):
        """Check quota for raising notification, if any"""
        raise NotImplementedError


class TextToTextChatService(BaseChatService):

    def __init__(self):
        super().__init__()
        self.limit = 10
        # Function call in OpenAI
        # (https://github.com/openai/openai-cookbook/blob/main/examples/How_to_call_functions_with_chat_models.ipynb)
        self.function_call = {"name": "get_answer"}
        self.functions = [
            {
                "name": "get_answer",
                "description": "",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Your response to user"
                        },
                        "links": {
                            "type": "array",
                            "description": "Around 3 links as references to your answer",
                            "items": {
                                "type": "string"
                            }
                        },
                        "next_questions": {
                            "type": "array",
                            "description": "Around 3 possible next questions to be asked, if there is none,"
                                           " you can create random questions relating to yourself.",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["content", "links", "next_questions"]
                }
            }
        ]

    def run(self, user_data: Dict, configs: ChatConfig):
        """
        Call to get text generation from OpenAI service.

        Args:
            user_data (Dict): Should contain

                prompt (str): User prompt

                message_id (int): Message ID

            configs (Dict): Configurations

        Returns:
            Dict with 3 fields: `content`, `links`, and `next_questions`
        """
        system_prompt = format_system_prompt(configs)

        message_id = configs.message_id
        message_history = aws_service.get_message_record_from_dynamo_db(message_id, self.limit).get("data")
        message_history = filter_message_history(message_history)

        filtered_message_history = self.limit_prompts(system_prompt, message_history)
        response = call_openai_request(filtered_message_history, configs, self.function_call, self.functions)
        bot_response = json.loads(response["choices"][0]["message"]["function_call"]["arguments"])

        return reformat_chat(
            role=ChatRole.ASSISTANT,
            uuid_request=configs.uuid_request,
            **bot_response
        ), None

    def validate(self, user_data: Dict, configs: ChatConfig):
        allowed_request = configs.package.allowed_request
        # Check allowed request
        if allowed_request == -1:
            return self.validate_languages(configs, user_data)
        else:
            request_within_an_hour = get_text_to_text_counter(configs.chatter.id, configs.role)
            if request_within_an_hour < allowed_request:
                return self.validate_languages(configs, user_data)
            else:
                raise OutOfQuotaError("Out of text-to-text quota")

    def validate_languages(self, configs: ChatConfig, user_data: Dict):
        # Continue to check language
        allowed_language = configs.chatter.chat_languages
        inferred_language = self.detect_language(user_data)
        not_allowed_language = set(inferred_language).difference(set(allowed_language))
        if len(not_allowed_language) == 0:
            return True
        else:
            raise LanguageIncompatibleError("The language you are using may be incorrect, expect"
                                            " {} but {} found".format(allowed_language, inferred_language))

    def update_counter(self, configs: ChatConfig) -> int:
        return update_text_to_text_counter(configs.chatter.id)

    def check_quota(self, configs: ChatConfig):
        num_chat = get_text_to_text_counter(configs.chatter.id, configs.role)
        if configs.package.allowed_request != -1 and num_chat + 1 >= configs.package.allowed_request:
            if configs.role == AppRole.USER:
                generate_notification(
                    event_code="CHILD_OUT_OF_MESSAGE_QUOTA_WARNING",
                    receive_user_id=configs.chatter.id
                )
            else:
                generate_notification(
                    event_code="PARENT_OUT_OF_MESSAGE_QUOTA_WARNING",
                    receive_parent_id=configs.chatter.id
                )

    def limit_prompts(self, system_prompt, message_history, max_input_tokens=2000, min_auto_acceptance_prompts=20):
        for i in range(len(message_history)):
            filtered_message_history = system_prompt + message_history[i:]
            if len(filtered_message_history) - 1 <= min_auto_acceptance_prompts:
                return filtered_message_history
            n_tokens = num_tokens_from_messages(filtered_message_history)
            if n_tokens <= max_input_tokens:
                return filtered_message_history


class ImageGenerationChatService(BaseChatService):

    def __init__(self):
        super(ImageGenerationChatService, self).__init__()
        self.ENGINE_ID = 'stable-diffusion-512-v2-1'
        self.STABILITY_API_KEY = os.getenv('STABILITY_KEY')

    def get_engine_id(self):
        return self.ENGINE_ID

    def get_api_key(self):
        return self.STABILITY_API_KEY

    def validate(self, user_data: Dict, configs: ChatConfig) -> bool:
        image_generation_limit = configs.package.image_generation_limit
        if image_generation_limit == -1:
            return True
        else:
            if configs.package_group is None:
                raise OutOfQuotaError("Cannot create image on a free package")

            current_period_start = configs.package_group.current_period_start
            request_within_a_month = get_image_generation_counter(
                package_group_id=configs.package_group.id,
                current_period_start=current_period_start
            )
            if request_within_a_month < image_generation_limit:
                return True
            else:
                raise OutOfQuotaError("Out of image generation quota")

    def check_quota(self, configs: ChatConfig):
        num_images = get_image_generation_counter(
            package_group_id=configs.package_group.id,
            current_period_start=configs.package_group.current_period_start
        )
        if num_images + 1 >= configs.package.image_generation_limit:
            # Raise notifications to learners
            for learner in configs.package_group.users:
                generate_notification(
                    event_code="CHILD_OUT_OF_IMAGE_QUOTA_WARNING",
                    receive_user_id=learner.id
                )
            # Raise notifications to parent
            for parent in configs.package_group.parents:
                generate_notification(
                    event_code="PARENT_OUT_OF_IMAGE_QUOTA_WARNING",
                    receive_parent_id=parent.id
                )

    def update_counter(self, configs: ChatConfig) -> int:
        return update_image_generation_counter(
            package_group_id=configs.package_group.id,
            current_period_start=configs.package_group.current_period_start
        )


class TextToImageChatService(ImageGenerationChatService):

    def __init__(self):
        super().__init__()
        self.draw_extraction_prompt = """From the given prompt, extract keywords from the prompt, along with 
        potential keywords to enhance image generation. Your answer would contain keyword only.

        User: Draw Kobe Bryant

        Agent:  Kobe Bryant, black buzz cut hairstyle, semi-realistic, detailed half body, 
        webtoon style, rinotuna reference, super detail, gradient background, soft colors, soft lighting, anime, 
        high detail, light and dark contrast, best quality super detail, 3d, C4d, blender, renderer, 
        cinematic lighting, ultra high definition high detail, art station seraflur, art, ip, blind box, divine, 
        cinematic, edge lighting, vray render

        User: Give me a picture of chibi Elon Musk

        Agent: Elon Musk, chi, standing centered, Pixar style, 3d style, disney style, 8k, Beautiful

        User: Give me a cute 3D version of Michael Jackson

        Agent: Michael Jackson, cute, 3D, standing centered, Pixar style, 3d style, disney style, 8k, Beautiful

        User: {}
        Agent:"""

    def extract_draw_keywords(self, user_prompt):
        formatted_prompt = self.draw_extraction_prompt.format(user_prompt)
        message_history = [
            {"role": "user", "content": formatted_prompt},
        ]
        response = call_openai_request(message_history)
        bot_response = response["choices"][0]["message"]["content"]
        return bot_response

    def run(self, user_data: Dict, configs: ChatConfig):
        user_prompt = user_data.get('content')
        extracted_prompt = self.extract_draw_keywords(user_prompt)
        response = requests.post(
            STABILITY_TEXT_TO_IMAGE_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.get_api_key()}"
            },
            json={
                "text_prompts": [
                    {
                        "text": extracted_prompt
                    }
                ],
                "cfg_scale": 12,
                "height": 512,
                "width": 512,
                "samples": 1,
                "steps": 50,
            },
        )
        if response.status_code != 200:
            raise StabilityAIRequestError("Non-200 response during image generation: " + str(response.text))
        data = response.json()
        img_data = base64.b64decode(data["artifacts"][0]["base64"])

        message_id = configs.message_id
        img_url, img_size = aws_service.register_image(img_data, message_id)
        return reformat_chat(
            role=ChatRole.IMAGE,
            content=img_url,
            uuid_request=configs.uuid_request
        ), img_size


class ImageToImageChatService(ImageGenerationChatService):

    def __init__(self):
        super().__init__()

    def run(self, user_data: Dict, configs: ChatConfig):
        """Image to image generation using Stability AI API

        Args:
            user_data (Dict): Should contains

                content (str): User prompt

                image (bytes): ASCII representation of image

            configs (Dict): Configuration

        Returns:
            img_data (bytes): The returned image
        """
        user_prompt = user_data.get('content')
        user_prompt = ImageGenerationStyle.keyword_mapping(user_prompt)
        image_bytes = user_data.get('image')
        response = requests.post(
            STABILITY_IMAGE_TO_IMAGE_URL,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.get_api_key()}"
            },
            files={
                "init_image": image_bytes
            },
            data={
                "image_strength": 0.3,
                "init_image_mode": "IMAGE_STRENGTH",
                "text_prompts[0][text]": user_prompt,
                "cfg_scale": 7,
                "clip_guidance_preset": "FAST_BLUE",
                "samples": 1,
                "steps": 50,
            }
        )
        if response.status_code != 200:
            raise StabilityAIRequestError("Non-200 response during image generation: " + str(response.text))
        data = response.json()
        img_data = base64.b64decode(data["artifacts"][0]["base64"])

        message_id = configs.message_id
        img_url, img_size = aws_service.register_image(img_data, message_id)
        return reformat_chat(
            role=ChatRole.IMAGE,
            content=img_url,
            uuid_request=configs.uuid_request
        ), img_size


class ChatFactory:
    chat_service_mapper = {
        Action.TEXT_TO_TEXT: TextToTextChatService,
        Action.TEXT_TO_IMAGE: TextToImageChatService,
        Action.IMAGE_TO_IMAGE: ImageToImageChatService
    }

    def get_chat_service(self, action: Action) -> BaseChatService:
        if action in self.chat_service_mapper:
            return self.chat_service_mapper[action]()
        else:
            raise ActionNotFoundError("Action is not available at this moment")
