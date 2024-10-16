from enum import Enum

from utils.exceptions import StyleNotFoundError


class ImageGenerationStyle(str, Enum):
    REALISM = "realism"
    ANIME = "anime"
    MINIMALISM = "minimalism"
    EXPRESSIONISM = "expressionism"
    IMPRESSIONISM = "impressionism"
    PAINTING = "painting"

    @staticmethod
    def keyword_mapping(style):
        mapper = {
            ImageGenerationStyle.REALISM: "realism, complex detailed, high contrast, low saturation, backlighting",
            ImageGenerationStyle.ANIME: "Anime, Big expressive eyes, cute chibi-like proportions, colorful and vibrant "
                                        "artwork, Playful expressions, stylized features, line art, sparkles",
            ImageGenerationStyle.MINIMALISM: "minimalism, cinematic, simplified, 8k, vivid color",
            ImageGenerationStyle.EXPRESSIONISM: "expressionism, detailed, digital art, colorful background, absurdist",
            ImageGenerationStyle.PAINTING: """Bold outlines, simplified shapes, Exaggerated facial features, playful 
            expressions, Vibrant colors, simplified backgrounds, Comic-style speech bubbles, Cartoonish textures, 
            dynamic poses"""
        }
        return mapper.get(style, style)
