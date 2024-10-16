from db.models.base_table import BaseTable
from db.extension import db


class Package(BaseTable):
    __tablename__ = "package"

    id = db.Column(db.Integer, primary_key=True)

    # General information
    name = db.Column(db.String(255))
    description = db.Column(db.String(255))

    # Pricing
    monthly_pay_price = db.Column(db.Float)
    monthly_pay_promotion_price = db.Column(db.Float)
    yearly_pay_price = db.Column(db.Float)
    yearly_pay_promotion_price = db.Column(db.Float)

    # Privileges
    allowed_request = db.Column(db.Integer)
    character_limit = db.Column(db.Integer)
    image_generation_limit = db.Column(db.Integer)
    num_languages = db.Column(db.Integer)
    available_languages = db.Column(db.JSON)
    is_multiple_subject_plugin = db.Column(db.Boolean)
    num_clone_voices = db.Column(db.Integer)
    is_noice_canceling = db.Column(db.Boolean)
    is_iot_device = db.Column(db.Boolean)
    num_watchable_videos = db.Column(db.Integer)
    num_watchable_subjects = db.Column(db.Integer)
    num_learners = db.Column(db.Integer)
    can_parent_chat = db.Column(db.Boolean, default=False)

    # Stripe information
    stripe_monthly_pay_price_id = db.Column(db.String(255))
    stripe_yearly_pay_price_id = db.Column(db.String(255))

    subscription = db.relationship("Subscription", back_populates="package")

    @staticmethod
    def get_package_by_id(package_id):
        return db.session.get(Package, package_id)
