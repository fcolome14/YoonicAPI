"""Add status codes table

Revision ID: 36b30b8dd601
Revises: 91db20c4d000
Create Date: 2024-12-17 16:08:37.599201

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "36b30b8dd601"
down_revision: Union[str, None] = "91db20c4d000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "status_codes",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
    )
    op.add_column("status_codes", sa.Column("name", sa.String(), nullable=False))
    op.add_column(
        "status_codes",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.add_column("events_headers", sa.Column("status", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "fk_status_id", "events_headers", "status_codes", ["status"], ["id"]
    )


def downgrade() -> None:
    op.drop_table("status_codes")
    op.drop_column("events_headers", "status")
    op.drop_constraint("fk_status_id", "events_headers")
