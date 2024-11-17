"""Add extra users columns to handle validation code

Revision ID: 1098e4ce307a
Revises: 011fd679417e
Create Date: 2024-11-17 15:38:49.201932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1098e4ce307a'
down_revision: Union[str, None] = '011fd679417e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("code", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("is_validated", sa.Boolean, default=False))
    op.add_column("users", sa.Column("code_expiration", sa.TIMESTAMP(timezone=True), nullable=True))
    pass

def downgrade() -> None:
    op.drop_column("users", "code")
    op.drop_column("users", "is_validated")
    op.drop_column("users", "code_expiration")
    pass
