from db.extension import db
from db.models.base_table import BaseTable


class Mail(BaseTable):
    __tablename__ = "mails"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(255))
    recipient = db.Column(db.String(255))
    status = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id', ondelete='CASCADE'))

    @staticmethod
    def is_mail_bounced_or_complained_over_limit(address: str, limit: int = 2) -> bool:
        bounce_records = db.session.query(Mail) \
            .filter(Mail.recipient == address, Mail.status.in_(["Bounce", "Complaint"])) \
            .all()
        return len(bounce_records) >= limit
