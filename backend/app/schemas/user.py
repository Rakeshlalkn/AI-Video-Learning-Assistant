"""Pydantic schemas — users and auth."""
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    profile_image: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class GoogleLoginRequest(BaseModel):
    """Body of POST /auth/google — accepts the id_token from Google Identity Services."""
    id_token: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
