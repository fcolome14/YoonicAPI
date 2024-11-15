"""Create event table

Revision ID: b85ad78f27bd
Revises: 7488b2cbf23c
Create Date: 2024-11-15 11:08:22.976385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b85ad78f27bd'
down_revision: Union[str, None] = '7488b2cbf23c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("events", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False))
    op.add_column("events", sa.Column("name", sa.String(), nullable=False))
    op.add_column("events", sa.Column("description", sa.String(), nullable=True))
    op.add_column("events", sa.Column("coordX", sa.Float(), nullable=False))
    op.add_column("events", sa.Column("coordY", sa.Float(), nullable=False))
    op.add_column("events", sa.Column("address", sa.String(), nullable=False))
    op.add_column("events", sa.Column("img", sa.String(), nullable=True))
    op.add_column("events", sa.Column("img2", sa.String(), nullable=True))
    op.add_column("events", sa.Column("datetime_start", sa.DateTime(), nullable=False))
    op.add_column("events", sa.Column("datetime_end", sa.DateTime(), nullable=False))
    op.add_column("events", sa.Column("cost", sa.Float(), nullable=False, default=0.00))
    op.add_column("events", sa.Column("capacity", sa.Integer(), nullable=False, default=0))
    op.add_column("events", sa.Column("currency", sa.String(), nullable=True, default="€"))
    op.add_column("events", sa.Column("isPublic", sa.Boolean(), nullable=False))
    pass


def downgrade() -> None:
    op.drop_table("events")
    pass
