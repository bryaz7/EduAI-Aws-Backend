from enum import Enum


class ChatRole(str, Enum):
    USER = "user"  # User text (text-to-text)
    ASSISTANT = "assistant"  # Assistant text
    IMAGE = "image"  # Assistant image
    SYSTEM = "system"  # System prompt
    USER_IMAGE = "user_image"  # User image
    ASSISTANT_IMAGE = "assistant_image"  # DEPRECIATED: Assistant image
    SUBSCRIPTION_WARNING = "subscription_warning"  # Subscription warning, for turning waiting response off


class AppRole(str, Enum):
    USER = "user"
    PARENT = "parent"

    def get_role(role_str: str):
        if role_str == "parent":
            return AppRole.PARENT
        elif role_str in ["user", "user_under_13", "user_over_13"]:
            return AppRole.USER
        else:
            raise ValueError("Role is invalid, it should be user or parent")
