"""Add users table password_recovery flag

Revision ID: 978aa8424b1d
Revises: 1098e4ce307a
Create Date: 2024-11-18 10:05:18.670964

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '978aa8424b1d'
down_revision: Union[str, None] = '1098e4ce307a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_recovery", sa.Boolean(), default=False))
    pass


def downgrade() -> None:
    op.drop_column("users", "password_recovery")
    pass
