from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_authenticated
from app.models.asset import AssetType
from app.models.user import User
from app.schemas.asset import AssetListResponse
from app.services import asset as asset_service

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetListResponse)
def list_assets(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=None, ge=1),
    domain_id: str | None = Query(default=None),
    type: AssetType | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_authenticated),
) -> AssetListResponse:
    """List discovered assets across domains."""
    effective_limit = settings.default_page_size if limit is None else limit
    return asset_service.list_assets(
        db,
        page=page,
        limit=effective_limit,
        domain_id=domain_id,
        asset_type=type,
    )
