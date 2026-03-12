"""Add verification_applications table.

Expand-only, backwards-compatible migration:
- Creates table for storing verification applications.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "008_verification_applications"
down_revision: Union[str, None] = "007_add_user_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verification_applications",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("tt_number", sa.String(length=64), nullable=False),
        sa.Column("ds_code", sa.String(length=64), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_verification_applications_tg_user",
        "verification_applications",
        ["tg_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_verification_applications_tg_user", table_name="verification_applications")
    op.drop_table("verification_applications")

