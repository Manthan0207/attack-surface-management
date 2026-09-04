from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import DomainStatus


class DomainCreateRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=253)


class DomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: DomainStatus


class DomainListResponse(BaseModel):
    items: list[DomainResponse]
    page: int
    limit: int
    total: int
