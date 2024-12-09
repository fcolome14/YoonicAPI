"""Split Events into Header and Lines

Revision ID: dd49adc5a5ba
Revises: 2a1487a90b61
Create Date: 2024-12-03 16:06:30.146470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = 'dd49adc5a5ba'
down_revision: Union[str, None] = '2a1487a90b61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE events CASCADE")
    
    op.create_table("events_headers", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
                    sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")))
    op.add_column("events_headers", sa.Column("title", sa.String(), nullable=False))
    op.add_column("events_headers", sa.Column("description", sa.String(), nullable=True))
    op.add_column("events_headers", sa.Column("coordinates", sa.String(), nullable=False))
    op.add_column("events_headers", sa.Column("address", sa.String(), nullable=False))
    op.add_column("events_headers", sa.Column("img", sa.String(), nullable=True))
    op.add_column("events_headers", sa.Column("img2", sa.String(), nullable=True))
    op.add_column("events_headers", sa.Column("category", sa.Integer(), nullable=False))
    op.add_column("events_headers", sa.Column("owner_id", sa.Integer(), nullable=False))
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.add_column("events_headers", sa.Column("geom", Geometry('POINT'), nullable=True))
    op.execute("""
        UPDATE events_headers
        SET geom = ST_SetSRID(geom, 4326)
        WHERE ST_SRID(geom) = 0;
    """)
    
    op.create_foreign_key('fk_category_id', 'events_headers', 'cat', ['category'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_ownerid_id', 'events_headers', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    
    op.create_table("events_lines", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
                    sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")))
    op.add_column("events_lines", sa.Column("start", sa.DateTime(), nullable=False))
    op.add_column("events_lines", sa.Column("end", sa.DateTime(), nullable=False))
    op.add_column("events_lines", sa.Column("cost", sa.DOUBLE_PRECISION(), nullable=False, default=0.00))
    op.add_column("events_lines", sa.Column("capacity", sa.Integer(), nullable=False, default=0))
    op.add_column("events_lines", sa.Column("currency", sa.String(), nullable=True, default="EUR"))
    op.add_column("events_lines", sa.Column("isPublic", sa.Boolean(), nullable=False, default=True))
    op.add_column("events_lines", sa.Column("header_id", sa.Integer(), nullable=False))
    
    op.create_foreign_key('fk_linesid_headersid', 'events_lines', 'events_headers', ['header_id'], ['id'], ondelete='CASCADE')

def downgrade() -> None:
    pass
