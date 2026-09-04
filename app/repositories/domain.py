from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.domain import Domain, DomainStatus


def get_domain_by_id(db: Session, domain_id: str) -> Domain | None:
    return db.get(Domain, domain_id)


def get_domain_by_name(db: Session, name: str) -> Domain | None:
    return db.scalar(select(Domain).where(Domain.name == name))


def create_domain(
    db: Session,
    *,
    name: str,
    created_by: str,
    status: DomainStatus = DomainStatus.PENDING,
) -> Domain:
    domain = Domain(name=name, created_by=created_by, status=status)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def delete_domain(db: Session, domain: Domain) -> None:
    db.delete(domain)
    db.commit()


def list_domains(
    db: Session,
    *,
    page: int,
    limit: int,
    status: DomainStatus | None = None,
    search: str | None = None,
) -> tuple[list[Domain], int]:
    stmt = select(Domain)
    count_stmt = select(func.count()).select_from(Domain)

    if status is not None:
        stmt = stmt.where(Domain.status == status)
        count_stmt = count_stmt.where(Domain.status == status)

    if search:
        pattern = f"%{search.lower().strip()}%"
        stmt = stmt.where(Domain.name.ilike(pattern))
        count_stmt = count_stmt.where(Domain.name.ilike(pattern))

    total = int(db.scalar(count_stmt) or 0)
    offset = (page - 1) * limit
    items = list(
        db.scalars(
            stmt.order_by(Domain.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return items, total
