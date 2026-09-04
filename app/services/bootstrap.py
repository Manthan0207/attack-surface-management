from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole


def seed_admin_user(db: Session) -> None:
    """Create the bootstrap admin user if no ADMIN exists yet."""
    existing_admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).limit(1))
    if existing_admin is not None:
        return

    admin = User(
        email=settings.admin_email.lower().strip(),
        password_hash=hash_password(settings.admin_password),
        full_name=settings.admin_full_name.strip(),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
