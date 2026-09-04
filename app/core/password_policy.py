import re

from fastapi import HTTPException, status

_MIN_LENGTH = 8
_COMPLEXITY_MESSAGE = (
    "Password must include uppercase, lowercase, a number, and a special character"
)


def validate_password_policy(password: str) -> None:
    """Raise HTTP 400 if password does not meet the agreed policy.

    - Length < 8 → specific message
    - Missing upper/lower/digit/special → one general requirements message
    """
    if len(password) < _MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_special = re.search(r"[^A-Za-z0-9]", password) is not None

    if not (has_upper and has_lower and has_digit and has_special):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_COMPLEXITY_MESSAGE,
        )
