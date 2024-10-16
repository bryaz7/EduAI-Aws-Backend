from db.extension import db
from db.models import LinkRequest
from db.models.base_table import BaseTable


class Notification(BaseTable):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='cascade'))
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id', ondelete='cascade'))
    title = db.Column(db.String(255))
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    is_read = db.Column(db.Boolean)
    notification_type = db.Column(db.String(255))  # Type: INFO, LINK_REQUEST
    reference_type = db.Column(db.String(255))  # Type: LINK_REQUEST
    reference_id = db.Column(db.Integer)  # Nullable if notification_type = INFO
    redirect_url = db.Column(db.String(255))

    @staticmethod
    def get_notifications_for_child(user_id, is_read):
        query = db.session.query(Notification).filter(Notification.user_id == user_id)
        if is_read:
            query = query.filter(Notification.is_read == is_read)
        return query.all()

    @staticmethod
    def get_notifications_for_parent(parent_id, is_read):
        query = db.session.query(Notification).filter(Notification.parent_id == parent_id)
        if is_read:
            query = query.filter(Notification.is_read == is_read)
        return query.all()

    def to_dict(self):
        notification_dict = super(Notification, self).to_dict()
        if notification_dict["reference_type"] == "LINK_REQUEST":
            link_request = db.session.get(LinkRequest, notification_dict["reference_id"])
            notification_dict["reference"] = link_request.to_dict()
        return notification_dict
