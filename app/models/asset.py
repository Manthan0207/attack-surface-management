from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssetType(StrEnum):
    A = "A"
    AAAA = "AAAA"
    NS = "NS"
    MX = "MX"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    scan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type", native_enum=True),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scan = relationship("Scan", back_populates="assets")
    domain = relationship("Domain")

    def __repr__(self) -> str:
        return f"<Asset id={self.id} type={self.type} value={self.value}>"
