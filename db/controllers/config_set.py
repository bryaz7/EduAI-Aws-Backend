from flask import jsonify, request
from main import db, app
from db.models.config_set import ConfigSet
from utils.auth import validate_token, prohibit_access


@app.route('/api/config_sets/<int:id>', methods=['GET'])
@validate_token
def get_config_set(id):
    config_set = db.session.get(ConfigSet, id)
    if not config_set:
        return jsonify({'error': 'ConfigSet not found'}), 404
    return jsonify(config_set.to_dict())


@app.route('/api/config_sets', methods=['POST'])
@validate_token
def create_config_set():
    data = request.get_json()
    config_set = ConfigSet.from_dict(data)
    db.session.add(config_set)
    db.session.commit()
    return jsonify({"message": "Config Set inserted successfully"}), 201


@app.route('/api/config_sets/<int:id>', methods=['PUT'])
@prohibit_access
def update_config_set(id):
    config_set = db.session.get(ConfigSet, id)
    if not config_set:
        return jsonify({'error': 'ConfigSet not found'}), 404
    data = request.get_json()
    config_set.update_fields(**data)
    db.session.commit()
    return jsonify({"message": "ConfigSet updated successfully"}), 201


@app.route('/api/config_sets/<int:id>', methods=['DELETE'])
@prohibit_access
def delete_config_set(id):
    config_set = db.session.get(ConfigSet, id)
    if not config_set:
        return jsonify({'error': 'ConfigSet not found'}), 404
    config_set.soft_delete()
    db.session.commit()
    return jsonify({'message': 'ConfigSet deleted'}), 200
