from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.time_utils import UTCDateTime


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["Event"]] = relationship("Event", back_populates="category")
    candidate_events: Mapped[list["CandidateEvent"]] = relationship(
        "CandidateEvent", back_populates="category"
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "all_day = 1 OR (start_datetime IS NOT NULL AND end_datetime IS NOT NULL "
            "AND timezone_name IS NOT NULL AND start_date IS NULL AND end_date IS NULL)",
            name="ck_events_timed_shape",
        ),
        CheckConstraint(
            "all_day = 0 OR (start_date IS NOT NULL AND end_date IS NOT NULL "
            "AND start_datetime IS NULL AND end_datetime IS NULL AND timezone_name IS NULL)",
            name="ck_events_all_day_shape",
        ),
        CheckConstraint(
            "all_day = 1 OR end_datetime > start_datetime",
            name="ck_events_timed_order",
        ),
        CheckConstraint(
            "all_day = 0 OR end_date > start_date",
            name="ck_events_all_day_order",
        ),
        UniqueConstraint("candidate_event_id", name="uq_events_candidate_event_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_datetime: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), index=True, nullable=True
    )
    end_datetime: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), index=True, nullable=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timezone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    candidate_event_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("candidate_events.id"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[Category | None] = relationship("Category", back_populates="events")
    candidate_event: Mapped["CandidateEvent | None"] = relationship(
        "CandidateEvent", back_populates="event", uselist=False
    )


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_source_documents_size_nonnegative"),
        CheckConstraint(
            "instr(storage_path, ':') = 0 AND substr(storage_path, 1, 1) != '/' "
            "AND substr(storage_path, 1, 1) != '\\'",
            name="ck_source_documents_relative_storage_path",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    import_batches: Mapped[list["ImportBatch"]] = relationship(
        "ImportBatch", back_populates="source_document"
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready_for_review', 'completed', 'failed')",
            name="ck_import_batches_status",
        ),
        CheckConstraint(
            "total_rows_detected >= 0", name="ck_import_batches_rows_nonnegative"
        ),
        CheckConstraint(
            "total_candidate_events >= 0",
            name="ck_import_batches_candidates_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", server_default=text("'pending'"), nullable=False
    )
    parser_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_rows_detected: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    total_candidate_events: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    source_document: Mapped[SourceDocument] = relationship(
        "SourceDocument", back_populates="import_batches"
    )
    import_rows: Mapped[list["ImportRow"]] = relationship(
        "ImportRow", back_populates="import_batch"
    )
    candidate_events: Mapped[list["CandidateEvent"]] = relationship(
        "CandidateEvent", back_populates="import_batch"
    )


class ImportRow(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        CheckConstraint(
            "parse_status IN ('pending', 'parsed', 'skipped', 'failed')",
            name="ck_import_rows_parse_status",
        ),
        UniqueConstraint("import_batch_id", "row_index", name="uq_import_rows_batch_row_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id"), index=True, nullable=False
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_locator_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(32), default="pending", server_default=text("'pending'"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    import_batch: Mapped[ImportBatch] = relationship("ImportBatch", back_populates="import_rows")
    candidate_events: Mapped[list["CandidateEvent"]] = relationship(
        "CandidateEvent", back_populates="import_row"
    )


class CandidateEvent(Base):
    __tablename__ = "candidate_events"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_candidate_events_review_status",
        ),
        CheckConstraint(
            "all_day = 1 OR (start_datetime IS NOT NULL AND end_datetime IS NOT NULL "
            "AND timezone_name IS NOT NULL AND start_date IS NULL AND end_date IS NULL)",
            name="ck_candidate_events_timed_shape",
        ),
        CheckConstraint(
            "all_day = 0 OR (start_date IS NOT NULL AND end_date IS NOT NULL "
            "AND start_datetime IS NULL AND end_datetime IS NULL AND timezone_name IS NULL)",
            name="ck_candidate_events_all_day_shape",
        ),
        CheckConstraint(
            "all_day = 1 OR end_datetime > start_datetime",
            name="ck_candidate_events_timed_order",
        ),
        CheckConstraint(
            "all_day = 0 OR end_date > start_date",
            name="ck_candidate_events_all_day_order",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id"), index=True, nullable=False
    )
    import_row_id: Mapped[int] = mapped_column(
        ForeignKey("import_rows.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    start_datetime: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    end_datetime: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timezone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    review_status: Mapped[str] = mapped_column(
        String(32), default="pending", server_default=text("'pending'"), nullable=False
    )
    was_edited: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    import_batch: Mapped[ImportBatch] = relationship(
        "ImportBatch", back_populates="candidate_events"
    )
    import_row: Mapped[ImportRow] = relationship("ImportRow", back_populates="candidate_events")
    category: Mapped[Category | None] = relationship("Category", back_populates="candidate_events")
    event: Mapped[Event | None] = relationship("Event", back_populates="candidate_event")
