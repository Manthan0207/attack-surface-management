from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Create a new platform user account (Admin only)."""
    return auth_service.register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and issue a Bearer access token."""
    return auth_service.login_user(db, payload)
