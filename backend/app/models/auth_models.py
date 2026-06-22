from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict