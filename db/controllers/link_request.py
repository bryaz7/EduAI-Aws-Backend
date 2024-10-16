from flask import jsonify, request

from db.extension import db
from db.models import LinkRequest, User, Parent
from main import app
from services.notification_service import generate_notification, send_notification_single
from utils.auth import validate_token, prohibit_access
from utils.exceptions import ItemNotFoundError


@app.route('/api/link-requests/<int:id>', methods=['GET'])
@validate_token
def get_link_request(id):
    link_request = db.session.get(LinkRequest, id)
    if not link_request:
        return jsonify({'error': 'Link request not found'}), 404
    return jsonify(link_request.to_dict())


@app.route('/api/link-requests/child', methods=['POST'])
@validate_token
def child_create_link_request():
    data = request.get_json()
    user_id = data.get('user_id')
    parent_id = data.get('parent_id')

    link_request, sender, receiver = LinkRequest.create_link_request(
        user_id=user_id,
        parent_id=parent_id,
        is_sent_by_parent=False
    )
    generate_notification(
        event_code="CHILD_LINK_INVITATION_REQUEST",
        receive_parent_id=parent_id,
        reference_id=link_request.id,
        image_url=sender.avatar_url
    )
    generate_notification(
        event_code="CHILD_LINK_INVITATION_SENT",
        receive_user_id=user_id,
        reference_id=parent_id
    )

    return jsonify({"message": "Link request inserted successfully"}), 201


@app.route('/api/link-requests/parent', methods=['POST'])
@validate_token
def parent_create_link_request():
    data = request.get_json()
    user_ids = data.get('user_ids')
    parent_id = data.get('parent_id')

    results = LinkRequest.create_multiple_link_requests(
        user_ids=user_ids,
        parent_id=parent_id,
        is_sent_by_parent=True
    )

    for link_request, sender, receiver in results:
        generate_notification(
            event_code="PARENT_LINK_INVITATION_REQUEST",
            receive_user_id=receiver.id,
            reference_id=link_request.id,
            image_url=sender.avatar_url
        )
        generate_notification(
            event_code="PARENT_LINK_INVITATION_SENT",
            receive_parent_id=parent_id,
            reference_id=receiver.id
        )

    return jsonify({"message": "Link request inserted successfully"}), 201


@app.route('/api/link-requests/child/confirm', methods=['PUT'])
@validate_token
def child_confirm_link_request():
    data = request.get_json()
    link_request_id = data.get('link_request_id')

    if not link_request_id:
        return jsonify({"message": "Missing link_request_id field"}), 400

    link_request, acceptor = LinkRequest.accept_link_request(link_request_id=link_request_id, acceptor="user")
    generate_notification(
        event_code="PARENT_LINK_INVITATION_ACCEPTED",
        receive_parent_id=link_request.parent_id,
        reference_id=acceptor.id,
        image_url=acceptor.avatar_url
    )

    return jsonify({"message": "Link request confirmed successfully"}), 201


@app.route('/api/link-requests/child/decline', methods=['PUT'])
@validate_token
def child_decline_link_request():
    data = request.get_json()
    link_request_id = data.get('link_request_id')

    if not link_request_id:
        return jsonify({"message": "Missing link_request_id field"}), 400

    link_request, decliner = LinkRequest.decline_link_request(link_request_id=link_request_id, decliner="user")
    generate_notification(
        event_code="PARENT_LINK_INVITATION_DECLINED",
        receive_parent_id=link_request.parent_id,
        reference_id=decliner.id,
        image_url=decliner.avatar_url
    )
    return jsonify({"message": "Link request declined successfully"}), 201


@app.route('/api/link-requests/child/cancel', methods=['PUT'])
@validate_token
def child_cancel_link_request():
    data = request.get_json()
    link_request_id = data.get('link_request_id')

    if not link_request_id:
        return jsonify({"message": "Missing link_request_id field"}), 400

    link_request, receiver = LinkRequest.cancel_link_request(link_request_id=link_request_id, canceler="user")
    if link_request.user is None or link_request.parent is None:
        return ItemNotFoundError("Link request is missing parent_id or user_id")
    send_notification_single(
        title="Connect account",
        msg="Link invitation between user {} and {} has been cancelled".format(
            link_request.user.display_name,
            link_request.parent.display_name
        ),
        registration_tokens=receiver.firebase_registration_tokens,
        data_object={"link_request_id": str(link_request_id)}
    )
    return jsonify({"message": "Link request cancelled successfully"}), 201


