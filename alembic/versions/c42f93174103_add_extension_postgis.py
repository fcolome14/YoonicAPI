"""Add extension PostGis

Revision ID: c42f93174103
Revises: 33ce9af27122
Create Date: 2024-12-01 11:04:30.810593

"""

from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c42f93174103"
down_revision: Union[str, None] = "33ce9af27122"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.add_column("events", sa.Column("geom", Geometry("POINT"), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "geom")
    op.execute("DROP EXTENSION IF EXISTS postgis")
