from botocore.exceptions import ClientError
from flask import jsonify, request

from main import db, app
from db.models.user_person_ai import UserPersonAI
from db.models.history_message import HistoryMessage
from services.aws_service import query_message_record
from utils.auth import validate_token
from utils.exceptions import MediaNotFoundError, BadRequestError, ItemNotFoundError
from services.aws_service import delete_item_on_message_history


@app.route('/api/delete_message', methods=['DELETE'])
@validate_token
def delete_message():
    data = request.get_json()
    history_message_id = data.get('history_message_id')
    timestamp = data.get('timestamp')

    result = delete_item_on_message_history(history_message_id, timestamp)
    if not result:
        return jsonify({'message': 'Delete failed'}), 404
    # user_person_ai = db.session.get(UserPersonAI, user_person_ai_id)
    # if not user_person_ai:
    #     return jsonify({'message': 'UserPersonAI not found.'}), 404

    # history_message = HistoryMessage.from_dict(data)
    # db.session.add(history_message)
    # db.session.commit()
    return jsonify({'message': 'Message deleted successfully.'}), 202


@app.route('/api/history_message', methods=['POST'])
@validate_token
def create_history_message():
    data = request.get_json()
    user_person_ai_id = data.get('user_person_ai_id')

    user_person_ai = db.session.get(UserPersonAI, user_person_ai_id)
    if not user_person_ai:
        return jsonify({'message': 'UserPersonAI not found.'}), 404

    history_message = HistoryMessage.from_dict(data)
    db.session.add(history_message)
    db.session.commit()
    return jsonify({'message': 'HistoryMessage created successfully.'}), 201


@app.route('/api/history_message/<int:message_id>', methods=['GET'])
@validate_token
def get_history_message(message_id):
    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found.'}), 404
    return jsonify(history_message.to_dict())


@app.route('/api/history_message/<int:message_id>', methods=['PUT'])
@validate_token
def update_history_message(message_id):
    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found.'}), 404

    data = request.get_json()
    user_person_ai_id = data.get('user_person_ai_id')

    user_person_ai = db.session.get(UserPersonAI, user_person_ai_id)
    if not user_person_ai:
        return jsonify({'message': 'UserPersonAI not found.'}), 404

    history_message.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'HistoryMessage updated successfully.'})


@app.route('/api/history_message/<int:message_id>', methods=['DELETE'])
@validate_token
def delete_history_message(message_id):
    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'Chatbox not found.'}), 404

    history_message.soft_delete()
    db.session.commit()
    return jsonify({'message': 'Chatbox soft-deleted successfully.'})


@app.route('/api/get-media-from-history/<int:message_id>', methods=['GET'])
@validate_token
def get_media_from_history(message_id):
    media = HistoryMessage.get_media_by_id(message_id)
    if not media:
        return jsonify({'message': 'HistoryMessage not found.'}), 404
    return jsonify(media)


@app.route('/api/get-note-from-history/<int:message_id>', methods=['GET'])
@validate_token
def get_notes_from_history(message_id):
    notes = HistoryMessage.get_notes_by_id(message_id)
    if not notes:
        return jsonify({'message': 'HistoryMessage not found.'}), 404
    return jsonify(notes)


@app.route('/api/get-files-from-history/<int:message_id>', methods=['GET'])
@validate_token
def get_files_from_history(message_id):
    files = HistoryMessage.get_files_by_id(message_id)
    if not files:
        return jsonify({'message': 'HistoryMessage not found'}), 404
    return jsonify(files)


@app.route('/api/update-note', methods=['PUT'])
@validate_token
def update_note():
    data = request.get_json()
    note = data.get('note')
    message_id = data.get('message_id')
    index = data.get('index')

    if not note:
        return jsonify({'message': 'Missing note field'}), 400

    if index is None:
        return jsonify({'message': 'Missing index field'}), 400

    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found'}), 404

    try:
        temp_list = [i for i in history_message.note]
        temp_list[index] = note
        history_message.note = temp_list
        db.session.commit()
    except IndexError:
        return jsonify({'message': 'Index out of range'}), 400

    return jsonify({'message': 'Note modified successfully'})


