"""Fix fk errors in cat table

Revision ID: 0a317f567c2e
Revises: 7f00d69e62b4
Create Date: 2024-11-27 17:24:16.066244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a317f567c2e'
down_revision: Union[str, None] = '7f00d69e62b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_events_cat", "events", type_="foreignkey")
    op.create_foreign_key("fk_events_cat", "events", "cat", ["category"], ["id"], ondelete='CASCADE')

def downgrade() -> None:
    op.drop_constraint("fk_events_cat", "events", type_="foreignkey")

