"""Ensure tg_user_id columns use BIGINT (Telegram IDs can exceed int32).

Alters users.tg_user_id and verification_applications.tg_user_id to BIGINT
only when current type is INTEGER (idempotent for DBs created with 001 that already use bigint).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_tg_user_id_bigint"
down_revision: Union[str, None] = "008_verification_applications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_type_is_integer(conn: sa.engine.Connection, table: str, column: str) -> bool:
    """True if column type is integer (int4), not bigint."""
    result = conn.execute(
        sa.text(
            """
            SELECT data_type FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    )
    row = result.fetchone()
    return row is not None and row[0] == "integer"


def upgrade() -> None:
    conn = op.get_bind()
    if _column_type_is_integer(conn, "users", "tg_user_id"):
        op.alter_column(
            "users",
            "tg_user_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )
    if _column_type_is_integer(conn, "verification_applications", "tg_user_id"):
        op.alter_column(
            "verification_applications",
            "tg_user_id",
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Downgrade only if you are sure no tg_user_id values exceed int32.
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'tg_user_id'"
        )
    )
    row = result.fetchone()
    if row is not None and row[0] == "bigint":
        op.alter_column(
            "users",
            "tg_user_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
    result = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'verification_applications' AND column_name = 'tg_user_id'"
        )
    )
    row = result.fetchone()
    if row is not None and row[0] == "bigint":
        op.alter_column(
            "verification_applications",
            "tg_user_id",
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
