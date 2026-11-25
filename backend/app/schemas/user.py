import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.user import UserRole

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserBase(BaseModel):
    email: str = Field(..., max_length=255)
    full_name: str
    role: UserRole = UserRole.CONTRIBUTOR
    territory_id: uuid.UUID | None = None
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean_v = v.strip().lower()
        if not EMAIL_REGEX.match(clean_v):
            raise ValueError("Adresse email invalide")
        return clean_v


class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.CONTRIBUTOR
    territory_id: uuid.UUID | None = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean_v = v.strip().lower()
        if not EMAIL_REGEX.match(clean_v):
            raise ValueError("Adresse email invalide")
        return clean_v

    @field_validator("password")
    @classmethod
    def validate_password_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le mot de passe ne peut pas être composé uniquement d'espaces blancs.")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Le mot de passe ne peut pas être composé uniquement d'espaces blancs.")
        return v


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
