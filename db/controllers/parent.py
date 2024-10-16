from flask import jsonify, request
from sqlalchemy import or_

from db.models import LinkRequest, Parent, User
from main import db, app
from services.aws_service import register_image, cognito_disable_user, get_image_generation_counter
from services.notification_service import generate_notification
from utils.auth import validate_token
from utils.enum.language import language_mapper
from utils.exceptions import NotificationGenerationError, ItemNotFoundError, ValidationError


@app.route('/api/parents/<int:parent_id>', methods=['GET'])
@validate_token
def get_parent(parent_id):
    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'Parent not found.'}), 404
    return jsonify(parent.to_dict())


@app.route('/api/parents', methods=['GET'])
@validate_token
def get_parent_by_fields():
    subject_id = request.args.get('subject_id')
    q = request.args.get('q')
    limit = request.args.get('limit')
    if not subject_id and not q:
        return jsonify({'error': 'Missing subject_id or q parameter.'}), 400

    if subject_id:
        parent = db.session.query(Parent).filter_by(subject_id=subject_id).first()
        if parent:
            return jsonify(parent.to_dict())
        else:
            return jsonify({'error': 'Parent not found.'}), 404
    else:
        parent_query = db.session.query(Parent).filter(
            or_(
                Parent.username.ilike(f"%{q}%"),
                Parent.display_name.ilike(f"%{q}%"),
                Parent.email.ilike(f"%{q}%")
            )
        )
        if limit is not None:
            parent_query = parent_query.limit(limit)
        parents = parent_query.all()
        parents = [parent.to_dict(subset=["id", "username", "display_name", "email", "avatar_url"])
                   for parent in parents]
        return jsonify(parents)


@app.route('/api/get_parent_level/<int:parent_id>', methods=['GET'])
@validate_token
def get_parent_level(parent_id):
    parent_level_info = Parent.get_parent_level(parent_id)
    if not parent_level_info:
        return jsonify({'message': 'Parent not found.'}), 404
    return jsonify(parent_level_info)


@app.route('/api/parents', methods=['POST'])
@validate_token
def create_parent():
    data = request.get_json()
    email = data.get('email')
    parent = Parent.from_dict(data)
    db.session.add(parent)
    db.session.commit()

    if email is not None:
        # Search for all users that entered parents' email
        users_with_parent_email = db.session.query(User).filter(User.parent_email == email).all()
        user_ids = [user.id for user in users_with_parent_email]
        LinkRequest.create_multiple_link_requests(user_ids=user_ids, parent_id=parent.id,
                                                  is_sent_by_parent=False, ignore_linked_users=True)

    try:
        generate_notification(event_code="PARENT_WELCOME_MESSAGE", receive_parent_id=parent.id)
        return jsonify({'message': 'Parent created successfully.'}), 201
    except NotificationGenerationError as e:
        return jsonify({'message': f'Parent created successfully, '
                                   f'but failed to create notification with error {e}'}), 201


@app.route('/api/parents/<int:parent_id>', methods=['PUT'])
@validate_token
def update_parent(parent_id):
    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'parent not found.'}), 404

    data = request.get_json()
    parent.update_fields(**data)
    db.session.commit()

    return jsonify({'message': 'Parent updated successfully.'})


@app.route('/api/parents/<int:parent_id>', methods=['DELETE'])
@validate_token
def delete_parent(parent_id):
    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'parent not found.'}), 404

    # Disable user in Cognito
    cognito_disable_user(parent.username)

    parent.soft_delete()
    db.session.commit()

    return jsonify({'message': 'Parent deleted successfully.'})


@app.route('/api/add-link/<int:parent_id>', methods=['PUT'])
@validate_token
def add_link(parent_id):
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id or not parent_id:
        return jsonify({'message': 'Missing user_id or parent_id parameter.'}), 400

    child = db.session.get(User, user_id)
    if not child:
        return jsonify({'message': 'Child user not found'}), 404

    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'Parent not found'}), 404

    # TODO: Prohibit parent to not link with n children

    child.parent_id = parent_id
    db.session.commit()

    return jsonify({'message': 'Child-parent link added successfully.'})


@app.route('/api/remove-link/<int:parent_id>', methods=['PUT'])
@validate_token
def remove_link(parent_id):
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id or not parent_id:
        return jsonify({'message': 'Missing user_id or parent_id parameter.'}), 400

    child = db.session.get(User, user_id)
    if not child:
        return jsonify({'message': 'Child user not found'}), 404

    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'Parent not found'}), 404

    if child.parent_id is None:
        return jsonify({'message': 'No link found between parent and child'}), 404

    child.parent_id = None
    db.session.commit()

    return jsonify({'message': 'Child-parent remove successfully.'})


