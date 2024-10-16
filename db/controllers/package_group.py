from flask import jsonify, request
from main import db, app
from db.models import PackageGroup
from utils.auth import validate_token
from utils.exceptions import ItemNotFoundError


@app.route('/api/package-groups', methods=['POST'])
@validate_token
def create_package_group():
    data = request.get_json()
    package_group = PackageGroup.from_dict(data)
    db.session.add(package_group)
    db.session.commit()
    return jsonify({'message': 'Package group created successfully.'}), 201


@app.route('/api/package-groups/<int:package_group_id>', methods=['GET'])
@validate_token
def get_package_group(package_group_id):
    detailed = request.args.get('detailed', type=lambda x: x.lower() == 'true')
    if detailed:
        try:
            package_group_detail = PackageGroup.get_package_group_details(package_group_id)
        except ItemNotFoundError as e:
            return jsonify({"message": str(e)}), 404
        return jsonify(package_group_detail)
    else:
        package_group = db.session.get(PackageGroup, package_group_id)
        if not package_group:
            return jsonify({'message': 'Package group not found.'}), 404
        return jsonify(package_group.to_dict())


@app.route('/api/package-groups/<int:package_group_id>', methods=['PUT'])
@validate_token
def update_package_group(package_group_id):
    package_group = db.session.get(PackageGroup, package_group_id)
    if not package_group:
        return jsonify({'message': 'Package group not found.'}), 404

    data = request.get_json()
    package_group.update_fields(**data)
    db.session.commit()

    return jsonify({'message': 'Package group updated successfully.'})


@app.route('/api/package-groups/<int:package_group_id>', methods=['DELETE'])
@validate_token
def delete_package_group(package_group_id):
    package_group = db.session.get(PackageGroup, package_group_id)
    if not package_group:
        return jsonify({'message': 'Package group not found.'}), 404

    package_group.soft_delete()
    db.session.commit()

    return jsonify({'message': 'Package group deleted successfully.'})
