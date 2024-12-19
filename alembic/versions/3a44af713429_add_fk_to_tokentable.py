"""Add fk to tokentable

Revision ID: 3a44af713429
Revises: 1a87316a0b90
Create Date: 2024-11-21 19:00:45.522964

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a44af713429"
down_revision: Union[str, None] = "1a87316a0b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # op.add_column('tokentable', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_tokentable_users", "tokentable", "users", ["user_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_tokentable_users", "tokentable", type_="foreignkey")
    # op.drop_column('tokentable', 'user_id')
