"""Added category column

Revision ID: 7f00d69e62b4
Revises: 858b376b4221
Create Date: 2024-11-27 16:29:41.515975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f00d69e62b4'
down_revision: Union[str, None] = '858b376b4221'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("category", sa.Integer(), nullable=False, default=1))
    op.create_foreign_key("fk_events_cat", "events", "cat", ["category"], ["id"])


def downgrade() -> None:
    op.drop_column("events", "category")
    op.drop_constraint("fk_events_cat", "events", type_="foreignkey")
