from db.models import Package
from db.models.base_table import BaseTable
from db.extension import db
from utils.exceptions import ItemNotFoundError


class User(BaseTable):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    email = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    gender = db.Column(db.String(255))
    nationality = db.Column(db.String(255))
    subject_id = db.Column(db.String(255))
    address = db.Column(db.String(255))
    date_of_birth = db.Column(db.DateTime)
    avatar_url = db.Column(db.String(255))
    level = db.Column(db.Integer, default=1)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id', ondelete='SET NULL'))
    parent_email = db.Column(db.String(255))
    stripe_client_id = db.Column(db.String(255))
    display_language = db.Column(db.String(255), default="English")
    chat_languages = db.Column(db.JSON, default=["English"])
    is_trash = db.Column(db.Boolean, default=False)
    is_notification_on = db.Column(db.Boolean, default=True)
    firebase_registration_tokens = db.Column(db.JSON, default=[])
    package_group_id = db.Column(db.Integer, db.ForeignKey('package_group.id', ondelete='SET NULL'))

    user_person_ais = db.relationship("UserPersonAI", cascade="all, delete")
    package_group = db.relationship("PackageGroup", back_populates="users", uselist=False)
    parent = db.relationship("Parent", back_populates="users", uselist=False)
    link_requests = db.relationship("LinkRequest", back_populates="user")

    @staticmethod
    def get_user_level(user_id):
        parent = db.session.get(User, user_id)
        return parent.to_dict(subset=["id", "level"])

    @staticmethod
    def get_by_subject_id(subject_id):
        return db.session.query(User).filter(User.subject_id == subject_id).first()

    @staticmethod
    def get_by_parent_email(parent_email):
        return db.session.query(User).filter(User.parent_email == parent_email).all()

    def add_firebase_registration_token(self, token):
        self.firebase_registration_tokens = self.firebase_registration_tokens + [token]
        db.session.commit()

    def remove_registration_token(self, token):
        self.firebase_registration_tokens = [i for i in self.firebase_registration_tokens if i != token]
        db.session.commit()

    @staticmethod
    def get_active_package(user_id) -> Package:
        user = db.session.get(User, user_id)
        if not user:
            raise ItemNotFoundError("User not found")
        if user.package_group_id:
            package_group = user.package_group
            subscription = package_group.subscription
            package = subscription.package
            return package
        else:
            # Get free package
            free_package = db.session.query(Package).filter(Package.monthly_pay_price == 0).first()
            return free_package
