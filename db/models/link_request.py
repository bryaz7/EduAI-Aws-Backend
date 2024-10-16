from db.extension import db
from db.models.base_table import BaseTable
from db.models import User, Parent, Package
from utils.exceptions import ItemNotFoundError, ValidationError


class LinkRequest(BaseTable):
    __tablename__ = "link_request"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='cascade'))
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id', ondelete='cascade'))
    status = db.Column(db.String(255), default="PENDING")  # Statuses: PENDING, CONFIRM, DECLINED, CANCELLED
    is_sent_by_parent = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="link_requests", uselist=False)
    parent = db.relationship("Parent", back_populates="link_requests", uselist=False)

    @staticmethod
    def get_all_pending_requests(user_id=None, parent_id=None):
        query = db.session.query(LinkRequest).filter(LinkRequest.status == "PENDING")
        if user_id is not None:
            query = query.filter(LinkRequest.user_id == user_id)
        if parent_id is not None:
            query = query.filter(LinkRequest.parent_id == parent_id)
        return query.all()

    def to_dict(self):
        link_request_dict = super(LinkRequest, self).to_dict()

        user_data = db.session.get(User, link_request_dict["user_id"])
        if not user_data:
            raise ItemNotFoundError("User {} not exists in link request ID {}".format(link_request_dict["user_id"], link_request_dict["id"]))
        link_request_dict["user_data"] = user_data.to_dict()
        return link_request_dict

    @staticmethod
    def create_link_request(user_id, parent_id, is_sent_by_parent, ignore_linked_users=False):
        """
        Create a link request.

        Args:
            user_id (int): User ID
            parent_id (int): Parent ID
            is_sent_by_parent (bool): True if the request is sent by parent, false if the request is sent by the child
            ignore_linked_users (bool): If True, error won't be raised when a user already
                have relationship with another parent.

        Returns:
            link_request: The Link Request object
            sender: The sender object (return Parent object if is_sent_by_parent is True, User otherwise)
            receiver: The receiver object (return User object if is_sent_by_parent is False, Parent otherwise)
        """
        user = db.session.get(User, user_id)
        if not user:
            raise ItemNotFoundError("User not found")

        # Check if user has already had a parent
        if user.parent_id:
            if not ignore_linked_users:
                raise ValidationError(f"User {user.username or user.display_name} ({user_id}) already had an "
                                      f"associated parent, cannot create link request")
            else:
                return None, None, None

        parent = db.session.get(Parent, parent_id)
        if not parent:
            raise ItemNotFoundError("Parent not found")

        # Check if there is any pending link request between user and parent
        existing_pending_link_requests = LinkRequest.get_all_pending_requests(user_id, parent_id)
        if len(existing_pending_link_requests) > 0:
            raise ValidationError(f"There has been already a link request between parent and user {user.id}")

        link_request = LinkRequest.from_dict({
            "user_id": user_id,
            "parent_id": parent_id,
            "is_sent_by_parent": is_sent_by_parent,
            "status": "PENDING"
        })
        db.session.add(link_request)
        db.session.commit()
        if is_sent_by_parent:
            sender = db.session.get(Parent, parent_id)
            receiver = db.session.get(User, user_id)
        else:
            sender = db.session.get(User, user_id)
            receiver = db.session.get(Parent, parent_id)
        return link_request, sender, receiver

    @staticmethod
    def create_multiple_link_requests(user_ids, parent_id, is_sent_by_parent, ignore_linked_users=False):
        """
        Send multiple link requests.

        Args:
            user_ids (List[int]): User ID
            parent_id (int): Parent ID
            is_sent_by_parent (bool): True if the request is sent by parent, false if the request is sent by the child
            ignore_linked_users (bool): If True, error won't be raised when a user already
                have relationship with another parent.

        Returns: List of 3-item tuples, where each tuple consists of:
            link_request: The Link Request object
            sender: The sender object (return Parent object if is_sent_by_parent is True, User otherwise)
            receiver: The receiver object (return User object if is_sent_by_parent is False, Parent otherwise)
        """
        return [LinkRequest.create_link_request(user_id, parent_id, is_sent_by_parent, ignore_linked_users) for user_id in user_ids]

    @staticmethod
    def accept_link_request(link_request_id, acceptor):
        """
        Accept a link request

        Args:
            link_request_id (int): Link Request ID
            acceptor (str): Either `user` or `parent`

        Returns:
            link_request (LinkRequest): Link Request object
            acceptor_object (User or Parent): Acceptor object
        """
        link_request = db.session.get(LinkRequest, link_request_id)
        if not link_request:
            return ItemNotFoundError("Link request not found")

        # Won't provide update if the link request status is not PENDING
        if link_request.status != "PENDING":
            raise ValidationError(f"Link request is {link_request.status}, expect PENDING to perform action")

        # Won't provide update if the link request is from child
        avail_acceptor = "user" if link_request.is_sent_by_parent else "parent"
        if avail_acceptor != acceptor:
            raise ValidationError(f"Link request is sent by {acceptor}, {acceptor} cannot confirm or decline this "
                                  f"request")

        # Check if the child already had a parent
        user_id = link_request.user_id
        user = db.session.get(User, user_id)
        if not user:
            raise ItemNotFoundError("User in link request not found")

        parent_id = link_request.parent_id
        parent = db.session.get(Parent, parent_id)
        if not parent:
            raise ItemNotFoundError("Parent not found")

        existing_parent_id = user.parent_id
        link_parent_id = link_request.parent_id
        if existing_parent_id:
            if link_parent_id == existing_parent_id:
                raise ValidationError("Already link to the parent")
            else:
                raise ValidationError("Learner has already linked to another parent")

        link_request.status = "CONFIRMED"
        user.parent_id = link_parent_id
        user.is_trash = False

        # Linking to subscription
        user_package: Package = User.get_active_package(user_id)
        parent_package: Package = Parent.get_active_package(parent_id)
        if user_package.monthly_pay_price != 0 and parent_package.monthly_pay_price != 0:
            # Merging to the most-valued subscription
            is_parent_package_better = parent_package.monthly_pay_price >= user_package.monthly_pay_price
            better_package_group_id = parent.package_group_id if is_parent_package_better else user.package_group_id
            user.package_group_id = better_package_group_id
            parent.package_group_id = better_package_group_id
        else:
            package_group_id = user.package_group_id or parent.package_group_id
            user.package_group_id = package_group_id
            parent.package_group_id = package_group_id

        # Reject all other requests
        active_link_requests = LinkRequest.get_all_pending_requests(user_id)
        for active_link_request in active_link_requests:
            active_link_request.status = "CANCELLED"
        db.session.commit()

        acceptor_object = user if acceptor == "user" else parent
        return link_request, acceptor_object

    @staticmethod
    def decline_link_request(link_request_id, decliner):
        """
        Decline a link request

        Args:
            link_request_id (int): Link Request ID
            decliner (str): Either `user` or `parent`

        Returns:
            link_request (LinkRequest): Link Request object
            decliner_object (User or Parent): Decliner object
        """

        link_request = db.session.get(LinkRequest, link_request_id)
        if not link_request:
            raise ItemNotFoundError("Link request not found")

        # Won't provide update if the link request status is not PENDING
        if link_request.status != "PENDING":
            raise ValidationError(f"Link request is at status {link_request.status}, expect PENDING to perform action")

        # Won't provide update if the link request is from child
        avail_decliner = "user" if link_request.is_sent_by_parent else "parent"
        if avail_decliner != decliner:
            raise ValidationError(f"Link request is sent by {decliner}, {decliner} cannot confirm or decline this "
                                  f"request")

        link_request.status = "DECLINED"
        db.session.commit()

        decliner_object = db.session.get(Parent, link_request.parent_id) if decliner == "parent" else \
            db.session.get(User, link_request.user_id)
        return link_request, decliner_object

    @staticmethod
    def cancel_link_request(link_request_id, canceler):
        """
        Cancel a link request. The cancellation will attach with a Firebase implicit notification.

        Args:
            link_request_id (int): Link Request ID
            canceler (str): Either `parent` or `user`

        Returns:
            link_request (LinkRequest): Link Request object
            receiver (User or Parent): The person who receives the notification on cancellation
        """
        link_request = db.session.get(LinkRequest, link_request_id)
        if not link_request:
            raise ItemNotFoundError(f"Link request {link_request_id} not found")

        # Won't provide update if the link request status is not PENDING
        if link_request.status != "PENDING":
            raise ValidationError(f"Link request {link_request_id} is at status {link_request.status}, expect PENDING "
                                  f"to perform cancellation")

        avail_canceler = "parent" if link_request.is_sent_by_parent else "user"
        if avail_canceler != canceler:
            raise ValidationError(f"Link request is sent by {avail_canceler}, {canceler} cannot cancel this "
                                  f"request")

        link_request.status = "CANCELLED"
        db.session.commit()

        user = db.session.get(User, link_request.user_id)
        parent = db.session.get(Parent, link_request.parent_id)

        if link_request.is_sent_by_parent:
            receiver = user
        else:
            receiver = parent

        return link_request, receiver
