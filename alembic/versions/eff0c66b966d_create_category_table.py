"""Create category table

Revision ID: eff0c66b966d
Revises: 1f958521ab42
Create Date: 2024-11-15 11:56:42.621209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eff0c66b966d'
down_revision: Union[str, None] = '1f958521ab42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("cat", sa.Column("id", sa.Integer(), primary_key=True, nullable=False, autoincrement=True),
                    sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")))
    op.add_column("cat", sa.Column("code", sa.String(), nullable=False))
    op.add_column("cat", sa.Column("name", sa.String(), nullable=False))
    pass


def downgrade() -> None:
    op.drop_table("cat")
    pass
