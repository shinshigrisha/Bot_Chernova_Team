"""Add user_status enum and status column to users.

Expand-only, backwards-compatible migration:
- Creates PostgreSQL ENUM type user_status.
- Adds non-null status column to users with server default 'guest'.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007_add_user_status"
down_revision: Union[str, None] = "006_faq_embedding_vector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_status_enum = sa.Enum(
    "guest",
    "pending",
    "approved",
    "rejected",
    "blocked",
    name="user_status",
)


def upgrade() -> None:
    # 1) Create ENUM type if not exists (idempotent-ish: safe when type missing).
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_enums = {e["name"] for e in inspector.get_enums()}
    if "user_status" not in existing_enums:
        user_status_enum.create(bind, checkfirst=True)

    # 2) Add column with server_default 'guest' to keep existing rows valid.
    op.add_column(
        "users",
        sa.Column(
            "status",
            user_status_enum,
            nullable=False,
            server_default="guest",
        ),
    )


def downgrade() -> None:
    # Order: drop column first, then enum type.
    op.drop_column("users", "status")
    bind = op.get_bind()
    user_status_enum.drop(bind, checkfirst=True)

