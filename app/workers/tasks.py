"""Celery tasks for DNS discovery."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.workers.celery_app import celery
from app.workers.discovery import _process_scan

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name="app.workers.tasks.run_discovery_scan",
    max_retries=settings.scan_max_retries,
)
def run_discovery_scan(self, scan_id: str) -> None:
    """Process one scan job; Celery retries transient DNS failures."""
    logger.info(
        "Celery task run_discovery_scan scan_id=%s attempt=%s",
        scan_id,
        self.request.retries + 1,
    )
    _process_scan(scan_id, task=self)
