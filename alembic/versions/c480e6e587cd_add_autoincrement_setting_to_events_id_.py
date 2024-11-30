"""Add autoincrement setting to events id column

Revision ID: c480e6e587cd
Revises: 0a317f567c2e
Create Date: 2024-11-28 09:33:55.412286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c480e6e587cd'
down_revision: Union[str, None] = '0a317f567c2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key('fk_category_id', 'events', 'cat', ['category'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_ownerid_id', 'events', 'users', ['owner_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('fk_category_id', 'events', type_='foreignkey')
    op.drop_constraint('fk_ownerid_id', 'events', type_='foreignkey')
