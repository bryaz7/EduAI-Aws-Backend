from flask import jsonify, request

from db.models import Notification, User, Parent
from main import db, app
from services.notification_service import generate_notification
from utils.auth import validate_token, prohibit_access
from utils.exceptions import NotificationGenerationError, ItemNotFoundError


@app.route('/api/notifications/generate-notification-from-code', methods=['GET'])
@validate_token
def generate_notification_from_code():
    data = request.get_json()
    event_code = data.get('event_code')
    if not event_code:
        return jsonify({'message': 'Missing event code field'}), 400
    return generate_notification(**data)


@app.route('/api/notifications/<int:id>', methods=['GET'])
@validate_token
def get_notification(id):
    notification = db.session.get(Notification, id)
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    return jsonify(notification.to_dict())


@app.route('/api/notifications', methods=['POST'])
@validate_token
def create_notification():
    data = request.get_json()
    notification = Notification.from_dict(data)
    db.session.add(notification)
    db.session.commit()
    return jsonify({"message": "Notification inserted successfully"}), 201


@app.route('/api/notifications/<int:id>', methods=['PUT'])
@validate_token
def update_notification(id):
    notification = db.session.get(Notification, id)
    if not notification:
        return jsonify({'error': 'Notification template not found'}), 404
    data = request.get_json()
    notification.update_fields(**data)
    db.session.commit()
    return jsonify({"message": "Notification updated successfully"}), 201


@app.route('/api/notifications/<int:id>', methods=['DELETE'])
@prohibit_access
def delete_notification(id):
    notifications = db.session.get(Notification, id)
    if not notifications:
        return jsonify({'error': 'Notification not found'}), 404
    notifications.soft_delete()
    db.session.commit()
    return jsonify({'message': 'Notification deleted'}), 200


@app.route("/api/notifications/request-package-upgrade", methods=['POST'])
@validate_token
def request_package_upgrade():
    data = request.get_json()
    event_code = "CHILD_PACKAGE_UPGRADE_REQUEST"
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"message": "Missing user_id field"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    parent_id = user.parent_id
    if not parent_id:
        return jsonify({"message": "Learner have not been linked to any parent"}), 451

    try:
        generate_notification(
            event_code=event_code,
            receive_parent_id=parent_id,
            reference_id=user_id
        )
        return jsonify({"message": "Trigger notification success"})
    except NotificationGenerationError as e:
        return jsonify({"message": f"Fail to generate notification. Details: {e}"}), 501


@app.route('/api/notifications/trigger-notification-by-event', methods=['POST'])
@validate_token
def trigger_notification():
    data = request.get_json()
    try:
        generate_notification(
            event_code=data.get('event_code'),
            receive_parent_id=data.get('parent_id'),
            receive_user_id=data.get('user_id'),
            reference_id=data.get('reference_id')
        )
        return jsonify({"message": "Trigger notification success"})
    except NotificationGenerationError as e:
        return jsonify({"message": f"Fail to generate notification. Details: {e}"}), 501


@app.route("/api/notifications/child", methods=['GET'])
@validate_token
def get_all_child_notifications():
    user_id = request.args.get("user_id")
    is_read = request.args.get("is_read", type=lambda x: x.lower() == "true")
    if not user_id:
        return jsonify({"message": "Missing user_id field"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    notifications = Notification.get_notifications_for_child(user_id, is_read)
    notifications = [notification.to_dict() for notification in notifications]
    return jsonify(notifications)


@app.route("/api/notifications/parent", methods=['GET'])
@validate_token
def get_all_parent_notifications():
    parent_id = request.args.get("parent_id")
    is_read = request.args.get("is_read", type=lambda x: x.lower() == "true")
    if not parent_id:
        return jsonify({"message": "Missing parent_id field"}), 400

    parent = db.session.get(Parent, parent_id)
    if not parent:
        return jsonify({"message": "Parent not found"}), 404

    notifications = Notification.get_notifications_for_parent(parent_id, is_read)
    notifications = [notification.to_dict() for notification in notifications]
    return jsonify(notifications)


@app.route("/api/notifications/mark-as-read", methods=['PUT'])
@validate_token
def mark_as_read():
    data = request.get_json()
    notification_ids = data.get("notification_ids")
    if not notification_ids or not isinstance(notification_ids, list):
        return jsonify({"message": "Missing notification_ids field or field is not a list of integers"}), 400
    for notification_id in notification_ids:
        notification = db.session.get(Notification, notification_id)
        if notification:
            notification.is_read = True
        else:
            raise ItemNotFoundError(f"Notification {notification_id} not found")
        db.session.flush()
    db.session.commit()
    return jsonify({"message": "All notification marked as read"})
