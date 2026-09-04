from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.password_policy import validate_password_policy
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import user as user_repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


def register_user(db: Session, payload: RegisterRequest) -> UserResponse:
    validate_password_policy(payload.password)

    if user_repo.get_user_by_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = user_repo.create_user(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    return UserResponse.model_validate(user)


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    user = user_repo.get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "role": user.role.value},
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )
