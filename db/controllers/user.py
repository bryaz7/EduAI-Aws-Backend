from flask import jsonify, request
from sqlalchemy import or_

from db.models import Parent, LinkRequest, Mail
from main import db, app
from db.models.user import User
from services.aws_service import register_image, send_approve_request_email, cognito_disable_user, \
    get_text_to_text_counter, get_image_generation_counter
from services.notification_service import generate_notification
from utils.auth import validate_token
from utils.email import validate_email

from utils.enum.language import language_mapper
from utils.enum.role import AppRole
from utils.exceptions import NotificationGenerationError, ItemNotFoundError, ValidationError
from utils.time import get_age


@app.route('/api/users/<int:user_id>', methods=['GET'])
@validate_token
def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found.'}), 404
    return jsonify(user.to_dict())


@app.route('/api/users', methods=['GET'])
@validate_token
def get_user_by_fields():
    subject_id = request.args.get('subject_id')
    parent_email = request.args.get('parent_email')
    q = request.args.get('q')
    limit = request.args.get('limit')
    no_parent = request.args.get('no_parent', default=False, type=lambda v: v.lower() == 'true')
    if not subject_id and not parent_email and not q:
        return jsonify({'error': 'Need either subject_id or parent_email or q field'}), 400

    if subject_id:
        user = db.session.query(User).filter_by(subject_id=subject_id).first()
        if user:
            return jsonify(user.to_dict())
        else:
            return jsonify({'error': 'User not found.'}), 404
    elif parent_email:
        users = User.get_by_parent_email(parent_email)
        users = [user.to_dict() for user in users]
        return jsonify(users)
    else:
        user_query = db.session.query(User).filter(
            or_(
                User.username.ilike(f"%{q}%"),
                User.display_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%")
            ),
        )
        if no_parent:
            user_query = user_query.filter(User.parent_id.is_(None))
        if limit is not None:
            user_query = user_query.limit(limit)
        users = user_query.all()
        users = [user.to_dict(subset=["id", "username", "display_name", "email", "avatar_url"]) for user in users]
        return jsonify(users)


@app.route('/api/get_user_level/<int:user_id>', methods=['GET'])
@validate_token
def get_user_level(user_id):
    user_level_info = User.get_user_level(user_id)
    if not user_level_info:
        return jsonify({'message': 'User not found.'}), 404
    return jsonify(user_level_info)


@app.route('/api/users', methods=['POST'])
@validate_token
def create_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    is_trash = data.get('is_trash')
    parent_id = data.get('parent_id')
    parent_email = data.get('parent_email')

    if is_trash is None:
        return jsonify({'message': 'Missing is_trash field'}), 400

    if is_trash and not email:
        if not username:
            return jsonify(
                {'message': 'Trash account (with is_trash = True) must have a username, username not found'}), 400

    if parent_id is not None:
        parent = db.session.get(Parent, parent_id)
        if not parent:
            return jsonify({"message": "Parent not found"}), 404

    user = User.from_dict(data)
    db.session.add(user)
    db.session.flush()

    if parent_email is not None:
        if validate_email(parent_email):
            # Check if email is on the bounced list
            if Mail.is_mail_bounced_or_complained_over_limit(parent_email):
                raise ValidationError("Guardian's email has been notified as an in-existing address")

            send_approve_request_email(parent_email, user_id=user.id)

            # Search for parents' email to send a link request
            parents_with_email = db.session.query(Parent).filter(Parent.email == parent_email).all()
            for parent in parents_with_email:
                LinkRequest.create_link_request(user_id=user.id, parent_id=parent.id, is_sent_by_parent=False, ignore_linked_users=True)
        else:
            raise ValidationError("Guardian's email is not valid")

    if user.parent_id is not None:
        user.package_group_id = Parent.get_active_package(user.parent_id)

    db.session.commit()
    try:
        generate_notification(event_code="CHILD_WELCOME_MESSAGE", receive_user_id=user.id)
        if parent_id is not None:
            generate_notification(event_code="PARENT_CREATE_CHILD_ACCOUNT_SUCCESS", receive_parent_id=parent_id)
        return jsonify({'message': 'User created successfully.'}), 201
    except NotificationGenerationError as e:
        return jsonify({'message': f'User created successfully, but failed to create notification with error {e}'}), 201


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@validate_token
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found.'}), 404

    data = request.get_json()
    user.update_fields(**data)
    db.session.commit()

    return jsonify({'message': 'User updated successfully.'})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@validate_token
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found.'}), 404

    # Disable user in Cognito
    cognito_disable_user(user.username)

    user.soft_delete()
    db.session.commit()

    return jsonify({'message': 'User deleted successfully.'})


@app.route('/api/set-chat-languages', methods=['PUT'])
@validate_token
def set_chat_languages():
    data = request.get_json()
    user_id = data.get('user_id')
    languages = data.get('chat_languages')

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    package = User.get_active_package(user_id)
    all_languages = list(language_mapper.values())
    for lang in languages:
        if lang not in all_languages:
            return jsonify(
                {'message': 'Incorrect language, it should be {}. {} found'.format(', '.join(all_languages), lang)})

    if len(languages) > package.num_languages:
        return jsonify({'message': 'Number of supported languages exceed package limit,'
                                   ' try to upgrade to a better one'}), 402

    user.chat_languages = languages
    db.session.commit()
    return jsonify({'message': 'Set chat languages successfully'})


@app.route('/api/users/set-chat-languages', methods=['PUT'])
@validate_token
def child_set_chat_languages():
    data = request.get_json()
    user_id = data.get('user_id')
    languages = data.get('chat_languages')

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    package = User.get_active_package(user_id)
    all_languages = list(language_mapper.values())
    for lang in languages:
        if lang not in all_languages:
            return jsonify(
                {'message': 'Incorrect language, it should be {}. {} found'.format(', '.join(all_languages), lang)})

    if len(languages) > package.num_languages:
        return jsonify({'message': 'Number of supported languages exceed package limit,'
                                   ' try to upgrade to a better one'}), 402

    user.chat_languages = languages
    db.session.commit()
    return jsonify({'message': 'Set chat languages successfully'})


@app.route('/api/users/add-notif-registration-token', methods=['PUT'])
@validate_token
def add_user_notif_registration_token():
    data = request.get_json()
    user_id = data.get('user_id')
    firebase_registration_token = data.get('firebase_registration_token')

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if not firebase_registration_token:
        return jsonify({'message': 'Missing firebase_registration_token field'}), 400

    if firebase_registration_token in user.firebase_registration_tokens:
        return jsonify({'message': 'Token exists, nothing changed'})

    try:
        user.add_firebase_registration_token(firebase_registration_token)
    except Exception as e:
        return jsonify({'message': f'Error found during insertion: {e}'}), 510

    return jsonify({'message': 'Add registration token successfully'})


@app.route('/api/users/remove-notif-registration-token', methods=['PUT'])
@validate_token
def remove_user_notif_registration_token():
    data = request.get_json()
    user_id = data.get('user_id')
    firebase_registration_token = data.get('firebase_registration_token')

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if not firebase_registration_token:
        return jsonify({'message': 'Missing firebase_registration_token field'}), 400

    if firebase_registration_token not in user.firebase_registration_tokens:
        return jsonify({'message': 'Token not found'}), 404

    try:
        user.remove_registration_token(firebase_registration_token)
    except Exception as e:
        return jsonify({'message': f'Error found during insertion: {e}'}), 510

    return jsonify({'message': 'Remove registration token successfully'})


@app.route('/api/get-user-data', methods=['GET'])
@validate_token
def get_user_data():
    subject_id = request.args.get('subject_id')

    user = User.get_by_subject_id(subject_id)
    if user is not None:
        user_object = user.to_dict()

        dob = user.date_of_birth
        age = get_age(dob)
        if age >= 13:
            user_object["role"] = "user_over_13"
        else:
            user_object["role"] = "user_under_13"

        package_id = User.get_active_package(user.id).id
        user_object["package_id"] = package_id
        return jsonify(user_object)

    parent = Parent.get_by_subject_id(subject_id)
    if parent is not None:
        parent_object = parent.to_dict()
        parent_object["role"] = "parent"
        parent_object["package_id"] = Parent.get_active_package(parent.id).id
        return jsonify(parent_object)

    return jsonify({"message": "Cannot found any user with given subject ID"}), 404


@app.route('/api/users/get-active-package', methods=['GET'])
@validate_token
def get_user_active_package():
    user_id = request.args.get('user_id', type=int)
    package = User.get_active_package(user_id)
    return {
        "user_id": user_id,
        "package_id": package.id
    }


@app.route('/api/users/upload-avatar', methods=['PUT'])
@validate_token
def child_upload_avatar():
    user_id = request.form.get("user_id", type=int)
    image = request.files.get("image")
    image_mimetype = image.mimetype
    if image_mimetype not in ["image/jpeg", "image/png"]:
        raise ValidationError("Only accept .jpg, .jpeg, and .png files")

    user = db.session.get(User, user_id)
    if not user:
        raise ItemNotFoundError("User not found")

    image_url, _ = register_image(image_data=image.read(), id=user_id, des="user_avatar")
    user.avatar_url = image_url
    db.session.commit()
    return jsonify({"message": "Upload avatar successfully"})


@app.route('/api/users/get-quota', methods=['GET'])
@validate_token
def child_get_quota():
    user_id = request.args.get("user_id", type=int)
    user = db.session.get(User, user_id)
    if not user:
        raise ItemNotFoundError("User not found")

    active_package = User.get_active_package(user_id)
    package_group = user.package_group

    messages_used = get_text_to_text_counter(user_id, AppRole.USER)
    available_messages = active_package.allowed_request

    if package_group is not None:
        package_group_id = package_group.id
        current_period_start = package_group.current_period_start
        images_used = get_image_generation_counter(package_group_id, current_period_start)
    else:
        images_used = 0
    available_images = active_package.image_generation_limit

    return {
        "messages_used": messages_used,
        "available_messages": available_messages,
        "images_used": images_used,
        "available_images": available_images
    }


@app.route("/api/users/request-link-parent-by-email", methods=['PUT'])
@validate_token
def request_link_parent_by_email():
    data = request.get_json()
    parent_email = data.get("parent_email")
    user_id = data.get("user_id")

    user = db.session.get(User, user_id)
    if not user:
        return ItemNotFoundError("User not found")

    if user.parent_id is not None:
        return ValidationError("User already had parent")

    if validate_email(parent_email):
        if Mail.is_mail_bounced_or_complained_over_limit(parent_email):
            raise ValidationError("Guardian's email has been notified as an in-existing address or it prevented us "
                                  "from sending")
    else:
        raise ValidationError("Not a correct email format")

    user.parent_email = parent_email
    db.session.commit()
    send_approve_request_email(parent_email, user_id)
    return jsonify({"message": "Email sent to parent"})
