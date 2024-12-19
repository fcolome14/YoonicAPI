"""Create subcategories table

Revision ID: 049a0058f44a
Revises: 36b30b8dd601
Create Date: 2024-12-17 16:36:27.718263

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "049a0058f44a"
down_revision: Union[str, None] = "36b30b8dd601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subcat",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
    )
    op.add_column("subcat", sa.Column("name", sa.String(), nullable=False))
    op.add_column("subcat", sa.Column("cat", sa.Integer(), nullable=False))  # fk
    op.add_column("subcat", sa.Column("code", sa.String(), nullable=False))
    op.add_column(
        "subcat",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.add_column(
        "events_headers", sa.Column("score", sa.Integer(), nullable=False, default=0)
    )
    op.create_foreign_key("fk_cat_id", "subcat", "cat", ["cat"], ["id"])


def downgrade() -> None:
    op.drop_table("subcat")
    op.drop_column("events_headers", "score")
    op.drop_constraint("fk_cat_id", "subcat")
