"""Background discovery worker: thread pool consuming the in-memory scan queue."""

from __future__ import annotations

import logging
import threading

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.domain import DomainStatus
from app.models.scan import Scan, ScanStatus
from app.repositories import asset as asset_repo
from app.repositories import domain as domain_repo
from app.repositories import scan as scan_repo
from app.workers.dns import resolve_domain_records
from app.workers.queue import dequeue_scan, enqueue_scan, mark_task_done

logger = logging.getLogger(__name__)

_workers: list[threading.Thread] = []
_stop_event = threading.Event()


def _enqueue_next_pending_for_domain(db, domain_id: str) -> None:
    next_id = db.scalar(
        select(Scan.id)
        .where(Scan.domain_id == domain_id, Scan.status == ScanStatus.PENDING)
        .order_by(Scan.created_at.asc())
        .limit(1)
    )
    if next_id:
        enqueue_scan(next_id)


def _process_scan(scan_id: str) -> None:
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
        except Exception as exc:  # noqa: BLE001 — ensure scan never stuck RUNNING
            logger.exception("Scan %s FAILED", scan.id)
            scan_repo.mark_scan_failed(db, scan, str(exc) or exc.__class__.__name__)
            domain = domain_repo.get_domain_by_id(db, scan.domain_id)
            if domain is not None:
                scan_repo.set_domain_status(db, domain, DomainStatus.FAILED)
        finally:
            _enqueue_next_pending_for_domain(db, scan.domain_id)
    finally:
        db.close()


def _worker_loop(worker_name: str) -> None:
    logger.info("%s started", worker_name)
    while not _stop_event.is_set():
        scan_id = dequeue_scan(timeout=1.0)
        if scan_id is None:
            continue
        try:
            _process_scan(scan_id)
        except Exception:  # noqa: BLE001
            logger.exception("%s crashed while processing %s", worker_name, scan_id)
        finally:
            mark_task_done()
    logger.info("%s stopped", worker_name)


def start_workers() -> None:
    """Start daemon worker threads (idempotent)."""
    if _workers:
        return
    _stop_event.clear()
    count = max(1, settings.discovery_worker_threads)
    for index in range(count):
        name = f"discovery-worker-{index + 1}"
        thread = threading.Thread(
            target=_worker_loop,
            name=name,
            args=(name,),
            daemon=True,
        )
        thread.start()
        _workers.append(thread)
    logger.info("Started %s discovery worker thread(s)", count)


def stop_workers() -> None:
    """Signal workers to stop (used on app shutdown)."""
    _stop_event.set()
    for thread in list(_workers):
        thread.join(timeout=2.0)
    _workers.clear()


def recover_pending_jobs() -> None:
    """Rebuild the in-memory queue from DB after process start."""
    db = SessionLocal()
    try:
        scan_repo.reset_interrupted_scans(db)
        pending_ids = scan_repo.list_recoverable_scan_ids(db)
        for scan_id in pending_ids:
            enqueue_scan(scan_id)
        logger.info("Recovered %s scan job(s) into in-memory queue", len(pending_ids))
    finally:
        db.close()
