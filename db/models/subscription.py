from db.models.base_table import BaseTable
from db.extension import db


class Subscription(BaseTable):
    __tablename__ = "subscription"

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id', ondelete='CASCADE'))
    package_group_id = db.Column(db.Integer, db.ForeignKey('package_group.id', ondelete='CASCADE'))

    package_group = db.relationship("PackageGroup", back_populates="subscription", uselist=False)
    package = db.relationship("Package", back_populates="subscription", uselist=False)
