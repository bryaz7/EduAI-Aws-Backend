from typing import Union

from db.models.base_table import BaseTable
from db.extension import db
from utils.enum.role import AppRole


class UserPersonAI(BaseTable):
    __tablename__ = "user_person_ai"

    id = db.Column(db.Integer, primary_key=True)
    person_ai_id = db.Column(db.Integer, db.ForeignKey('person_ai.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id', ondelete='CASCADE'))

    history_messages = db.relationship("HistoryMessage", cascade="all, delete")

    @staticmethod
    def get_user_person_ai_by_user(user_id, person_ai_id) -> Union[int, None]:
        user_person_ai = db.session.query(UserPersonAI).filter_by(person_ai_id=person_ai_id, user_id=user_id).first()
        if user_person_ai:
            return user_person_ai.id
        else:
            return None

    @staticmethod
    def get_user_person_ai_by_parent(parent_id, person_ai_id) -> Union[int, None]:
        user_person_ai = db.session.query(UserPersonAI).filter_by(person_ai_id=person_ai_id,
                                                                  parent_id=parent_id).first()
        if user_person_ai:
            return user_person_ai.id
        else:
            return None

    @staticmethod
    def get_user_person_ai_by_chatter(id, person_ai_id, role) -> Union[int, None]:
        if role == AppRole.USER:
            return UserPersonAI.get_user_person_ai_by_user(id, person_ai_id)
        else:
            return UserPersonAI.get_user_person_ai_by_parent(id, person_ai_id)

    @staticmethod
    def get_by_user_id(user_id):
        return db.session.query(UserPersonAI).filter(UserPersonAI.user_id == user_id).all()

    @staticmethod
    def get_by_parent_id(parent_id):
        return db.session.query(UserPersonAI).filter(UserPersonAI.parent_id == parent_id).all()
