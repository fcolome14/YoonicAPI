"""Added owner field in Events table

Revision ID: 858b376b4221
Revises: 3a44af713429
Create Date: 2024-11-27 16:01:19.576248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '858b376b4221'
down_revision: Union[str, None] = '3a44af713429'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("owner_id", sa.Integer(), nullable=False))
    op.alter_column("events", "name", nullable=False, new_column_name="title")
    op.alter_column("events", "datetime_start", nullable=False, new_column_name="start")
    op.alter_column("events", "datetime_end", nullable=False, new_column_name="end")
    op.drop_column("events", "coordX")
    op.drop_column("events", "coordY")
    op.add_column("events", sa.Column("coordinates", sa.String(), nullable=False))
    op.create_foreign_key("fk_events_users", "events", "users", ["owner_id"], ["id"])


def downgrade() -> None:
    op.drop_table("events", "owner_id")
    op.alter_column("events", "title", nullable=False, new_column_name="name")
    op.alter_column("events", "start", nullable=False, new_column_name="datetime_start")
    op.alter_column("events", "end", nullable=False, new_column_name="datetime_end")
    op.drop_column("events", "coordinates")
    op.add_column("events", sa.Column("coordX", sa.DOUBLE_PRECISION(), nullable=False))
    op.add_column("events", sa.Column("coordY", sa.DOUBLE_PRECISION(), nullable=False))
    op.drop_constraint("fk_events_users", "events", type_="foreignkey")
