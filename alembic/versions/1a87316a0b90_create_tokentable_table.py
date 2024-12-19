"""Create tokentable table

Revision ID: 1a87316a0b90
Revises: 1098e4ce307a
Create Date: 2024-11-19 13:01:43.090523

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a87316a0b90"
down_revision: Union[str, None] = "1098e4ce307a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tokentable",
        sa.Column("access_token", sa.VARCHAR(), primary_key=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("refresh_token", sa.VARCHAR(), nullable=False),
        sa.Column("user_id", sa.INTEGER()),
        sa.Column("status", sa.BOOLEAN()),
    )


def downgrade() -> None:
    op.drop_table("tokentable")
    pass
