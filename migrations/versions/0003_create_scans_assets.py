"""create scans and assets tables

Revision ID: 0003_create_scans_assets
Revises: 0002_create_domains
Create Date: 2026-09-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_scans_assets"
down_revision: Union[str, None] = "0002_create_domains"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

scan_status_enum = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    name="scan_status",
    create_type=False,
)
asset_type_enum = postgresql.ENUM(
    "A",
    "AAAA",
    "NS",
    "MX",
    name="asset_type",
    create_type=False,
)


def upgrade() -> None:
    scan_status_enum.create(op.get_bind(), checkfirst=True)
    asset_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", scan_status_enum, nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_scans_domain_id", "scans", ["domain_id"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("type", asset_type_enum, nullable=False),
        sa.Column("value", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_assets_scan_id", "assets", ["scan_id"], unique=False)
    op.create_index("ix_assets_domain_id", "assets", ["domain_id"], unique=False)
    op.create_index("ix_assets_domain_id_type", "assets", ["domain_id", "type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assets_domain_id_type", table_name="assets")
    op.drop_index("ix_assets_domain_id", table_name="assets")
    op.drop_index("ix_assets_scan_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_scans_domain_id", table_name="scans")
    op.drop_table("scans")
    asset_type_enum.drop(op.get_bind(), checkfirst=True)
    scan_status_enum.drop(op.get_bind(), checkfirst=True)
