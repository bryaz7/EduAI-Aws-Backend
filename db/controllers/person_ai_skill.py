from flask import jsonify, request
from main import db, app
from db.models.person_ai import PersonAIs
from db.models.skills import Skills
from db.models.person_ai_skill import PersonAISkills
from utils.auth import prohibit_access


@app.route('/api/person_ai_skills', methods=['POST'])
@prohibit_access
def create_person_ai_skill():
    data = request.get_json()
    person_ai_id = data.get('person_ai_id')
    skill_id = data.get('skill_id')

    person_ai = db.session.get(PersonAIs, person_ai_id)
    if not person_ai:
        return jsonify({'message': 'PersonAI not found.'}), 404

    skill = db.session.get(Skills, skill_id)
    if not skill:
        return jsonify({'message': 'Skill not found.'}), 404

    person_ai_skill = PersonAISkills.from_dict(data)
    db.session.add(person_ai_skill)
    db.session.commit()

    return jsonify({'message': 'PersonAI Skill created successfully.'}), 201


@app.route('/api/person_ai_skills/<int:person_ai_skill_id>', methods=['GET'])
def get_person_ai_skill(person_ai_skill_id):
    person_ai_skill = db.session.get(PersonAISkills, person_ai_skill_id)
    if not person_ai_skill:
        return jsonify({'message': 'PersonAI Skill not found.'}), 404
    return jsonify(person_ai_skill.to_dict())


@app.route('/api/person_ai_skills/<int:person_ai_skill_id>', methods=['PUT'])
@prohibit_access
def update_person_ai_skill(person_ai_skill_id):
    person_ai_skill = db.session.get(PersonAISkills, person_ai_skill_id)
    if not person_ai_skill:
        return jsonify({'message': 'PersonAI Skill not found.'}), 404

    data = request.get_json()
    person_ai_id = data.get('person_ai_id')
    skill_id = data.get('skill_id')

    person_ai = PersonAIs.query.get(person_ai_id)
    if not person_ai:
        return jsonify({'message': 'PersonAI not found.'}), 404

    skill = Skills.query.get(skill_id)
    if not skill:
        return jsonify({'message': 'Skill not found.'}), 404

    person_ai_skill.update_fields(**data)
    db.session.commit()
    return jsonify({'message': 'PersonAI Skill updated successfully.'})


@app.route('/api/person_ai_skills/<int:person_ai_skill_id>', methods=['DELETE'])
@prohibit_access
def delete_person_ai_skill(person_ai_skill_id):
    person_ai_skill = db.session.get(PersonAISkills, person_ai_skill_id)
    if not person_ai_skill:
        return jsonify({'message': 'PersonAI Skill not found.'}), 404

    person_ai_skill.soft_delete()
    db.session.commit()

    return jsonify({'message': 'PersonAI Skill deleted successfully.'})
