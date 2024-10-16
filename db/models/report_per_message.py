from db.models.base_table import BaseTable
from db.extension import db


class ReportPerMessage(BaseTable):
    __tablename__ = "report_per_message"
    
    id = db.Column(db.Integer, primary_key=True)
    history_message_id = db.Column(db.Integer, db.ForeignKey('history_message.id', ondelete='CASCADE'))
    detail = db.Column(db.String(1024))
    timestamp = db.Column(db.String(1024))
    
    # history_message = db.relationship('HistoryMessage', backref=db.backref('history_message_report_history_message', cascade='all, delete'))
