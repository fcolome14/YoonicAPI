"""Create events table again

Revision ID: 224ce9ffe416
Revises: 3985f68cd4de
Create Date: 2024-11-28 11:03:51.798183

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "224ce9ffe416"
down_revision: Union[str, None] = "3985f68cd4de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column(
            "id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
    )
    op.add_column("events", sa.Column("title", sa.String(), nullable=False))
    op.add_column("events", sa.Column("description", sa.String(), nullable=True))
    op.add_column("events", sa.Column("coordinates", sa.String(), nullable=False))
    op.add_column("events", sa.Column("address", sa.String(), nullable=False))
    op.add_column("events", sa.Column("img", sa.String(), nullable=True))
    op.add_column("events", sa.Column("img2", sa.String(), nullable=True))
    op.add_column("events", sa.Column("start", sa.DateTime(), nullable=False))
    op.add_column("events", sa.Column("end", sa.DateTime(), nullable=False))
    op.add_column(
        "events", sa.Column("cost", sa.DOUBLE_PRECISION(), nullable=False, default=0.00)
    )
    op.add_column(
        "events", sa.Column("capacity", sa.Integer(), nullable=False, default=0)
    )
    op.add_column(
        "events", sa.Column("currency", sa.String(), nullable=True, default="EUR")
    )
    op.add_column(
        "events", sa.Column("isPublic", sa.Boolean(), nullable=False, default=True)
    )
    op.add_column("events", sa.Column("category", sa.Integer(), nullable=False))
    op.add_column("events", sa.Column("owner_id", sa.Integer(), nullable=False))


def downgrade() -> None:
    op.drop_table("events")
