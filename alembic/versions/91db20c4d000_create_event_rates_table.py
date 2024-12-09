"""Create event_rates table

Revision ID: 91db20c4d000
Revises: dd49adc5a5ba
Create Date: 2024-12-03 17:56:19.966412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91db20c4d000'
down_revision: Union[str, None] = 'dd49adc5a5ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("rate", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
                    sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")))
    op.add_column("rate", sa.Column("title", sa.String(), nullable=False))
    op.add_column("rate", sa.Column("amount", sa.FLOAT(), nullable=False))
    op.add_column("rate", sa.Column("currency", sa.String(), nullable=False, default="EUR"))
    op.add_column("rate", sa.Column("line_id", sa.Integer(), nullable=False))
    
    op.drop_column("events_lines","cost")
    op.drop_column("events_lines","currency")
    op.add_column("events_lines", sa.Column("cost_id", sa.Integer(), nullable=False))
    
    op.create_foreign_key('fk_lineid_eventid', 'rate', 'events_lines', ['line_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.execute("DROP TABLE rate CASCADE")
    op.drop_column("events_lines", "cost_id")
