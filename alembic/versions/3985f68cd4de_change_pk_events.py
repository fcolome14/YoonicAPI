"""Drop events table

Revision ID: 3985f68cd4de
Revises: c480e6e587cd
Create Date: 2024-11-28 10:30:54.394861

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3985f68cd4de"
down_revision: Union[str, None] = "c480e6e587cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events CASCADE")


def downgrade() -> None:
    pass
