from operator import or_
from typing import Union

from db.models import PersonAIs, UserPersonAI, HistoryMessage
from db.extension import db
from utils.enum.role import AppRole


class UserPersonAIService:

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

    @staticmethod
    def get_by_chatter(id, role):
        if role == AppRole.USER:
            return UserPersonAI.get_by_user_id(id)
        else:
            return UserPersonAI.get_by_parent_id(id)

    @staticmethod
    def get_person_ai_by_user_id(category_id, education, search_query, sort_by, sort_order, id, role):
        user_person_ai_query = db.session.query(UserPersonAI) \
            .join(HistoryMessage, UserPersonAI.id == HistoryMessage.user_person_ai_id)
        if role == AppRole.USER:
            user_person_ai_query = user_person_ai_query.filter(UserPersonAI.user_id == id).distinct()
        else:
            user_person_ai_query = user_person_ai_query.filter(UserPersonAI.parent_id == id).distinct()
        user_person_ais = user_person_ai_query.all()
        user_person_ais = [user_person_ai for user_person_ai in user_person_ais]
        user_person_ai_ids = [user_person_ai.person_ai_id for user_person_ai in user_person_ais]
        # Apply filters, if provided
        filters = []
        if category_id:
            filters.append(PersonAIs.category_id == category_id)
        # Education filter
        if education:
            filters.append(PersonAIs.education == education)
        # Apply search query, if provided
        search_filters = []
        if search_query:
            search_filters.append(PersonAIs.name.ilike(f"%{search_query}%"))
        # Construct the base query
        base_query = db.session.query(PersonAIs).filter(PersonAIs.id.in_(user_person_ai_ids))
        if filters:
            base_query = base_query.filter(*filters)
        if search_filters:
            base_query = base_query.filter(*search_filters)
        # Apply sorting
        sort_column = getattr(PersonAIs, sort_by)
        if sort_order == 'asc':
            base_query = base_query.order_by(sort_column)
        else:
            base_query = base_query.order_by(sort_column.desc())
        # Apply pagination
        person_ais = base_query.all()
        person_ais = [person_ai.to_dict() for person_ai in person_ais]
        return person_ais
