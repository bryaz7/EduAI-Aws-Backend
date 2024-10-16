from typing import Optional

from db.models import PersonAIs
from utils.enum.language import Language

welcome_messages = {
    Language.ENGLISH: "Hi, I'm {agent_name}. It's great to have you here. How can I assist you?",
    Language.SPANISH: "Hola, soy {agent_name}. Es emocionante verte aquí. ¿En qué puedo ayudarte?",
    Language.FRENCH: "Bonjour, je suis {agent_name}. C'est génial de te voir ici. Comment puis-je t'aider ?",
    Language.HINDI: "नमस्ते, मैं {agent_name} हूँ। तुम्हें यहाँ देखकर बहुत खुशी हुई। मैं तुम्हारी कैसे सहायता कर सकता हूँ?",
    Language.ITALIAN: "Ciao, sono {agent_name}. È fantastico vederti qui. Come posso aiutarti?",
    Language.GERMAN: "Hallo, ich bin {agent_name}. Es ist aufregend, dich hier zu sehen. Wie kann ich dir helfen?",
    Language.POLISH: "Cześć, jestem {agent_name}. Miło cię widzieć tutaj. W czym mogę pomóc?",
    Language.PORTUGUESE: "Olá, eu sou {agent_name}. É empolgante te ver aqui. Como posso ajudar?"
}


def get_welcome_message(language: str, user_name: Optional[str], person_ai: PersonAIs):
    person_ai_welcome_messages = person_ai.welcome_messages
    if person_ai_welcome_messages:
        if language in person_ai_welcome_messages:
            return person_ai_welcome_messages[language]

    # Return default message if not found any
    language = Language.value_of(language)
    return welcome_messages[language].format(agent_name=person_ai.name)
