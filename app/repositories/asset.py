from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetType


def create_assets(
    db: Session,
    *,
    scan_id: str,
    domain_id: str,
    records: list[tuple[AssetType, str]],
) -> list[Asset]:
    assets = [
        Asset(scan_id=scan_id, domain_id=domain_id, type=asset_type, value=value)
        for asset_type, value in records
    ]
    db.add_all(assets)
    db.commit()
    for asset in assets:
        db.refresh(asset)
    return assets


def list_assets(
    db: Session,
    *,
    page: int,
    limit: int,
    domain_id: str | None = None,
    asset_type: AssetType | None = None,
) -> tuple[list[Asset], int]:
    stmt = select(Asset)
    count_stmt = select(func.count()).select_from(Asset)

    if domain_id is not None:
        stmt = stmt.where(Asset.domain_id == domain_id)
        count_stmt = count_stmt.where(Asset.domain_id == domain_id)
    if asset_type is not None:
        stmt = stmt.where(Asset.type == asset_type)
        count_stmt = count_stmt.where(Asset.type == asset_type)

    total = int(db.scalar(count_stmt) or 0)
    offset = (page - 1) * limit
    items = list(
        db.scalars(
            stmt.order_by(Asset.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return items, total
