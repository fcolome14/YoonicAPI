"""Create register validation table

Revision ID: a403ebbef299
Revises: eff0c66b966d
Create Date: 2024-11-15 12:10:32.221827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a403ebbef299'
down_revision: Union[str, None] = 'eff0c66b966d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
