from db.models.base_table import BaseTable
from db.extension import db


class AppReport(BaseTable):
    __tablename__ = "app_report"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete='CASCADE'))
    category = db.Column(db.String(255))
    detail = db.Column(db.String(1024))
    media = db.Column(db.JSON)
