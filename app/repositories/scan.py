from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.domain import Domain, DomainStatus
from app.models.scan import Scan, ScanStatus


def get_scan_by_id(db: Session, scan_id: str) -> Scan | None:
    return db.get(Scan, scan_id)


def domain_has_running_scan(db: Session, domain_id: str) -> bool:
    scan_id = db.scalar(
        select(Scan.id)
        .where(Scan.domain_id == domain_id, Scan.status == ScanStatus.RUNNING)
        .limit(1)
    )
    return scan_id is not None


def domain_has_active_scan(db: Session, domain_id: str) -> bool:
    """True if a scan is already queued (PENDING) or in progress (RUNNING)."""
    scan_id = db.scalar(
        select(Scan.id)
        .where(
            Scan.domain_id == domain_id,
            Scan.status.in_([ScanStatus.PENDING, ScanStatus.RUNNING]),
        )
        .limit(1)
    )
    return scan_id is not None


def create_scan(
    db: Session,
    *,
    domain_id: str,
    triggered_by: str | None,
    commit: bool = True,
) -> Scan:
    scan = Scan(
        domain_id=domain_id,
        status=ScanStatus.PENDING,
        triggered_by=triggered_by,
    )
    db.add(scan)
    if commit:
        db.commit()
        db.refresh(scan)
    else:
        db.flush()
    return scan


def mark_scan_running(db: Session, scan: Scan) -> Scan:
    scan.status = ScanStatus.RUNNING
    scan.started_at = datetime.now(UTC)
    scan.error_message = None
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def mark_scan_completed(db: Session, scan: Scan) -> Scan:
    scan.status = ScanStatus.COMPLETED
    scan.completed_at = datetime.now(UTC)
    scan.error_message = None
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def mark_scan_failed(db: Session, scan: Scan, error_message: str) -> Scan:
    scan.status = ScanStatus.FAILED
    scan.completed_at = datetime.now(UTC)
    scan.error_message = error_message
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def set_domain_status(db: Session, domain: Domain, status: DomainStatus) -> Domain:
    domain.status = status
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def list_scans_for_domain(
    db: Session,
    *,
    domain_id: str,
    page: int,
    limit: int,
) -> tuple[list[Scan], int]:
    count_stmt = select(func.count()).select_from(Scan).where(Scan.domain_id == domain_id)
    total = int(db.scalar(count_stmt) or 0)
    offset = (page - 1) * limit
    items = list(
        db.scalars(
            select(Scan)
            .where(Scan.domain_id == domain_id)
            .order_by(Scan.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return items, total


def list_recoverable_scan_ids(db: Session) -> list[str]:
    """PENDING scans, plus RUNNING scans left behind by a process restart."""
    rows = db.scalars(
        select(Scan.id).where(Scan.status.in_([ScanStatus.PENDING, ScanStatus.RUNNING]))
    ).all()
    return list(rows)


def reset_interrupted_scans(db: Session) -> list[str]:
    """Move leftover RUNNING scans back to PENDING so they can be re-queued."""
    scans = list(db.scalars(select(Scan).where(Scan.status == ScanStatus.RUNNING)).all())
    ids: list[str] = []
    for scan in scans:
        scan.status = ScanStatus.PENDING
        scan.started_at = None
        scan.error_message = "Interrupted by process restart; re-queued"
        db.add(scan)
        ids.append(scan.id)
    if ids:
        db.commit()
    return ids
