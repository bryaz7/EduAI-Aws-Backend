from flask import jsonify, request
from sqlalchemy import or_
from main import db, app
from db.models.category_ai import CategoryAI
from db.models.person_ai import PersonAIs
from db.models.person_ai_skill import PersonAISkills
from db.models.skills import Skills
from utils.auth import validate_token, prohibit_access


@app.route('/api/person_ai', methods=['POST'])
@prohibit_access
def create_person_ai():
    data = request.get_json()
    category_id = data.get('category_id')

    category = db.session.get(CategoryAI, category_id)
    if not category:
        return jsonify({'message': 'CategoryAI not found.'}), 404

    person_ai = PersonAIs.from_dict(data)
    db.session.add(person_ai)
    db.session.commit()

    return jsonify({'message': 'PersonAI created successfully.'}), 201


@app.route('/api/person_ai/<int:person_ai_id>', methods=['GET'])
@validate_token
def get_person_ai(person_ai_id):
    person_ai = db.session.get(PersonAIs, person_ai_id)
    if not person_ai:
        return jsonify({'message': 'PersonAI not found.'}), 404

    # Retrieve the associated CategoryAI record
    category = db.session.get(CategoryAI, person_ai.category_id)

    # Retrieve the associated Skills records
    skills = db.session.query(Skills, PersonAISkills).join(
        PersonAISkills, PersonAISkills.skill_id == Skills.id
    ).filter(
        PersonAISkills.person_ai_id == person_ai_id
    ).all()

    person_ai_dict = person_ai.to_dict()
    person_ai_dict.update({
        'skills': [{
            'skill_name': skill.Skills.name,
            'skill_weight': skill.PersonAISkills.skill_weight}
            for skill in skills],
        'category': category.to_dict()
    })

    return jsonify(person_ai_dict)


@app.route('/api/person_ai/<int:person_ai_id>', methods=['PUT'])
@prohibit_access
def update_person_ai(person_ai_id):
    person_ai = db.session.get(PersonAIs, person_ai_id)
    if not person_ai:
        return jsonify({'message': 'PersonAI not found.'}), 404

    data = request.get_json()
    category_id = data.get('category_id')

    category = db.session.get(CategoryAI, category_id)
    if not category:
        return jsonify({'message': 'CategoryAI not found.'}), 404

    person_ai.update_fields(**data)
    db.session.commit()

    return jsonify({'message': 'PersonAI updated successfully.'})


@app.route('/api/person_ai/<int:person_ai_id>', methods=['DELETE'])
@prohibit_access
def delete_person_ai(person_ai_id):
    person_ai = db.session.get(PersonAIs, person_ai_id)
    if not person_ai:
        return jsonify({'message': 'PersonAI not found.'}), 404

    person_ai.soft_delete()
    db.session.commit()

    return jsonify({'message': 'PersonAI deleted successfully.'})


@app.route('/api/person_ai', methods=['GET'])
def get_person_ais():
    # Define default values and extract query parameters
    default_page = 1
    default_per_page = 10
    page = int(request.args.get('page', default_page))
    per_page = int(request.args.get('per_page', default_per_page))
    search_query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')

    # Apply filters, if provided
    category_id = request.args.get('category_id')
    filters = []
    if category_id:
        filters.append(PersonAIs.category_id == category_id)

    # Education filter
    education = request.args.get('education')
    if education:
        filters.append(PersonAIs.education == education)

    # Apply search query, if provided
    search_filters = []
    if search_query:
        search_filters.append(PersonAIs.name.ilike(f"%{search_query}%"))

    # Construct the base query
    base_query = db.session.query(PersonAIs)
    if filters:
        base_query = base_query.filter(*filters)
    if search_filters:
        base_query = base_query.filter(or_(*search_filters))

    # Determine the total number of results
    total_count = base_query.count()

    # Apply sorting
    sort_column = getattr(PersonAIs, sort_by)
    if sort_order == 'asc':
        base_query = base_query.order_by(sort_column)
    else:
        base_query = base_query.order_by(sort_column.desc())

    # Apply pagination
    person_ais = base_query.paginate(page=page, per_page=per_page).items

    # Fetch skills separately for each PersonAI
    person_ai_data = []
    for person_ai in person_ais:
        output = db.session.query(Skills, PersonAISkills).join(
            PersonAISkills, PersonAISkills.skill_id == Skills.id
        ).filter(
            PersonAISkills.person_ai_id == person_ai.id
        ).all()

        person_ai = person_ai.to_dict()
        skills = []
        for skill, person_ai_skill in output:
            skill = skill.to_dict()
            skill.update({"skill_weight": person_ai_skill.skill_weight})
            skills.append(skill)
        person_ai.update({'skills': skills})
        person_ai_data.append(person_ai)

    # Prepare the response
    response = {
        'page': page,
        'per_page': per_page,
        'total_count': total_count,
        'person_ais': person_ai_data
    }
    return jsonify(response)
