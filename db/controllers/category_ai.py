from flask import jsonify, request
from main import db, app
from db.models.category_ai import CategoryAI
from utils.auth import validate_token, prohibit_access


@app.route('/api/categories', methods=['POST'])
@validate_token
def create_category():
    data = request.get_json()
    category = CategoryAI.from_dict(data)
    db.session.add(category)
    db.session.commit()
    return jsonify({'message': 'Category created successfully.'}), 201


@app.route('/api/categories', methods=['GET'])
def get_all_categories():
    categories = db.session.query(CategoryAI).all()
    categories = [category.to_dict() for category in categories]
    if not categories:
        return jsonify({'message': 'No category found.'}), 404
    return categories


@app.route('/api/categories/<int:category_id>', methods=['GET'])
def get_category(category_id):
    category = db.session.get(CategoryAI, category_id)
    if not category:
        return jsonify({'message': 'Category not found.'}), 404
    return jsonify(category.to_dict())


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@prohibit_access
def update_category(category_id):
    category = db.session.get(CategoryAI, category_id)
    if not category:
        return jsonify({'message': 'Category not found.'}), 404
    data = request.get_json()
    category.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'Category updated successfully.'})


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@prohibit_access
def delete_category(category_id):
    category = db.session.get(CategoryAI, category_id)
    if not category:
        return jsonify({'message': 'Category not found.'}), 404
    category.soft_delete()
    db.session.commit()
    return jsonify({'message': 'Category deleted successfully.'})
