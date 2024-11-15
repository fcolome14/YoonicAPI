"""Create user table

Revision ID: 0607798b435b
Revises: 
Create Date: 2024-11-15 09:49:11.038959

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0607798b435b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False))
    op.add_column("users", sa.Column("username", sa.String(), nullable=False))
    op.add_column("users", sa.Column("name", sa.String(), nullable=False))
    op.add_column("users", sa.Column("lastname", sa.String(), nullable=False))
    op.add_column("users", sa.Column("email", sa.String(), nullable=False))
    op.add_column("users", sa.Column("password", sa.String(), nullable=False))
    op.add_column("users", sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')))
    op.create_unique_constraint(None, "users", ["username", "email"])
    pass


def downgrade() -> None:
    op.drop_table("users")
    pass
