from db.models.base_table import BaseTable
from db.extension import db


class PersonAIs(BaseTable):
    __tablename__ = "person_ai"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    place_of_birth = db.Column(db.String(255))
    date_of_birth = db.Column(db.String(255))
    education = db.Column(db.String(255))
    title = db.Column(db.String(255))
    description = db.Column(db.String(1000))
    welcome_messages = db.Column(db.JSON)
    guideline_next_questions = db.Column(db.JSON)
    quote = db.Column(db.String(255))
    inspired_character = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey("category_ai.id", ondelete="SET NULL"))
    is_promoted = db.Column(db.Boolean)
    voice = db.Column(db.String(255))

    person_ai_skills = db.relationship("PersonAISkills", cascade="all, delete")
    user_person_ais = db.relationship("UserPersonAI", cascade="all, delete")

    @staticmethod
    def get_name_by_id(person_ai_id):
        return db.session.get(PersonAIs, person_ai_id).name
