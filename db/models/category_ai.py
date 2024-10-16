from db.models.base_table import BaseTable
from db.extension import db


class CategoryAI(BaseTable):
    __tablename__ = "category_ai"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
