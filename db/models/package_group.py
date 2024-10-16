from db.extension import db
from db.models.base_table import BaseTable
from utils.exceptions import ItemNotFoundError


class PackageGroup(BaseTable):
    __tablename__ = "package_group"

    id = db.Column(db.Integer, primary_key=True)
    buyer_type = db.Column(db.String(32))
    buyer_id = db.Column(db.Integer)
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    stripe_subscription_id = db.Column(db.String(255))
    status = db.Column(db.String(32))
    latest_invoice = db.Column(db.String(255))
    reference_number = db.Column(db.String(255))
    payment_method = db.Column(db.String(255))
    total_payment = db.Column(db.Float)
    currency = db.Column(db.String(32))
    cancel_at_period_end = db.Column(db.Boolean)

    # Backref to users and parents
    users = db.relationship("User", back_populates="package_group")
    parents = db.relationship("Parent", back_populates="package_group")
    subscription = db.relationship("Subscription", back_populates="package_group", uselist=False)

    @staticmethod
    def get_package_group_details(package_group_id):
        package_group = db.session.get(PackageGroup, package_group_id)
        if not package_group:
            raise ItemNotFoundError("Package group not found")

        users = package_group.users
        parents = package_group.parents
        subscription = package_group.subscription
        if not subscription:
            raise ItemNotFoundError("Subscription not found")
        package = subscription.package
        if not package:
            raise ItemNotFoundError("Package not found")

        package_group_details = package_group.to_dict()
        package_group_details["users"] = [user.to_dict(subset=["id", "username", "display_name", "email", "avatar_url"]) for user in users]
        package_group_details["parents"] = [parent.to_dict(subset=["id", "username", "display_name", "email", "avatar_url"]) for parent in parents]
        package_group_details["package"] = package.to_dict(subset=["id", "num_learners"])
        return package_group_details
