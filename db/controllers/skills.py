from flask import jsonify, request
from main import db, app
from db.models.skills import Skills
from utils.auth import validate_token, prohibit_access


@app.route('/api/skills', methods=['POST'])
@prohibit_access
def create_skill():
    data = request.get_json()
    skill = Skills.from_dict(data)
    db.session.add(skill)
    db.session.commit()
    return jsonify({'message': 'Skill created successfully.'}), 201


@app.route('/api/skills/<int:skill_id>', methods=['GET'])
def get_skill(skill_id):
    skill = db.session.get(Skills, skill_id)
    if not skill:
        return jsonify({'message': 'Skill not found.'}), 404
    return jsonify(skill.to_dict())


@app.route('/api/skills/<int:skill_id>', methods=['PUT'])
@prohibit_access
def update_skill(skill_id):
    skill = db.session.get(Skills, skill_id)
    if not skill:
        return jsonify({'message': 'Skill not found.'}), 404

    data = request.get_json()
    skill.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'Skill updated successfully.'})


@app.route('/api/skills/<int:skill_id>', methods=['DELETE'])
@validate_token
def delete_skill(skill_id):
    skill = db.session.get(Skills, skill_id)
    if not skill:
        return jsonify({'message': 'Skill not found.'}), 404

    skill.soft_delete()
    db.session.commit()
    return jsonify({'message': 'Skill deleted successfully.'})
