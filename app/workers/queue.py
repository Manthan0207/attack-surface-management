"""Enqueue scan jobs onto Celery (Redis broker)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def enqueue_scan(scan_id: str) -> None:
    """Publish a discovery job for ``scan_id`` to the Celery worker."""
    # Local import avoids circular import at module load (tasks → discovery → queue).
    from app.workers.tasks import run_discovery_scan

    run_discovery_scan.delay(scan_id)
    logger.info("Enqueued Celery discovery task for scan %s", scan_id)
