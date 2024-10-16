from flask import jsonify, request
from main import db, app
from db.models.package import Package
from utils.auth import validate_token, prohibit_access


@app.route('/api/packages', methods=['POST'])
@validate_token
def create_package():
    data = request.get_json()
    package = Package.from_dict(data)
    db.session.add(package)
    db.session.commit()
    return jsonify({'message': 'Package created successfully.'}), 201


@app.route('/api/packages/<int:package_id>', methods=['GET'])
def get_package(package_id):
    package = db.session.get(Package, package_id)
    if not package:
        return jsonify({'message': 'Package not found.'}), 404
    return jsonify(package.to_dict())


@app.route('/api/packages/<int:package_id>', methods=['PUT'])
@validate_token
def update_package(package_id):
    package = db.session.get(Package, package_id)
    if not package:
        return jsonify({'message': 'Package not found.'}), 404

    data = request.get_json()
    package.update_fields(**data)
    db.session.commit()

    return jsonify({'message': 'Package updated successfully.'})


@app.route('/api/packages/<int:package_id>', methods=['DELETE'])
@prohibit_access
def delete_package(package_id):
    package = db.session.get(Package, package_id)
    if not package:
        return jsonify({'message': 'Package not found.'}), 404

    package.soft_delete()
    db.session.commit()

    return jsonify({'message': 'Package deleted successfully.'})
