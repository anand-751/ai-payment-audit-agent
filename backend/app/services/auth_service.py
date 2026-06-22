from app.repositories.user_repository import get_user


def authenticate_user(username, password, role):
    user = get_user(username)

    if not user:
        return None

    if user["password_hash"] != password:
        return None

    if user["role"].lower() != role.lower():
        return None

    return user