@app.route('/api/list-children/<int:parent_id>', methods=['GET'])
@validate_token
def list_children(parent_id):
    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'Parent not found'}), 404

    children = db.session.query(User).filter_by(parent_id=parent_id).all()
    children = [child.to_dict() for child in children]
    return jsonify(children)


@app.route('/api/parents/set-chat-languages', methods=['PUT'])
@validate_token
def parent_set_chat_languages():
    data = request.get_json()
    parent_id = data.get('parent_id')
    languages = data.get('chat_languages')

    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'User not found'}), 404

    package = Parent.get_active_package(parent_id)
    all_languages = list(language_mapper.values())
    for lang in languages:
        if lang not in all_languages:
            return jsonify(
                {'message': 'Incorrect language, it should be {}. {} found'.format(', '.join(all_languages), lang)})

    if len(languages) > package.num_languages:
        return jsonify({'message': 'Number of supported languages exceed package limit,'
                                   ' try to upgrade to a better one'}), 402

    parent.chat_languages = languages
    db.session.commit()
    return jsonify({'message': 'Set chat languages successfully'})


@app.route('/api/parents/add-notif-registration-token', methods=['PUT'])
@validate_token
def add_parent_notif_registration_token():
    data = request.get_json()
    parent_id = data.get('parent_id')
    firebase_registration_token = data.get('firebase_registration_token')

    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'Parent not found'}), 404

    if not firebase_registration_token:
        return jsonify({'message': 'Missing firebase_registration_token field'}), 400

    if firebase_registration_token in parent.firebase_registration_tokens:
       return jsonify({'message': 'Token exists, nothing changed'})

    try:
        parent.add_firebase_registration_token(firebase_registration_token)
    except Exception as e:
        return jsonify({'message': f'Error found during insertion: {e}'}), 510

    return jsonify({'message': 'Add registration token successfully'})


@app.route('/api/parents/remove-notif-registration-token', methods=['PUT'])
@validate_token
def remove_parent_notif_registration_token():
    data = request.get_json()
    parent_id = data.get('parent_id')
    firebase_registration_token = data.get('firebase_registration_token')

    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({'message': 'Parent not found'}), 404

    if not firebase_registration_token:
        return jsonify({'message': 'Missing firebase_registration_token field'}), 400

    if firebase_registration_token not in parent.firebase_registration_tokens:
        return jsonify({'message': 'Token not found'}), 404

    try:
        parent.remove_registration_token(firebase_registration_token)
    except Exception as e:
        return jsonify({'message': f'Error found during insertion: {e}'}), 510

    return jsonify({'message': 'Remove registration token successfully'})


@app.route('/api/parents/get-active-package', methods=['GET'])
@validate_token
def get_parent_active_package():
    parent_id = int(request.args.get('parent_id'))
    package = Parent.get_active_package(parent_id)
    return {
        "parent_id": parent_id,
        "package_id": package.id
    }


@app.route('/api/parents/upload-avatar', methods=['PUT'])
@validate_token
def parent_upload_avatar():
    parent_id = request.form.get("parent_id", type=int)
    image = request.files.get("image")
    image_mimetype = image.mimetype
    if image_mimetype not in ["image/jpeg", "image/png"]:
        raise ValidationError("Only accept .jpg, .jpeg, and .png files")

    parent = db.session.get(Parent, parent_id)
    if not parent:
        raise ItemNotFoundError("User not found")

    image_url, _ = register_image(image_data=image.read(), id=parent_id, des="parent_avatar")
    parent.avatar_url = image_url
    db.session.commit()
    return jsonify({"message": "Upload avatar successfully"})


@app.route("/api/parents/get-num-links", methods=['GET'])
@validate_token
def get_linked_number():
    parent_id = request.args.get("parent_id", type=int)
    return Parent.get_current_num_link_with_quota(parent_id)


@app.route('/api/parents/get-quota', methods=['GET'])
@validate_token
def parent_get_quota():
    parent_id = request.args.get("parent_id", type=int)
    parent = db.session.get(Parent, parent_id)
    if not parent:
        raise ItemNotFoundError("Parent not found")

    active_package = Parent.get_active_package(parent_id)
    package_group = parent.package_group

    if package_group is not None:
        package_group_id = package_group.id
        current_period_start = package_group.current_period_start
        images_used = get_image_generation_counter(package_group_id, current_period_start)
    else:
        images_used = 0
    available_images = active_package.image_generation_limit

    return {
        "images_used": images_used,
        "available_images": available_images
    }
