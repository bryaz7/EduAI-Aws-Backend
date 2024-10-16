from db.models.base_table import BaseTable
from db.extension import db


class DrawStyle(BaseTable):
    __tablename__ = "draw_style"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    example = db.Column(db.String(255))
    image_url = db.Column(db.String(255))