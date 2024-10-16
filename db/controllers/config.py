from flask import jsonify, request
from main import db, app
from db.models.config import ConfigInstance
from utils.auth import validate_token, prohibit_access


@app.route('/api/config_instances/<int:id>', methods=['GET'])
@validate_token
def get_config_instance(id):
    config_instance = db.session.get(ConfigInstance, id)
    if not config_instance:
        return jsonify({'error': 'ConfigInstance not found'}), 404
    return jsonify(config_instance.to_dict())


@app.route('/api/config_instances', methods=['POST'])
@validate_token
def create_config_instance():
    data = request.get_json()
    config_instance = ConfigInstance.from_dict(data)
    db.session.add(config_instance)
    db.session.commit()
    return jsonify({'message': 'Create configuration instance successfully'}), 201


@app.route('/api/config_instances/<int:id>', methods=['PUT'])
@validate_token
def update_config_instance(id):
    config_instance = db.session.get(ConfigInstance, id)
    if not config_instance:
        return jsonify({'error': 'ConfigInstance not found'}), 404
    data = request.get_json()
    config_instance.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'Create ConfigInstance successfully'})


@app.route('/api/config_instances/<int:id>', methods=['DELETE'])
@prohibit_access
def delete_config_instance(id):
    config_instance = db.session.get(ConfigInstance, id)
    if not config_instance:
        return jsonify({'error': 'ConfigInstance not found'}), 404
    config_instance.soft_delete()
    db.session.commit()
    return jsonify({'message': 'ConfigInstance deleted'}), 200
