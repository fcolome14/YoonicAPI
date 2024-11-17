"""Modify users table columns name, lastname

Revision ID: 011fd679417e
Revises: eff0c66b966d
Create Date: 2024-11-17 13:02:53.251376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011fd679417e'
down_revision: Union[str, None] = 'eff0c66b966d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "name")
    op.drop_column("users", "lastname")
    op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    pass


def downgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(), nullable=False))
    op.add_column("users", sa.Column("lastname", sa.String(), nullable=True))
    op.drop_column("users", "full_name")
    pass
