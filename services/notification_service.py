import logging
from typing import Optional, Dict, List

import firebase_admin
import os
from firebase_admin import credentials, messaging

from dotenv import load_dotenv, find_dotenv

from db.extension import db
from db.models import NotificationTemplate, LinkRequest, Notification, User, Parent
from utils.exceptions import NotificationGenerationError

load_dotenv(find_dotenv())

FIREBASE_CRED_PATH = os.getenv('FIREBASE_CRED_PATH')
COMPANY_AVATAR_URL = os.getenv('COMPANY_AVATAR_URL')
cred = credentials.Certificate(FIREBASE_CRED_PATH)
firebase_admin.initialize_app(cred)

reference_mapper = {
    "USER": User,
    "PARENT": Parent
}


def generate_notification(event_code, receive_user_id=None, receive_parent_id=None, reference_id=None,
                          image_url=COMPANY_AVATAR_URL, **kwargs) -> Dict:
    """
    Generate a `Notification` object.
    The function takes `event_code` as a required argument to get the template logic to generate the
    notification object.

    Args:
        event_code (str): Event code defined in the `NotificationTemplate` table.
        receive_user_id (int): User that receives the notification. Null if the receiver is parent.
        receive_parent_id (int): Parent that receives the notification. Null if the receiver is user.
        reference_id (int): Metadata ID. Depends on the `notification_type`, metadata ID can refer to a `LinkRequest`,
            `Promotion` or neither of those objects.
        image_url (int): Link to image URL. Default as FlipJungle logo.

    Returns:
        A `Notification` object.
    """
    notification_template: Optional[NotificationTemplate] = db.session.query(NotificationTemplate) \
        .filter(NotificationTemplate.event_code == event_code) \
        .first()

    if not receive_user_id and not receive_parent_id:
        raise NotificationGenerationError('Missing both user_id and parent_id as receiver')
    if (receive_user_id is not None) and (receive_parent_id is not None):
        raise NotificationGenerationError('Only 1 receiver is accepted, both user_id and parent_id is non-null')

    if not notification_template:
        raise NotificationGenerationError('Notification template not found, check if the event_code is correct')

    reference_type = notification_template.reference_type
    reference_dict = find_and_update_reference(reference_type, reference_id)
    kwargs.update(reference_dict)

    notification_object = {
        "user_id": receive_user_id,
        "parent_id": receive_parent_id,
        "reference_id": reference_id,
        "title": notification_template.title,
        "description": notification_template.description.format(**kwargs),
        "is_read": False,  # Set by default
        "notification_type": notification_template.notification_type,
        "reference_type": notification_template.reference_type,
        "image_url": image_url if image_url else COMPANY_AVATAR_URL
    }

    notification = Notification.from_dict(notification_object)
    if notification_template.is_pop_up_pushed:
        try:
            send_notification_single(
                title=notification.title,
                msg=notification.description,
                registration_tokens=get_firebase_registration_token(receive_user_id, receive_parent_id)
            )
        except Exception as e:
            raise NotificationGenerationError(f"Fail to push notification. Details: {e}")
    db.session.add(notification)
    db.session.commit()
    return notification.to_dict()


def find_and_update_reference(reference_type, reference_id) -> Dict:
    if not reference_type:
        return {}
    if reference_id is None:
        raise NotificationGenerationError(f"Reference type {reference_type} exists, but reference ID not found")

    # Special type: Link request
    if reference_type == "LINK_REQUEST":
        link_request = db.session.get(LinkRequest, reference_id)
        if not link_request:
            raise NotificationGenerationError(f'No link request found with reference_id {reference_id}')

        parent = db.session.get(Parent, link_request.parent_id)
        result = {}
        if parent:
            result.update({f"PARENT_{k}": v for k, v in parent.to_dict().items()})
            if parent.display_name is None:
                result["PARENT_display_name"] = f"Parent {parent.username or parent.email}"

        user = db.session.get(User, link_request.user_id)
        if user:
            result.update({f"USER_{k}": v for k, v in user.to_dict().items()})
            if user.display_name is None:
                result["USER_display_name"] = f"child {user.username or user.email}'"

        return result

    # Other common type
    reference_class = reference_mapper.get(reference_type)
    if not reference_class:
        raise NotificationGenerationError("Reference type not found in the reference_mapper")

    reference = db.session.get(reference_class, reference_id)
    if not reference:
        raise NotificationGenerationError("Reference not found")

    return {f"{reference_type}_{k}": v for k, v in reference.to_dict().items()}


def get_firebase_registration_token(receive_user_id, receiver_parent_id) -> List[str]:
    """
    Retrieve firebase tokens from user or parent entities.

    Args:
        receive_user_id: User ID that receives the notification. Set this to None if the entity is parent.
        receiver_parent_id: Parent ID that receives the notification. Set this to None if the entity is user.

    Returns:
        A list of Firebase registration tokens if entity's is_notification_on is True, else returns an empty list.
    """
    if receive_user_id:
        user = db.session.get(User, receive_user_id)
        if not user:
            raise NotificationGenerationError("Fail to generate notification: User not found")
        return user.firebase_registration_tokens if user.is_notification_on and user.firebase_registration_tokens else []
    elif receiver_parent_id:
        parent = db.session.get(Parent, receiver_parent_id)
        if not parent:
            raise NotificationGenerationError("Fail to generate notification: Parent not found")
        return parent.firebase_registration_tokens if parent.is_notification_on and parent.firebase_registration_tokens else []


def send_notification_single(title, msg, registration_tokens, data_object=None):
    """Send a notification to a single user. A user can have multiple registration tokens if he/she logs in
    multiple devices."""
    if len(registration_tokens) > 0:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=msg
            ),
            data=data_object,
            tokens=registration_tokens
        )
        messaging.send_each_for_multicast(message)
    else:
        logging.warning("List of registration tokens is empty, no notification will be sent")
