"""create domains table

Revision ID: 0002_create_domains
Revises: 0001_create_users
Create Date: 2026-09-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_create_domains"
down_revision: Union[str, None] = "0001_create_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

domain_status_enum = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    name="domain_status",
    create_type=False,
)


def upgrade() -> None:
    domain_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "domains",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=253), nullable=False),
        sa.Column("status", domain_status_enum, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_domains_name", "domains", ["name"], unique=True)
    op.create_index("ix_domains_created_by", "domains", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_domains_created_by", table_name="domains")
    op.drop_index("ix_domains_name", table_name="domains")
    op.drop_table("domains")
    domain_status_enum.drop(op.get_bind(), checkfirst=True)
