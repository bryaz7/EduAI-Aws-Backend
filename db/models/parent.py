from db.models import Package
from db.models.base_table import BaseTable
from db.extension import db
from utils.exceptions import ItemNotFoundError


class Parent(BaseTable):
    __tablename__ = "parent"

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
    stripe_client_id = db.Column(db.String(255))
    display_language = db.Column(db.String(255), default="English")
    chat_languages = db.Column(db.JSON, default=["English"])
    is_notification_on = db.Column(db.Boolean, default=True)
    firebase_registration_tokens = db.Column(db.JSON, default=[])
    package_group_id = db.Column(db.Integer, db.ForeignKey('package_group.id', ondelete='SET NULL'))

    package_group = db.relationship("PackageGroup", back_populates="parents", uselist=False)
    users = db.relationship("User", back_populates="parent")
    link_requests = db.relationship("LinkRequest", back_populates="parent")

    @staticmethod
    def get_parent_level(parent_id):
        parent = db.session.get(Parent, parent_id)
        return parent.to_dict(subset=["id", "level"])

    @staticmethod
    def get_by_subject_id(subject_id):
        return db.session.query(Parent).filter(Parent.subject_id == subject_id).first()

    def add_firebase_registration_token(self, token):
        self.firebase_registration_tokens = self.firebase_registration_tokens + [token]
        db.session.commit()

    def remove_registration_token(self, token):
        self.firebase_registration_tokens = [i for i in self.firebase_registration_tokens if i != token]
        db.session.commit()

    @staticmethod
    def get_active_package(parent_id) -> Package:
        parent = db.session.get(Parent, parent_id)
        if not parent:
            raise ItemNotFoundError("Parent not found")
        if parent.package_group_id:
            package_group = parent.package_group
            subscription = package_group.subscription
            package = subscription.package
            return package
        else:
            # Get free package
            free_package = db.session.query(Package).filter(Package.monthly_pay_price == 0).first()
            return free_package

    @staticmethod
    def get_current_num_link_with_quota(parent_id):
        parent = db.session.get(Parent, parent_id)
        if not parent:
            raise ItemNotFoundError("Parent not found")

        # Get current package from parent
        current_package = Parent.get_active_package(parent_id)

        return {
            "current_num_links": len(parent.users),
            "max_num_links": current_package.num_learners
        }
