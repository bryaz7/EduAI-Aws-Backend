import base64
import logging
import io
from typing import Dict

import requests
import os

from PIL import Image

from services import openai_services
from utils.exceptions import StabilityAIRequestError

ENGINE_ID = 'stable-diffusion-512-v2-1'
STABILITY_API_KEY = os.getenv('STABILITY_KEY')


def create_image(user_input):
    prompt = openai_services.extract_draw_keywords(user_input)

    logging.info('prompt after analyze: ', prompt)

    API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
    headers = {"Authorization": "Bearer {HUGGINGFACE_ACCESS_TOKEN}"}

    def query(payload):
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.content

    image_bytes = query({
        "inputs": prompt
    })

    return image_bytes


def text_to_image_stability_ai(user_prompt: str, configs: Dict):
    extracted_prompt = openai_services.extract_draw_keywords(user_prompt)
    response = requests.post(
        f"https://api.stability.ai/v1/generation/{ENGINE_ID}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {STABILITY_API_KEY}"
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
    return img_data


def image_to_image_stability_ai(user_prompt: str, image_bytes: bytes, configs: Dict):
    """Image to image generation using Stability AI API

    Args:
        user_prompt (str): User inquiry
        image_bytes (bytes): Byte representation of user image
        configs (Dict): Configuration

    Returns:
        img_data (bytes): The returned image
    """
    response = requests.post(
        f"https://api.stability.ai/v1/generation/{ENGINE_ID}/image-to-image",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {STABILITY_API_KEY}"
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
    return img_data


def create_image_with_stability_ai(user_prompt: str, user_image: bytes, configs: Dict):
    if user_image is None:
        # Text to image
        return text_to_image_stability_ai(user_prompt, configs)
    else:
        # Image to image
        return image_to_image_stability_ai(user_prompt, user_image, configs)
