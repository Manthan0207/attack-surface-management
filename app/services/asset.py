from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import AssetType
from app.repositories import asset as asset_repo
from app.repositories import domain as domain_repo
from app.schemas.asset import AssetListResponse, AssetResponse


def list_assets(
    db: Session,
    *,
    page: int,
    limit: int,
    domain_id: str | None,
    asset_type: AssetType | None,
) -> AssetListResponse:
    if domain_id is not None and domain_repo.get_domain_by_id(db, domain_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    page = max(page, 1)
    limit = min(max(limit, 1), settings.max_page_size)
    items, total = asset_repo.list_assets(
        db,
        page=page,
        limit=limit,
        domain_id=domain_id,
        asset_type=asset_type,
    )

    responses: list[AssetResponse] = []
    for item in items:
        domain = domain_repo.get_domain_by_id(db, item.domain_id)
        responses.append(
            AssetResponse(
                id=item.id,
                domain=domain.name if domain else item.domain_id,
                type=item.type,
                value=item.value,
            )
        )

    return AssetListResponse(items=responses, page=page, limit=limit, total=total)
