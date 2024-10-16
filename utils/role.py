def validate_role(role):
    if role not in ["user", "parent", "user_under_13", "user_over_13"]:
        raise ValueError("Role is invalid, it should be user or parent")
    if role in ["user_under_13", "user_over_13"]:
        role = "user"
    else:
        role = role
    return role
