from datetime import datetime

from pydantic import BaseModel

from app.models.scan import ScanStatus


class ScanTriggerResponse(BaseModel):
    scan_id: str
    status: ScanStatus


class ScanHistoryItem(BaseModel):
    scan_id: str
    status: ScanStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class ScanListResponse(BaseModel):
    items: list[ScanHistoryItem]
    page: int
    limit: int
    total: int
