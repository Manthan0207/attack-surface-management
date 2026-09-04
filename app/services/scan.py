from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.domain import DomainStatus
from app.models.user import User
from app.repositories import domain as domain_repo
from app.repositories import scan as scan_repo
from app.schemas.scan import ScanHistoryItem, ScanListResponse, ScanTriggerResponse
from app.workers.queue import enqueue_scan


def trigger_manual_scan(db: Session, domain_id: str, current_user: User) -> ScanTriggerResponse:
    """Trigger a scan under a domain row lock so concurrent POSTs cannot both succeed."""
    domain = domain_repo.get_domain_by_id_for_update(db, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    # Treat PENDING as in-flight too. A RUNNING-only check still allows two parallel
    # POSTs to both create PENDING jobs before either worker marks RUNNING.
    if scan_repo.domain_has_active_scan(db, domain_id):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A scan is already running for this domain",
        )

    scan = scan_repo.create_scan(
        db,
        domain_id=domain_id,
        triggered_by=current_user.id,
        commit=False,
    )
    if domain.status != DomainStatus.RUNNING:
        domain.status = DomainStatus.PENDING
        db.add(domain)

    db.commit()
    db.refresh(scan)
    enqueue_scan(scan.id)
    return ScanTriggerResponse(scan_id=scan.id, status=scan.status)


def enqueue_initial_scan(db: Session, *, domain_id: str, triggered_by: str | None) -> None:
    """Used when a domain is created — always starts a background discovery scan."""
    scan = scan_repo.create_scan(db, domain_id=domain_id, triggered_by=triggered_by)
    domain = domain_repo.get_domain_by_id(db, domain_id)
    if domain is not None and domain.status != DomainStatus.RUNNING:
        scan_repo.set_domain_status(db, domain, DomainStatus.PENDING)
    enqueue_scan(scan.id)


def list_scans(
    db: Session,
    domain_id: str,
    *,
    page: int,
    limit: int,
) -> ScanListResponse:
    domain = domain_repo.get_domain_by_id(db, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    page = max(page, 1)
    limit = min(max(limit, 1), settings.max_page_size)
    items, total = scan_repo.list_scans_for_domain(
        db, domain_id=domain_id, page=page, limit=limit
    )
    return ScanListResponse(
        items=[
            ScanHistoryItem(
                scan_id=item.id,
                status=item.status,
                started_at=item.started_at,
                completed_at=item.completed_at,
                error_message=item.error_message,
            )
            for item in items
        ],
        page=page,
        limit=limit,
        total=total,
    )
