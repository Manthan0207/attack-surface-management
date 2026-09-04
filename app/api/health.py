from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(response: Response) -> dict[str, str]:
    """Report API and database connectivity for uptime monitoring."""
    db: Session | None = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "unreachable"}
    finally:
        if db is not None:
            db.close()
