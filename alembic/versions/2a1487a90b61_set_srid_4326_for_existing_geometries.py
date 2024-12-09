"""Set SRID 4326 for existing geometries

Revision ID: 2a1487a90b61
Revises: c42f93174103
Create Date: 2024-12-01 13:14:06.816685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a1487a90b61'
down_revision: Union[str, None] = 'c42f93174103'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE events
        SET geom = ST_SetSRID(geom, 4326)
        WHERE ST_SRID(geom) = 0;
    """)


def downgrade() -> None:
    pass
