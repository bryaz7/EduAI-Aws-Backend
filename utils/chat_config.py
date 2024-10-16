from typing import Union
from db.extension import db
from db.models import User, PersonAIs, Parent, PackageGroup, Package
from utils.enum.role import AppRole
from utils.exceptions import ItemNotFoundError
from utils.time import calculate_age


class ChatConfig:

    def __init__(self, chatter: Union[User, Parent], person_ai: PersonAIs,
                 package_group: PackageGroup, package: Package,
                 role: str, message_id: int, uuid_request: str):
        self.chatter = chatter
        self.person_ai = person_ai
        self.package_group = package_group
        self.package = package
        self.user_age = calculate_age(chatter.date_of_birth)
        self.user_or_display_name = chatter.display_name or chatter.username
        self.role = role
        self.message_id = message_id
        self.uuid_request = uuid_request
        self.request_type = None
        self.request_count = None

    def set_request_type_and_count(self, request_type, request_count):
        self.request_type = request_type
        self.request_count = request_count


def generate_config_object(id, message_id, person_ai_id, role, uuid_request):
    if role == AppRole.USER:
        chatter = db.session.get(User, id)
    else:
        chatter = db.session.get(Parent, id)

    if not chatter:
        raise ItemNotFoundError("User or Parent not found")
    package_group = chatter.package_group

    if role == AppRole.USER:
        package = User.get_active_package(id)
    else:
        package = Parent.get_active_package(id)
    if not package:
        raise ItemNotFoundError("Package not found")

    person_ai = db.session.get(PersonAIs, person_ai_id)
    configs = ChatConfig(chatter, person_ai, package_group, package, role, message_id, uuid_request)
    return configs
