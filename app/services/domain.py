from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.fqdn import normalize_and_validate_fqdn
from app.models.domain import DomainStatus
from app.models.user import User
from app.repositories import domain as domain_repo
from app.schemas.domain import (
    DomainCreateRequest,
    DomainListResponse,
    DomainResponse,
)
from app.services import scan as scan_service


def create_domain(db: Session, payload: DomainCreateRequest, current_user: User) -> DomainResponse:
    """Register a domain and automatically enqueue a discovery scan."""
    name = normalize_and_validate_fqdn(payload.domain)

    if domain_repo.get_domain_by_name(db, name) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Domain already exists",
        )

    domain = domain_repo.create_domain(
        db,
        name=name,
        created_by=current_user.id,
        status=DomainStatus.PENDING,
    )
    scan_service.enqueue_initial_scan(
        db,
        domain_id=domain.id,
        triggered_by=current_user.id,
    )
    #read in case status changed 
    domain = domain_repo.get_domain_by_id(db, domain.id) or domain
    return DomainResponse.model_validate(domain)


def get_domain(db: Session, domain_id: str) -> DomainResponse:
    domain = domain_repo.get_domain_by_id(db, domain_id)
    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    return DomainResponse.model_validate(domain)


def list_domains(
    db: Session,
    *,
    page: int,
    limit: int,
    status_filter: DomainStatus | None,
    search: str | None,
) -> DomainListResponse:
    page = max(page, 1)
    limit = min(max(limit, 1), settings.max_page_size)

    items, total = domain_repo.list_domains(
        db,
        page=page,
        limit=limit,
        status=status_filter,
        search=search,
    )
    return DomainListResponse(
        items=[DomainResponse.model_validate(item) for item in items],
        page=page,
        limit=limit,
        total=total,
    )


def delete_domain(db: Session, domain_id: str) -> None:
    domain = domain_repo.get_domain_by_id(db, domain_id)
    if domain is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    domain_repo.delete_domain(db, domain)
