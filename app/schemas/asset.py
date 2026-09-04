from pydantic import BaseModel, ConfigDict, Field

from app.models.asset import AssetType


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: str = Field(description="Domain name")
    type: AssetType
    value: str


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    page: int
    limit: int
    total: int
