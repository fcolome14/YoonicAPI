"""Add pk constraint id subs, events table

Revision ID: 1f958521ab42
Revises: 69a866554789
Create Date: 2024-11-15 11:53:58.037644

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f958521ab42"
down_revision: Union[str, None] = "69a866554789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_primary_key("pk_events", "events", ["id"])
    op.create_primary_key("pk_subs", "subs", ["id"])
    pass


def downgrade() -> None:
    pass
