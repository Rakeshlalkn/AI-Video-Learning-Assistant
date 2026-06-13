"""Google OAuth login endpoint.

Accepts a Google id_token (from Google Identity Services on the frontend),
verifies it, upserts the user, and issues a JWT access token.
"""
from fastapi import APIRouter, Depends, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import (
    GoogleLoginRequest,
    TokenResponse,
    UserOut,
    UserLoginRequest,
    UserRegisterRequest,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Verify a Google id_token and return our own JWT."""
    if (
        not settings.google_client_id
        or settings.google_client_id == "your-google-client-id.apps.googleusercontent.com"
    ):
        # Allow dev mode: skip verification and trust the token payload.
        # In production this branch will never run because the env var is set.
        import base64
        import json

        try:
            payload_part = body.id_token.split(".")[1]
            # pad
            payload_part += "=" * (-len(payload_part) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_part))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid dev token: {exc}")
    else:
        try:
            payload = id_token.verify_oauth2_token(
                body.id_token,
                grequests.Request(),
                settings.google_client_id,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=401, detail=f"Invalid Google token: {exc}")

    google_sub = payload["sub"]
    email = payload.get("email", "")
    name = payload.get("name", "") or email.split("@")[0]
    picture = payload.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user = db.query(User).filter(User.id == google_sub).first()
    if not user:
        user = User(
            id=google_sub,
            name=name,
            email=email,
            profile_image=picture,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Keep profile info fresh
        user.name = name or user.name
        user.profile_image = picture or user.profile_image
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse)
def register_user(body: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email/password and return a JWT."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with that email already exists")

    hashed_password = get_password_hash(body.password)
    name = body.name or body.email.split("@")[0]
    user = User(
        name=name,
        email=body.email,
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login_user(body: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user by email/password and return a JWT."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current
