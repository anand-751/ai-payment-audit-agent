from fastapi import APIRouter, HTTPException

from app.services.auth_service import authenticate_user
from app.utils.jwt_utils import create_token
from app.models.auth_models import LoginRequest

router = APIRouter()


@router.post("/auth/login")
def login(request: LoginRequest):

    user = authenticate_user(
        request.username,
        request.password,
        request.role
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "name": user["full_name"],
            "role": user["role"]
        }
    }