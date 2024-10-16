from datetime import datetime

from sqlalchemy.orm import declarative_base
from sqlalchemy_easy_softdelete.mixin import generate_soft_delete_mixin_class

from db.extension import db


class SoftDeleteMixin(generate_soft_delete_mixin_class()):
    deleted_at: datetime


Base = declarative_base()


class BaseTable(db.Model, Base, SoftDeleteMixin):
    __abstract__ = True
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        self.update_fields(**kwargs)

    def update_fields(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if hasattr(self.__class__, 'updated_date'):
            setattr(self, 'updated_date', datetime.utcnow())

    @classmethod
    def from_dict(cls, data):
        instance = cls()
        instance.update_fields(**data)
        return instance

    def to_dict(self, subset=None) -> dict:
        fields = self.__table__.columns.keys()
        if subset is None:
            return {field: getattr(self, field) for field in fields}
        else:
            return {field: getattr(self, field) for field in fields if field in subset}

    def soft_delete(self):
        # TODO: Perform cascade delete if required
        self.delete()
        # current_time = datetime.utcnow()
        #
        # if hasattr(self, 'deleted_at'):
        #     setattr(self, 'deleted_at', current_time)
        #
        # if hasattr(self, 'updated_date'):
        #     setattr(self, 'updated_date', current_time)
        #
        # for relation in self.__mapper__.relationships:
        #     if relation.uselist:
        #         for child in getattr(self, relation.key):
        #             if not getattr(child, 'deleted_at'):
        #                 child.soft_delete()
        #     else:
        #         child = getattr(self, relation.key)
        #         if child and not getattr(child, 'deleted_at'):
        #             child.soft_delete()
        #
        # # Commit the changes to the database
        # db.session.commit()
