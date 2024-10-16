from db.extension import db
from db.models.base_table import BaseTable


class NotificationTemplate(BaseTable):
    __tablename__ = "notification_template"

    id = db.Column(db.Integer, primary_key=True)
    event_code = db.Column(db.String(255))
    title = db.Column(db.String(255))
    description = db.Column(db.String(255))
    notification_type = db.Column(db.String(255))
    reference_type = db.Column(db.String(255))
    redirect_url = db.Column(db.String(255))
    is_pop_up_pushed = db.Column(db.Boolean)
