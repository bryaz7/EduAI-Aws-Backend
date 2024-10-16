import json
import os
import logging
from typing import Dict

import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def extract_draw_keywords(user_input):
    system_prompt = """From the given prompt, extract keywords from the prompt, along with potential keywords to 
    enhance image generation. Your answer would contain keyword only.

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
    Agent:""".format(user_input)
    message_history = [
        {"role": "user", "content": system_prompt},
    ]
    response = call_openai_request(message_history)
    bot_response = response["choices"][0]["message"]["content"]
    logging.info("Analyze draw image prompt")
    logging.info(user_input)
    logging.info(bot_response)
    return bot_response


def is_prompt_request_image(prompt):
    message_history = [
        {"role": "system", "content": "Provide an answer and determine if the user's input indicates a request for an "
                                      "image on a specific topic. Respond with 'true' if the user wants an image, "
                                      "or 'false' otherwise."},
        {"role": "system", "content": "Please respond just with either 'true' or 'false'."},
        {"role": "user", "content": "Can you help me draw a cat?"},
        {"role": "assistant", "content": "true"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "false"},
        {"role": "user", "content": prompt},
    ]
    response = call_openai_request(message_history)
    bot_response = response["choices"][0]["message"]["content"]
    logging.info("Checking drawing function")
    logging.info(prompt)
    logging.info(bot_response)
    return bot_response == 'true'


def generate_text(message_history, configs=None):
    if configs is None:
        configs = {}
    system_prompt = [
        {"role": "system", "content": f"Your name is {configs.get('agent_name')} and you have the knowledge and characteristic as {configs.get('agent_imitation')}" \
                                        ". You are talking to a 7 year-old kid." \
                                        "All of your answers must follow the below json format in 500 tokens at maximum.\n" \
                                        "{\"content\": <Your main answer as the character>, \"links\":  <around 3 web links as references>,"
                                        "\"next_questions\": <around 3 possible questions that improves brainstorming process>}"}
    ]
    message_history = [{"role": record["role"], "content": record["content"]}
                       for record in message_history if record["role"] in ["user", "assistant", "system"]]
    response = call_openai_request(system_prompt + message_history)
    logging.info(f'Response: {response["choices"][0]["message"]["content"]}')
    logging.info(f'{response["usage"]["prompt_tokens"]} prompt tokens used.')
    bot_response = response["choices"][0]["message"]["content"]
    
    if is_content_json_parsable(bot_response):
        return bot_response
    else:
        return json.dumps({
            "content": bot_response,
            "links": [],
            "next_questions": []
        })
    

def call_openai_request(messages):
    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.1,
        max_tokens=500,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        n=1,
        stop=["\nUser:"]
    )
    
def is_content_json_parsable(content):
    """Check if a string can be parsed into JSON or not

    Args:
        content (str): Content
    """
    try:
        json.loads(content)
        return True
    except json.JSONDecodeError:
        return False
    except Exception as e:
        logging.info("Exception occurred during encoding the answer")
        raise e