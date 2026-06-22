from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "payment-audit-secret"
ALGORITHM = "HS256"


def create_token(user):

    payload = {
        "sub": user["username"],
        "role": user["role"],
        "name": user["full_name"],
        "exp": datetime.utcnow() + timedelta(hours=8)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )