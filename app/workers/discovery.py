"""DNS discovery processing (runs inside Celery workers or inline in tests)."""

from __future__ import annotations

import logging
from typing import Any

import dns.exception
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.domain import DomainStatus
from app.models.scan import Scan, ScanStatus
from app.repositories import asset as asset_repo
from app.repositories import domain as domain_repo
from app.repositories import scan as scan_repo
from app.workers.dns import resolve_domain_records
from app.workers.queue import enqueue_scan

logger = logging.getLogger(__name__)

_RETRYABLE = (dns.exception.Timeout, dns.exception.DNSException)


def _enqueue_next_pending_for_domain(db, domain_id: str) -> None:
    next_id = db.scalar(
        select(Scan.id)
        .where(Scan.domain_id == domain_id, Scan.status == ScanStatus.PENDING)
        .order_by(Scan.created_at.asc())
        .limit(1)
    )
    if next_id:
        enqueue_scan(next_id)


def _fail_scan(db, scan: Scan, message: str) -> None:
    scan_repo.mark_scan_failed(db, scan, message)
    domain = domain_repo.get_domain_by_id(db, scan.domain_id)
    if domain is not None:
        scan_repo.set_domain_status(db, domain, DomainStatus.FAILED)
    _enqueue_next_pending_for_domain(db, scan.domain_id)


def _process_scan(scan_id: str, task: Any | None = None) -> None:
    """Run discovery for one scan.

    When ``task`` is a bound Celery task, transient DNS errors trigger retries
    up to ``settings.scan_max_retries``. Without a task (pytest sync path),
    failures are terminal immediately.
    """
    db = SessionLocal()
    try:
        scan = scan_repo.get_scan_by_id(db, scan_id)
        if scan is None:
            logger.warning("Scan %s not found; dropping job", scan_id)
            return

        if scan.status not in (ScanStatus.PENDING, ScanStatus.RUNNING):
            logger.info("Scan %s already finished (%s); skipping", scan_id, scan.status)
            return

        domain = domain_repo.get_domain_by_id(db, scan.domain_id)
        if domain is None:
            scan_repo.mark_scan_failed(db, scan, "Domain no longer exists")
            return

        # Only one RUNNING scan per domain. Leave this job PENDING for later.
        if scan_repo.domain_has_running_scan(db, domain.id) and scan.status != ScanStatus.RUNNING:
            logger.info(
                "Domain %s already RUNNING; leaving scan %s PENDING",
                domain.id,
                scan_id,
            )
            return

        scan = scan_repo.mark_scan_running(db, scan)
        scan_repo.set_domain_status(db, domain, DomainStatus.RUNNING)
        logger.info("Scan %s RUNNING for domain %s", scan.id, domain.name)

        try:
            records = resolve_domain_records(domain.name)
            asset_repo.create_assets(
                db,
                scan_id=scan.id,
                domain_id=domain.id,
                records=records,
            )
            scan_repo.mark_scan_completed(db, scan)
            domain = domain_repo.get_domain_by_id(db, scan.domain_id)
            if domain is not None:
                scan_repo.set_domain_status(db, domain, DomainStatus.COMPLETED)
            logger.info(
                "Scan %s COMPLETED for %s (%s assets)",
                scan.id,
                domain.name if domain else scan.domain_id,
                len(records),
            )
            _enqueue_next_pending_for_domain(db, scan.domain_id)
        except _RETRYABLE as exc:
            message = str(exc) or exc.__class__.__name__
            logger.warning("Scan %s hit retryable DNS error: %s", scan.id, message)
            if task is not None and task.request.retries < settings.scan_max_retries:
                # Schedule another attempt; keep scan RUNNING until success or final fail.
                raise task.retry(
                    exc=exc,
                    countdown=settings.scan_retry_backoff_seconds,
                    max_retries=settings.scan_max_retries,
                )
            logger.exception("Scan %s FAILED after retries", scan.id)
            _fail_scan(db, scan, message)
        except Exception as exc:  # noqa: BLE001 — ensure scan never stuck RUNNING
            logger.exception("Scan %s FAILED", scan.id)
            _fail_scan(db, scan, str(exc) or exc.__class__.__name__)
    finally:
        db.close()


def recover_pending_jobs() -> None:
    """Re-queue PENDING / interrupted RUNNING scans into Celery after API start."""
    db = SessionLocal()
    try:
        scan_repo.reset_interrupted_scans(db)
        pending_ids = scan_repo.list_recoverable_scan_ids(db)
        for scan_id in pending_ids:
            enqueue_scan(scan_id)
        logger.info("Recovered %s scan job(s) into Celery", len(pending_ids))
    finally:
        db.close()
