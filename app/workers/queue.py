"""In-memory scan job queue.

Scan/asset status lives in Postgres. This queue only holds scan IDs waiting
for a worker thread — it is process-local and rebuilt from DB on startup.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Set

logger = logging.getLogger(__name__)

_job_queue: queue.Queue[str] = queue.Queue()
_queued_ids: Set[str] = set()
_queued_lock = threading.Lock()


def enqueue_scan(scan_id: str) -> None:
    """Enqueue a scan id if it is not already waiting in the in-memory queue."""
    with _queued_lock:
        if scan_id in _queued_ids:
            logger.debug("Scan %s already queued; skipping duplicate enqueue", scan_id)
            return
        _queued_ids.add(scan_id)
        _job_queue.put(scan_id)
        logger.info("Enqueued scan job %s", scan_id)


def dequeue_scan(timeout: float = 1.0) -> str | None:
    try:
        scan_id = _job_queue.get(timeout=timeout)
    except queue.Empty:
        return None
    with _queued_lock:
        _queued_ids.discard(scan_id)
    return scan_id


def mark_task_done() -> None:
    _job_queue.task_done()
