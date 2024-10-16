from db.models.base_table import BaseTable
from db.extension import db


class ConfigInstance(BaseTable):
    __tablename__ = "config_instance"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(255))
    value = db.Column(db.String(64))
    config_set_id = db.Column(db.Integer, db.ForeignKey('config_set.id', ondelete='CASCADE'))

    # config_set = db.relationship('ConfigSet', backref=db.backref('config_config_set', cascade='all, delete'))
