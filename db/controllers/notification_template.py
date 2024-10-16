from flask import jsonify, request

from db.models import NotificationTemplate
from main import db, app
from utils.auth import validate_token, prohibit_access


@app.route('/api/notification-templates/<int:id>', methods=['GET'])
@validate_token
def get_notification_template(id):
    notification_template = db.session.get(NotificationTemplate, id)
    if not notification_template:
        return jsonify({'error': 'Notification template not found'}), 404
    return jsonify(notification_template.to_dict())


@app.route('/api/notification-templates', methods=['POST'])
@validate_token
def create_notification_template():
    data = request.get_json()
    notification_template = NotificationTemplate.from_dict(data)
    db.session.add(notification_template)
    db.session.commit()
    return jsonify({"message": "Notification template inserted successfully"}), 201


@app.route('/api/notification-templates/<int:id>', methods=['PUT'])
@validate_token
def update_notification_template(id):
    notification_template = db.session.get(NotificationTemplate, id)
    if not notification_template:
        return jsonify({'error': 'Notification template not found'}), 404
    data = request.get_json()
    notification_template.update_fields(**data)
    db.session.commit()
    return jsonify({"message": "Notification template updated successfully"}), 201


@app.route('/api/notification-templates/<int:id>', methods=['DELETE'])
@prohibit_access
def delete_notification_template(id):
    notification_template = db.session.get(NotificationTemplate, id)
    if not notification_template:
        return jsonify({'error': 'Notification template not found'}), 404
    notification_template.soft_delete()
    db.session.commit()
    return jsonify({'message': 'Notification template deleted'}), 200
