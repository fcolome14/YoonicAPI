"""Create subscriptions table

Revision ID: dc6fd407aae7
Revises: 80dd69ee18ba
Create Date: 2024-11-15 11:27:42.995610

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc6fd407aae7"
down_revision: Union[str, None] = "80dd69ee18ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_events_id", "events", ["id"])
    op.create_table(
        "subs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
    )
    op.add_column("subs", sa.Column("user", sa.Integer(), nullable=False))
    op.add_column("subs", sa.Column("event", sa.Integer(), nullable=False))
    op.create_foreign_key(
        "fk_subs_user", "subs", "users", ["user"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_subs_event", "subs", "events", ["event"], ["id"], ondelete="CASCADE"
    )
    pass


def downgrade() -> None:
    op.drop_table("subs")
    pass