@app.route('/api/link-requests/parent/confirm', methods=['PUT'])
@validate_token
def parent_confirm_link_request():
    data = request.get_json()
    link_request_id = data.get('link_request_id')

    if not link_request_id:
        return jsonify({"message": "Missing link_request_id field"}), 400

    link_request, acceptor = LinkRequest.accept_link_request(link_request_id=link_request_id, acceptor="parent")
    generate_notification(
        event_code="CHILD_LINK_INVITATION_ACCEPTED",
        receive_user_id=link_request.user_id,
        reference_id=acceptor.id,
        image_url=acceptor.avatar_url
    )
    return jsonify({"message": "Link request inserted successfully"}), 201


@app.route('/api/link-requests/parent/decline', methods=['PUT'])
@validate_token
def parent_decline_link_request():
    data = request.get_json()
    link_request_id = data.get('link_request_id')
    if not link_request_id:
        return jsonify({"message": "Missing link_request_id field"}), 400

    link_request, decliner = LinkRequest.decline_link_request(link_request_id=link_request_id, decliner="parent")
    generate_notification(
        event_code="CHILD_LINK_INVITATION_DECLINED",
        receive_user_id=link_request.user_id,
        reference_id=decliner.id,
        image_url=decliner.avatar_url
    )
    return jsonify({"message": "Link request declined successfully"}), 201


@app.route('/api/link-requests/parent/cancel', methods=['PUT'])
@validate_token
def parent_cancel_link_request():
    data = request.get_json()
    link_request_id = data.get('link_request_id')

    if not link_request_id:
        return jsonify({"message": "Missing link_request_id field"}), 400

    link_request, receiver = LinkRequest.cancel_link_request(link_request_id=link_request_id, canceler="parent")
    if link_request.user is None or link_request.parent is None:
        return ItemNotFoundError("Link request is missing parent_id or user_id")
    send_notification_single(
        title="Connect account",
        msg="Link invitation between user {} and {} has been cancelled".format(
            link_request.user.display_name,
            link_request.parent.display_name
        ),
        registration_tokens=receiver.firebase_registration_tokens,
        data_object={"link_request_id": str(link_request_id)}
    )
    return jsonify({"message": "Link request cancelled successfully"}), 201


@app.route('/api/link-requests/<int:id>', methods=['PUT'])
@validate_token
def update_link_request(id):
    link_request = db.session.get(LinkRequest, id)
    if not link_request:
        return jsonify({'error': 'Link request not found'}), 404
    data = request.get_json()
    link_request.update_fields(**data)
    db.session.commit()
    return jsonify({"message": "Link request updated successfully"}), 201


@app.route('/api/link-requests/<int:id>', methods=['DELETE'])
@prohibit_access
def delete_link_request(id):
    link_request = db.session.get(LinkRequest, id)
    if not link_request:
        return jsonify({'error': 'Link request not found'}), 404
    link_request.soft_delete()
    db.session.commit()
    return jsonify({'message': 'Link request deleted'}), 200


@app.route('/api/link-requests/get-pending-requests', methods=['GET'])
@validate_token
def get_pending_requests():
    user_id = request.args.get('user_id')
    parent_id = request.args.get('parent_id')
    is_sent_by_parent = request.args.get('is_sent_by_parent', type=lambda x: x.lower() == 'true')

    query = db.session.query(LinkRequest).filter(LinkRequest.status == "PENDING")
    if user_id:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404
        query = query.filter(LinkRequest.user_id == user_id)

    if parent_id:
        parent = db.session.get(Parent, parent_id)
        if not parent:
            return jsonify({"message": "Parent not found"}), 404
        query = query.filter(LinkRequest.parent_id == parent_id)

    if is_sent_by_parent is not None:
        query = query.filter(LinkRequest.is_sent_by_parent == is_sent_by_parent)

    link_requests = query.all()
    link_requests = [link_request.to_dict() for link_request in link_requests]
    return jsonify(link_requests)
