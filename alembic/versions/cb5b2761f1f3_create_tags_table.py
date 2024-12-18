"""Create tags table

Revision ID: cb5b2761f1f3
Revises: 049a0058f44a
Create Date: 2024-12-17 18:01:44.943864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb5b2761f1f3'
down_revision: Union[str, None] = '049a0058f44a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("tags", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False))
    op.add_column("tags", sa.Column("name", sa.String(), nullable=False))
    op.add_column("tags", sa.Column("subcat", sa.Integer(), nullable=False)) #fk
    op.add_column("tags", sa.Column("weight", sa.Integer(), nullable=False, default=1))
    op.add_column("tags", sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')))
    
    op.create_foreign_key('fk_subcat_id', 'tags', 'subcat', ['subcat'], ['id'])


def downgrade() -> None:
    op.drop_table("tags")
    op.drop_constraint("fk_subcat_id", "tags")
