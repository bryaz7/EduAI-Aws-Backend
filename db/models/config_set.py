from db.models.base_table import BaseTable
from db.extension import db


class ConfigSet(BaseTable):
    __tablename__ = "config_set"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id', ondelete='CASCADE'))

    # skill = db.relationship('Skills', backref=db.backref('config_set_skill', cascade='all, delete'))
