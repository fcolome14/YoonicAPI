"""Add fks

Revision ID: 33ce9af27122
Revises: 224ce9ffe416
Create Date: 2024-11-28 11:22:47.708991

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "33ce9af27122"
down_revision: Union[str, None] = "224ce9ffe416"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_category_id", "events", "cat", ["category"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_ownerid_id", "events", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_user_id", "subs", "users", ["user"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_event_id", "subs", "events", ["event"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("fk_category_id", "events", type_="foreignkey")
    op.drop_constraint("fk_ownerid_id", "events", type_="foreignkey")
    op.drop_constraint("fk_user_id", "subs", type_="foreignkey")
    op.drop_constraint("fk_event_id", "subs", type_="foreignkey")
    op.drop_constraint("events_category_key", "events", type_="unique")
