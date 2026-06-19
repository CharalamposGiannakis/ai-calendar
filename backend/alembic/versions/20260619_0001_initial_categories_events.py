"""Initial categories and events schema.

Revision ID: 20260619_0001
Revises:
Create Date: 2026-06-19 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260619_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_categories_id", "categories", ["id"], unique=False)
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_datetime", sa.DateTime(timezone=False), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=False), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_end_datetime", "events", ["end_datetime"], unique=False)
    op.create_index("ix_events_id", "events", ["id"], unique=False)
    op.create_index("ix_events_start_datetime", "events", ["start_datetime"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_events_start_datetime", table_name="events")
    op.drop_index("ix_events_id", table_name="events")
    op.drop_index("ix_events_end_datetime", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_index("ix_categories_id", table_name="categories")
    op.drop_table("categories")
