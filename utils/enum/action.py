from enum import Enum


class Action(str, Enum):
    TEXT_TO_TEXT = "text_to_text"
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"

    # Unavailable actions
    PLAY_GAME = "play_game"
    TRANSLATE = "translate"
