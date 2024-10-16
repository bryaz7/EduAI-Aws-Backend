from db.models.base_table import BaseTable
from db.extension import db


class Skills(BaseTable):
    __tablename__ = "skill"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    descriptions = db.Column(db.String(255))

    person_ai_skills = db.relationship("PersonAISkills", cascade="all, delete")
