from flask import jsonify, request
from db.models.draw_style import DrawStyle
from main import db, app
from utils.auth import validate_token, prohibit_access


@app.route('/api/draw_styles', methods=['POST'])
@validate_token
def create_draw_style():
    data = request.get_json()
    draw_style = DrawStyle.from_dict(data)
    db.session.add(draw_style)
    db.session.commit()
    return jsonify({'message': 'DrawStyle created successfully.'}), 201


@app.route('/api/draw_styles/<int:draw_style_id>', methods=['GET'])
@validate_token
def get_draw_style(draw_style_id):
    draw_style = db.session.get(DrawStyle, draw_style_id)
    if not draw_style:
        return jsonify({'message': 'DrawStyle not found.'}), 404
    return jsonify(draw_style.to_dict())


@app.route('/api/draw_styles', methods=['GET'])
@validate_token
def get_all_draw_styles():
    draw_styles = db.session.query(DrawStyle).all()
    draw_styles = [draw_style.to_dict() for draw_style in draw_styles]
    if not draw_styles:
        return jsonify({'message': 'No draw style found.'}), 404
    return draw_styles


@app.route('/api/draw_styles/<int:draw_style_id>', methods=['PUT'])
@prohibit_access
def update_draw_style(draw_style_id):
    draw_style = db.session.get(DrawStyle, draw_style_id)
    if not draw_style:
        return jsonify({'message': 'DrawStyle not found.'}), 404

    data = request.get_json()
    draw_style.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'DrawStyle updated successfully.'})


@app.route('/api/draw_styles/<int:draw_style_id>', methods=['DELETE'])
@prohibit_access
def delete_draw_style(draw_style_id):
    draw_style = db.session.get(DrawStyle, draw_style_id)
    if not draw_style:
        return jsonify({'message': 'DrawStyle not found.'}), 404

    draw_style.soft_delete()
    db.session.commit()
    return jsonify({'message': 'DrawStyle deleted successfully.'})
