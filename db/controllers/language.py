from flask import jsonify, request
from main import db, app
from db.models import Language
from utils.auth import validate_token, prohibit_access


@app.route('/api/languages/<int:id>', methods=['GET'])
@validate_token
def get_language(id):
    language = db.session.get(Language, id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404
    return jsonify(language.to_dict())


@app.route('/api/languages', methods=['POST'])
@validate_token
def create_language():
    data = request.get_json()
    language = Language.from_dict(data)
    db.session.add(language)
    db.session.commit()
    return jsonify({'message': 'Create language successfully'}), 201


@app.route('/api/languages/<int:id>', methods=['PUT'])
@prohibit_access
def update_language(id):
    language = db.session.get(Language, id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404
    data = request.get_json()
    language.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'Create Language successfully'})


@app.route('/api/languages/<int:id>', methods=['DELETE'])
@prohibit_access
def delete_language(id):
    language = db.session.get(Language, id)
    if not language:
        return jsonify({'error': 'Language not found'}), 404
    language.soft_delete()
    db.session.commit()
    return jsonify({'message': 'Language deleted'}), 200


@app.route('/api/languages', methods=['GET'])
@validate_token
def get_language_from_name_list():
    language_names = request.args.get('languages').split(',')
    languages = db.session.query(Language).filter(
        Language.name.in_(language_names)
    ).all()
    languages = [language.to_dict() for language in languages]
    return jsonify(languages)
