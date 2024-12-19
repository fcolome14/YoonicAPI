"""Upgrade users table unique constraints columns

Revision ID: 7488b2cbf23c
Revises: 0607798b435b
Create Date: 2024-11-15 10:55:16.879009

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7488b2cbf23c"
down_revision: Union[str, None] = "0607798b435b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("users_username_email_key", "users", type_="unique")
    op.create_unique_constraint("uq_user_username", "users", ["username"])
    op.create_unique_constraint("uq_user_email", "users", ["email"])
    pass


def downgrade() -> None:
    op.create_unique_constraint(None, "users", ["username", "email"])
    pass
