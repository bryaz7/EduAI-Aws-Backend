from flask import jsonify, request

from db.models import Parent
from db.services.user_person_ai import UserPersonAIService
from main import db, app

from db.models.user_person_ai import UserPersonAI
from db.models.person_ai import PersonAIs
from db.models.user import User
from utils.auth import validate_token, prohibit_access
from utils.enum.role import AppRole
from utils.exceptions import BadRequestError
from utils.warns import deprecated


@app.route('/api/user_person_ai', methods=['POST'])
@prohibit_access
def create_user_person_ai():
    data = request.get_json()
    person_ai_id = data.get('person_ai_id')
    user_id = data.get('user_id')

    person_ai = db.session.get(PersonAIs, person_ai_id)
    user = db.session.get(User, user_id)
    if not person_ai or not user:
        return jsonify({'message': 'PersonAI or User not found.'}), 404

    user_person_ai = UserPersonAI.from_dict(data)
    db.session.add(user_person_ai)
    db.session.commit()

    return jsonify({'message': 'UserPersonAI created successfully.'}), 201


@app.route('/api/user_person_ai/<int:user_person_ai_id>', methods=['GET'])
@validate_token
def get_user_person_ai(user_person_ai_id):
    user_person_ai = db.session.get(UserPersonAI, user_person_ai_id)
    if not user_person_ai:
        return jsonify({'message': 'UserPersonAI not found.'}), 404
    return jsonify(user_person_ai.to_dict())


@app.route('/api/user_person_ai/<int:user_person_ai_id>', methods=['PUT'])
@prohibit_access
def update_user_person_ai(user_person_ai_id):
    user_person_ai = db.session.get(UserPersonAI, user_person_ai_id)
    if not user_person_ai:
        return jsonify({'message': 'UserPersonAI not found.'}), 404

    data = request.get_json()
    person_ai_id = data.get('person_ai_id')
    user_id = data.get('user_id')

    person_ai = db.session.get(PersonAIs, person_ai_id)
    user = db.session.get(User, user_id)
    if not person_ai or not user:
        return jsonify({'message': 'PersonAI or User not found.'}), 404

    user_person_ai.person_ai_id = person_ai_id
    user_person_ai.user_id = user_id
    db.session.commit()

    return jsonify({'message': 'UserPersonAI updated successfully.'})


@app.route('/api/user_person_ai/<int:user_person_ai_id>', methods=['DELETE'])
@prohibit_access
def delete_user_person_ai(user_person_ai_id):
    user_person_ai = db.session.get(UserPersonAI, user_person_ai_id)
    if not user_person_ai:
        return jsonify({'message': 'UserPersonAI not found.'}), 404

    user_person_ai.soft_delete()
    db.session.commit()

    return jsonify({'message': 'UserPersonAI deleted successfully.'})


@app.route("/api/user_person_ai/user_person_ai_by_user", methods=["GET"])
@validate_token
def user_get_person_ai():
    # Define user_id
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        raise BadRequestError("Missing user_id field")

    # Define default values and extract query parameters
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')
    category_id = request.args.get('category_id')
    education = request.args.get('education')

    person_ais = UserPersonAIService.get_person_ai_by_user_id(category_id, education, search_query,
                                                              sort_by, sort_order, user_id, AppRole.USER)

    return jsonify(person_ais)


@app.route("/api/user_person_ai/user_person_ai_by_parent", methods=["GET"])
@validate_token
def parent_get_person_ai():
    # Define user_id
    parent_id = request.args.get('parent_id', type=int)
    if not parent_id:
        raise BadRequestError("Missing parent_id field")

    # Define default values and extract query parameters
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')
    category_id = request.args.get('category_id')
    education = request.args.get('education')

    person_ais = UserPersonAIService.get_person_ai_by_user_id(category_id, education, search_query,
                                                              sort_by, sort_order, parent_id, AppRole.PARENT)

    return jsonify(person_ais)


@deprecated([user_get_person_ai, parent_get_person_ai])
@app.route("/api/user_person_ai_by_user", methods=["GET"])
@validate_token
def get_person_ai_by_user():
    # Define user_id
    user_id = request.args.get('user_id')

    # Define default values and extract query parameters
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')
    category_id = request.args.get('category_id')
    education = request.args.get('education')

    person_ais = UserPersonAIService.get_person_ai_by_user_id(category_id, education, search_query,
                                                              sort_by, sort_order, user_id, AppRole.USER)

    return jsonify(person_ais)


@app.route("/api/user_person_ai/user-pre-check-to-create-chat", methods=['GET'])
@validate_token
def user_pre_check_to_create_chat():
    user_id = request.args.get('user_id', type=int)
    person_ai_id = request.args.get('person_ai_id', type=int)

    user_person_ais = UserPersonAI.get_by_user_id(user_id)
    person_ai_ids = set([user_person_ai.person_ai_id for user_person_ai in user_person_ais])
    if person_ai_id in person_ai_ids:
        return jsonify({'can_create': True})

    package = User.get_active_package(user_id)
    n_users = len(person_ai_ids)
    if n_users + 1 > package.character_limit:
        return jsonify({'message': "Number of characters exceed package limit, try to upgrade to a better one"}), 402
    else:
        return jsonify({'can_create': True})


@app.route("/api/user_person_ai/parent-pre-check-to-create-chat", methods=['GET'])
@validate_token
def parent_pre_check_to_create_chat():
    parent_id = request.args.get('parent_id', type=int)
    person_ai_id = request.args.get('person_ai_id', type=int)

    user_person_ais = UserPersonAI.get_by_parent_id(parent_id)
    person_ai_ids = set([user_person_ai.person_ai_id for user_person_ai in user_person_ais])
    if person_ai_id in person_ai_ids:
        return jsonify({'can_create': True})

    package = Parent.get_active_package(parent_id)
    n_users = len(person_ai_ids)
    if not package.can_parent_chat:
        return jsonify({"message": "Parent cannot chat in this package, try to upgrade to a better one"}), 402
    if n_users + 1 > package.character_limit:
        return jsonify({'message': "Number of characters exceed package limit, try to upgrade to a better one"}), 402
    else:
        return jsonify({'can_create': True})


@deprecated([user_pre_check_to_create_chat, parent_pre_check_to_create_chat])
@app.route("/api/pre-check-to-create-chat", methods=['POST'])
@validate_token
def pre_check_to_create_chat():
    data = request.get_json()
    user_id = data.get('user_id')
    person_ai_id = data.get('person_ai_id')

    user_person_ais = UserPersonAI.get_by_user_id(user_id)
    person_ai_ids = set([user_person_ai.person_ai_id for user_person_ai in user_person_ais])
    if person_ai_id in person_ai_ids:
        return jsonify({'can_create': True})

    package = User.get_active_package(user_id)
    n_users = len(person_ai_ids)
    if n_users + 1 > package.character_limit:
        return jsonify({'message': "Number of characters exceed package limit, try to upgrade to a better one"}), 402
    else:
        return jsonify({'can_create': True})
