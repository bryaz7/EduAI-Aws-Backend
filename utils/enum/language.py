from enum import Enum


class Language(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    HINDI = "hi"
    ITALIAN = "it"
    GERMAN = "de"
    POLISH = "pl"
    PORTUGUESE = "pt"

    @classmethod
    def value_of(cls, value: str):
        for k, v in cls.__members__.items():
            if k.lower() == value.lower():
                return v
        else:
            return Language.ENGLISH


language_mapper = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "it": "Italian",
    "de": "German",
    "pl": "Polish",
    "pt": "Portuguese"
}


def get_language_name_from_code(language_code: str):
    return language_mapper.get(language_code, "Other")
