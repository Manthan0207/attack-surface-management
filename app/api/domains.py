from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin, require_analyst_or_admin, require_authenticated
from app.models.domain import DomainStatus
from app.models.user import User
from app.schemas.domain import DomainCreateRequest, DomainListResponse, DomainResponse
from app.schemas.scan import ScanListResponse, ScanTriggerResponse
from app.services import domain as domain_service
from app.services import scan as scan_service

router = APIRouter(prefix="/domains", tags=["domains"])


@router.post(
    "",
    response_model=DomainResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_domain(
    payload: DomainCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst_or_admin),
) -> DomainResponse:
    """Register a domain and automatically start a discovery scan."""
    return domain_service.create_domain(db, payload, current_user)


@router.get("", response_model=DomainListResponse)
def list_domains(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=None, ge=1),
    status: DomainStatus | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_authenticated),
) -> DomainListResponse:
    """List domains with pagination, status filter, and partial name search."""
    effective_limit = settings.default_page_size if limit is None else limit
    return domain_service.list_domains(
        db,
        page=page,
        limit=effective_limit,
        status_filter=status,
        search=search,
    )


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_authenticated),
) -> DomainResponse:
    """Retrieve a single domain by id."""
    return domain_service.get_domain(db, domain_id)


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Response:
    """Permanently delete a domain and cascaded scans/assets (Admin only)."""
    domain_service.delete_domain(db, domain_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{domain_id}/scan",
    response_model=ScanTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_scan(
    domain_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst_or_admin),
) -> ScanTriggerResponse:
    """Manually trigger a discovery scan for a domain."""
    return scan_service.trigger_manual_scan(db, domain_id, current_user)


@router.get("/{domain_id}/scans", response_model=ScanListResponse)
def list_domain_scans(
    domain_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _user: User = Depends(require_authenticated),
) -> ScanListResponse:
    """Return scan history for a domain."""
    effective_limit = settings.default_page_size if limit is None else limit
    return scan_service.list_scans(db, domain_id, page=page, limit=effective_limit)
