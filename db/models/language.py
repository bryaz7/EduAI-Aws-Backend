from db.models.base_table import BaseTable
from db.extension import db


class Language(BaseTable):
    __tablename__ = "language"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    code = db.Column(db.String(8))
    image_url = db.Column(db.String(255))
