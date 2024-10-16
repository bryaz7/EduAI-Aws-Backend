from datetime import datetime, timedelta

from sqlalchemy.sql import func

from db.extension import db
from db.models.base_table import BaseTable
from utils.exceptions import ItemNotFoundError


class UserProgressTracking(BaseTable):
    __tablename__ = "user_progress_tracking"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    critical_thinking = db.Column(db.Float, default=0)
    emotional_awareness = db.Column(db.Float, default=0)
    creative_thinking = db.Column(db.Float, default=0)
    communication = db.Column(db.Float, default=0)
    problem_solving = db.Column(db.Float, default=0)

    @staticmethod
    def get_zeros(user_id):
        user_progress_tracking = {
            "user_id": user_id,
            "critical_thinking": 0,
            "emotional_awareness": 0,
            "creative_thinking": 0,
            "communication": 0,
            "problem_solving": 0
        }
        return UserProgressTracking.from_dict(user_progress_tracking)

    @staticmethod
    def get_latest_progress_tracking(user_id):
        return db.session.query(UserProgressTracking) \
            .filter_by(user_id=user_id) \
            .order_by(db.desc(UserProgressTracking.created_date)) \
            .limit(1).first()

    @staticmethod
    def get_line_chart_data(user_id, skill, days=7, freq='day', from_date=None, to_date=None):
        if to_date is None:
            to_date = datetime.now().date()
        else:
            to_date = datetime.strptime(to_date, "%Y-%m-%d").date()

        if from_date is None:
            from_date = to_date - timedelta(days=days)
        else:
            from_date = datetime.strptime(from_date, "%Y-%m-%d").date()

        if not getattr(UserProgressTracking, skill):
            raise ItemNotFoundError(f"Skill {skill} is not found")

        grouping_function = func.date_trunc(freq, UserProgressTracking.created_date)

        subquery = db.session.query(
            grouping_function.label("grouped_date"),
            func.avg(getattr(UserProgressTracking, skill)).label("value")
        ).filter(
            UserProgressTracking.created_date <= to_date,
            UserProgressTracking.created_date >= from_date,
            UserProgressTracking.user_id == user_id
        ).group_by(
            "grouped_date"
        ).order_by(
            db.asc("grouped_date")
        ).subquery()

        aggregated_records = db.session.query(
            subquery.c.grouped_date,
            subquery.c.value
        ).all()

        aggregated_records = [{"time": record[0], "value": round(record[1], 2)} for record in aggregated_records]
        return aggregated_records
