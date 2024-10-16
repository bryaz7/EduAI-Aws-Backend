from db.models.base_table import BaseTable
from db.extension import db


class PersonAISkills(BaseTable):
    __tablename__ = "person_ai_skill"

    id = db.Column(db.Integer, primary_key=True)
    person_ai_id = db.Column(db.Integer, db.ForeignKey('person_ai.id', ondelete='CASCADE'))
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id', ondelete='CASCADE'))
    skill_weight = db.Column(db.Float)

    # skill = db.relationship('Skills', backref=db.backref('skill_person_ai_skill', cascade='all, delete'))
    # person_ai = db.relationship('PersonAIs', backref=db.backref('person_ai_person_ai_skill', cascade='all, delete'))
