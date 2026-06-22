"""Add the review-first import pipeline foundation.

Revision ID: 20260623_0003
Revises: 20260623_0002
Create Date: 2026-06-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260623_0003"
down_revision: Union[str, Sequence[str], None] = "20260623_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_source_documents_size_nonnegative"),
        sa.CheckConstraint(
            "instr(storage_path, ':') = 0 AND substr(storage_path, 1, 1) != '/' "
            "AND substr(storage_path, 1, 1) != '\\'",
            name="ck_source_documents_relative_storage_path",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path", name="uq_source_documents_storage_path"),
    )
    op.create_index(
        "ix_source_documents_sha256_checksum",
        "source_documents",
        ["sha256_checksum"],
        unique=False,
    )

    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("parser_name", sa.String(length=100), nullable=True),
        sa.Column("parser_version", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "total_rows_detected", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "total_candidate_events", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready_for_review', 'completed', 'failed')",
            name="ck_import_batches_status",
        ),
        sa.CheckConstraint(
            "total_rows_detected >= 0", name="ck_import_batches_rows_nonnegative"
        ),
        sa.CheckConstraint(
            "total_candidate_events >= 0",
            name="ck_import_batches_candidates_nonnegative",
        ),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_batches_source_document_id",
        "import_batches",
        ["source_document_id"],
        unique=False,
    )

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("source_locator_json", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("raw_data_json", sa.Text(), nullable=True),
        sa.Column(
            "parse_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "parse_status IN ('pending', 'parsed', 'skipped', 'failed')",
            name="ck_import_rows_parse_status",
        ),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_batch_id", "row_index", name="uq_import_rows_batch_row_index"),
    )
    op.create_index(
        "ix_import_rows_import_batch_id",
        "import_rows",
        ["import_batch_id"],
        unique=False,
    )

    op.create_table(
        "candidate_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_batch_id", sa.Integer(), nullable=False),
        sa.Column("import_row_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("start_datetime", sa.DateTime(timezone=False), nullable=True),
        sa.Column("end_datetime", sa.DateTime(timezone=False), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("timezone_name", sa.String(length=64), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=32),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "was_edited", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_candidate_events_review_status",
        ),
        sa.CheckConstraint(
            "all_day = 1 OR (start_datetime IS NOT NULL AND end_datetime IS NOT NULL "
            "AND timezone_name IS NOT NULL AND start_date IS NULL AND end_date IS NULL)",
            name="ck_candidate_events_timed_shape",
        ),
        sa.CheckConstraint(
            "all_day = 0 OR (start_date IS NOT NULL AND end_date IS NOT NULL "
            "AND start_datetime IS NULL AND end_datetime IS NULL AND timezone_name IS NULL)",
            name="ck_candidate_events_all_day_shape",
        ),
        sa.CheckConstraint(
            "all_day = 1 OR end_datetime > start_datetime",
            name="ck_candidate_events_timed_order",
        ),
        sa.CheckConstraint(
            "all_day = 0 OR end_date > start_date",
            name="ck_candidate_events_all_day_order",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"]),
        sa.ForeignKeyConstraint(["import_row_id"], ["import_rows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_events_import_batch_id",
        "candidate_events",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_events_import_row_id",
        "candidate_events",
        ["import_row_id"],
        unique=False,
    )

    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("candidate_event_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_events_candidate_event_id_candidate_events",
            "candidate_events",
            ["candidate_event_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_events_candidate_event_id", ["candidate_event_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_constraint("uq_events_candidate_event_id", type_="unique")
        batch_op.drop_constraint(
            "fk_events_candidate_event_id_candidate_events", type_="foreignkey"
        )
        batch_op.drop_column("candidate_event_id")

    op.drop_index("ix_candidate_events_import_row_id", table_name="candidate_events")
    op.drop_index("ix_candidate_events_import_batch_id", table_name="candidate_events")
    op.drop_table("candidate_events")

    op.drop_index("ix_import_rows_import_batch_id", table_name="import_rows")
    op.drop_table("import_rows")

    op.drop_index("ix_import_batches_source_document_id", table_name="import_batches")
    op.drop_table("import_batches")

    op.drop_index("ix_source_documents_sha256_checksum", table_name="source_documents")
    op.drop_table("source_documents")
