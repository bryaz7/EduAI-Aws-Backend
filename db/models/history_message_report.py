from db.models.base_table import BaseTable
from db.extension import db


class HistoryMessageReport(BaseTable):
    __tablename__ = "history_message_report"
    
    id = db.Column(db.Integer, primary_key=True)
    history_message_id = db.Column(db.Integer, db.ForeignKey('history_message.id', ondelete='CASCADE'))
    detail = db.Column(db.String(1024))
