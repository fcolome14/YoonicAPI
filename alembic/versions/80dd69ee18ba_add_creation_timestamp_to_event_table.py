"""Add creation timestamp to event table

Revision ID: 80dd69ee18ba
Revises: b85ad78f27bd
Create Date: 2024-11-15 11:24:34.929302

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "80dd69ee18ba"
down_revision: Union[str, None] = "b85ad78f27bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    pass


def downgrade() -> None:
    op.drop_column("events", "created_at")
    pass