@app.route('/api/add-note', methods=['PUT'])
@validate_token
def add_note():
    data = request.get_json()
    note = data.get('note')
    timestamp = data.get('timestamp')
    message_id = data.get('message_id')

    if not note:
        raise BadRequestError("Missing note field")
    if not timestamp:
        raise BadRequestError("Missing timestamp field")

    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found'}), 404

    history_message.append_note(note, timestamp)
    return jsonify({'message': 'Note added successfully'})


@app.route("/api/history_message/check-note-is-saved", methods=['GET'])
@validate_token
def check_note_is_saved():
    timestamp = request.args.get('timestamp')
    message_id = request.args.get('message_id', type=int)

    if not message_id:
        raise BadRequestError("Missing message_id field")
    if not timestamp:
        raise BadRequestError("Missing timestamp field")

    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        raise ItemNotFoundError("History message not found")

    is_note_saved = history_message.check_note_is_saved(timestamp)
    return jsonify({"is_saved": is_note_saved})


@app.route('/api/remove-note', methods=['PUT'])
@validate_token
def remove_note():
    data = request.get_json()
    message_id = data.get('message_id')
    index = data.get('index')

    if index is None:
        return jsonify({'message': 'Missing index field'}), 400

    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found'}), 404

    try:
        temp_list = [i for i in history_message.note]
        temp_list.pop(index)
        history_message.note = temp_list
        db.session.commit()
    except IndexError:
        return jsonify({'message': 'Index out of range'}), 400
    return jsonify({'message': 'Note removed successfully'})


@app.route('/api/remove-media', methods=['PUT'])
@validate_token
def remove_media():
    data = request.get_json()
    message_id = data.get('message_id')
    media_url = data.get('media_url')
    if not media_url:
        return jsonify({'message': 'Media URL field is empty'}), 400
    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found'}), 404
    try:
        history_message.delete_media(media_url)
        return jsonify({'message': 'Delete media from message history successfully'})
    except ClientError as e:
        return jsonify({'message': f'Exception from the cloud server with detail: {e}'}), 500
    except MediaNotFoundError as e:
        return jsonify({'message': f'Media not found with detail: {e}'}), 500
    except Exception as e:
        return jsonify({'message': f'Unexpected error occurred: {e}'}), 500


@app.route('/api/get-message-history-id-by-user-id-and-person-ai-id', methods=['GET'])
@validate_token
def get_message_history_id_by_user_id_and_person_ai_id():
    user_id = int(request.args.get('user_id', None))
    person_ai_id = int(request.args.get('person_ai_id', None))

    if not user_id or not person_ai_id:
        return jsonify({'error': 'Missing required fields'}), 400

    user_person_ai_id = UserPersonAI.get_user_person_ai_by_user(user_id, person_ai_id)
    if not user_person_ai_id:
        return jsonify({'error': 'UserPersonAI not found'}), 404

    history_message = HistoryMessage.get_by_user_person_ai_id(user_person_ai_id)
    if not history_message:
        return jsonify({'error': 'HistoryMessage not found'}), 404

    result = {
        'user_id': user_id,
        'person_ai_id': person_ai_id,
        'history_message_id': history_message.id
    }
    return jsonify(result)


@app.route('/api/get-size/<int:message_id>', methods=['GET'])
@validate_token
def get_size(message_id):
    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found'}), 404
    size_in_bytes = history_message.get_size()  # Size in bytes
    size_in_megabytes = size_in_bytes / 1024 / 1024
    return jsonify({
        'message_id': message_id,
        'size': size_in_megabytes
    })


@app.route('/api/search-history-message', methods=['GET'])
@validate_token
def search_history_message():
    message_id = request.args.get('message_id')
    q = request.args.get('q')

    history_message = db.session.get(HistoryMessage, message_id)
    if not history_message:
        return jsonify({'message': 'HistoryMessage not found'}), 404

    try:
        result = query_message_record(message_id, q)
        return jsonify(result)
    except ClientError as e:
        return jsonify({'message': f'Error occurred when performing query. Details: {e}'}), 510
    except Exception as e:
        return jsonify({'message': f'Unexpected error occurred. Details: {e}'}), 510
