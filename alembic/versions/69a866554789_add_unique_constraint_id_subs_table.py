"""Add unique constraint id subs table

Revision ID: 69a866554789
Revises: dc6fd407aae7
Create Date: 2024-11-15 11:51:59.377410

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69a866554789'
down_revision: Union[str, None] = 'dc6fd407aae7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_subs_id", "subs", ["id"])
    pass


def downgrade() -> None:
    pass
