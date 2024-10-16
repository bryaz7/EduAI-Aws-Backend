import io

from db.extension import db
from db.models import User, Parent

from main import app

from flask import request, jsonify, send_file

from services.aws_service import get_image_from_s3, cognito_disable_user, cognito_delete_user, cognito_set_password

from utils.auth import validate_token, testing_purpose
from utils.exceptions import ItemNotFoundError, ValidationError


@app.route("/api/pre-check-create-link", methods=['GET'])
@validate_token
def check_parent_can_create_link():
    parent_id = request.args.get("parent_id", type=int)
    user_id = request.args.get("user_id", type=int)

    if parent_id is None:
        return jsonify({"message": "Missing parent_id field"}), 400

    parent_quota = Parent.get_current_num_link_with_quota(parent_id)
    current_num_links = parent_quota["current_num_links"]
    max_num_links = parent_quota["max_num_links"]
    if current_num_links >= max_num_links:
        return jsonify({
            "status": "UNAVAILABLE",
            "reason": "Parent reaches maximum of links between parent and learners."
        })

    if user_id is not None:
        user = db.session.get(User, user_id)
        if user.parent is not None:
            return jsonify({
                "status": "UNAVAILABLE",
                "reason": "Learner already linked to a parent"
            })

        user_package = User.get_active_package(user_id)
        parent_package = Parent.get_active_package(parent_id)
        if user_package.monthly_pay_price != 0 and parent_package.monthly_pay_price != 0:
            return jsonify({
                "status": "WARNING",
                "reason": f"Parent is at {parent_package.name} package, while learner is at {user_package.name} "
                          f"package, which are both paid packages. Confirm linking will remove "
                          f"usage at the lower-valued package.",
                "parent_package": parent_package.to_dict(),
                "user_package": user_package.to_dict()
            })

    return jsonify({
        "status": "SUCCESS",
        "reason": "Can create link"
    })


@app.route("/api/get-image-from-chat-history", methods=['GET'])
@validate_token
def get_image_from_chat_history():
    image_key = request.args.get('image_key')
    try:
        image_data = get_image_from_s3(image_key)
    except ConnectionError as e:
        return jsonify({"message": str(e)}), 510

    return send_file(
        io.BytesIO(image_data),
        mimetype='image/jpeg',
        as_attachment=False,
        download_name='image.jpg'
    )


@app.route("/api/authorized-change-password", methods=['PUT'])
@validate_token
def authorized_reset_password():
    data = request.get_json()
    parent_id = data.get('parent_id')
    user_id = data.get('user_id')
    new_password = data.get('password')

    user = db.session.get(User, user_id)
    if not user:
        raise ItemNotFoundError("User not found")

    if user.email is not None:
        raise ValidationError("The user has email, therefore user should validate change password by their own email")

    parent = db.session.get(Parent, parent_id)
    if not parent:
        raise ItemNotFoundError("Parent not found")

    if user.parent_id != parent_id:
        raise ValidationError("The user is not parent's child, cannot change password")

    cognito_set_password(user.username, new_password)
    return jsonify({"message": "Set new password successfully"})


# Rollback features for testing
@app.route("/api/rollback", methods=['DELETE'])
@testing_purpose
def rollback_account():
    data = request.get_json()
    user_id = data.get("user_id")
    parent_id = data.get("parent_id")

    if user_id is not None:
        user = db.session.get(User, user_id)
        cognito_disable_user(user.username)
        cognito_delete_user(user.username)
        db.session.delete(user)
        db.session.commit()

    if parent_id is not None:
        parent = db.session.get(Parent, parent_id)
        cognito_disable_user(parent.username)
        cognito_delete_user(parent.username)
        db.session.delete(parent)
        db.session.commit()

    return jsonify({"message": "Rollback user/parent successfully"})
