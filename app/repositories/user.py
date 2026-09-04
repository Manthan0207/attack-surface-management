from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower().strip()))


def create_user(
    db: Session,
    *,
    email: str,
    password_hash: str,
    full_name: str,
    role: UserRole,
) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=password_hash,
        full_name=full_name.strip(),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
