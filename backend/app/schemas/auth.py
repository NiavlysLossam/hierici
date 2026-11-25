import uuid
from pydantic import BaseModel
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenPayload(BaseModel):
    sub: str | None = None
    email: str | None = None
    role: str | None = None
    territory_id: str | None = None

