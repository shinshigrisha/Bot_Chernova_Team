"""Add resolution fields to verification_applications (decision, resolved_at).

Expand-only: allows recording admin decision on each application.
Revision id kept short (017_verif_resolution) to fit alembic_version.version_num(32).
If this migration was partially applied (columns added but version update failed),
run: UPDATE alembic_version SET version_num='017_verif_resolution' WHERE version_num='016_minimal_production_core';
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "017_verif_resolution"
down_revision: Union[str, None] = "016_minimal_production_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "verification_applications",
        sa.Column("decision", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "verification_applications",
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("verification_applications", "resolved_at")
    op.drop_column("verification_applications", "decision")
