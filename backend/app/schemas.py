from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

from app.time_utils import TimeSemanticsError, get_timezone, normalize_timed_datetime


class CategoryBase(BaseModel):
    name: str
    color: str | None = None
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    description: str | None = None


class CategoryRead(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SourceDocumentRead(BaseModel):
    id: int
    original_filename: str
    storage_path: str
    file_type: str
    mime_type: str | None = None
    size_bytes: int
    sha256_checksum: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportBatchRead(BaseModel):
    id: int
    source_document_id: int
    status: str
    parser_name: str | None = None
    parser_version: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_rows_detected: int
    total_candidate_events: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExcelUploadResponse(BaseModel):
    source_document: SourceDocumentRead
    import_batch: ImportBatchRead


def normalize_event_shape(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    all_day = normalized.get("all_day", False)

    if all_day:
        if normalized.get("start_date") is None or normalized.get("end_date") is None:
            raise ValueError("All-day events require start_date and exclusive end_date.")
        if any(
            normalized.get(field) is not None
            for field in ("start_datetime", "end_datetime", "timezone_name")
        ):
            raise ValueError("All-day events cannot include timed datetime fields or timezone_name.")
        if normalized["end_date"] <= normalized["start_date"]:
            raise ValueError("end_date must be later than start_date.")
        normalized["start_datetime"] = None
        normalized["end_datetime"] = None
        normalized["timezone_name"] = None
        return normalized

    start_datetime = normalized.get("start_datetime")
    end_datetime = normalized.get("end_datetime")
    timezone_name = normalized.get("timezone_name")
    if start_datetime is None or end_datetime is None or not timezone_name:
        raise ValueError(
            "Timed events require start_datetime, end_datetime, and timezone_name."
        )
    if normalized.get("start_date") is not None or normalized.get("end_date") is not None:
        raise ValueError("Timed events cannot include date-only fields.")

    try:
        get_timezone(timezone_name)
        start_utc = normalize_timed_datetime(start_datetime, timezone_name)
        end_utc = normalize_timed_datetime(end_datetime, timezone_name)
    except TimeSemanticsError as error:
        raise ValueError(str(error)) from error

    if end_utc <= start_utc:
        raise ValueError("end_datetime must be later than start_datetime.")

    normalized["start_datetime"] = start_utc
    normalized["end_datetime"] = end_utc
    normalized["start_date"] = None
    normalized["end_date"] = None
    return normalized


class EventBase(BaseModel):
    title: str
    description: str | None = None
    all_day: bool = False
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    timezone_name: str | None = None
    location: str | None = None
    category_id: int | None = None
    source_type: str = "manual"
    status: str = "active"


class EventCreate(EventBase):
    @model_validator(mode="after")
    def validate_and_normalize_time_shape(self):
        normalized = normalize_event_shape(self.model_dump())
        for field_name, value in normalized.items():
            setattr(self, field_name, value)
        return self


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    all_day: bool | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    timezone_name: str | None = None
    location: str | None = None
    category_id: int | None = None
    source_type: str | None = None
    status: str | None = None


class EventRead(EventBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start_datetime", "end_datetime", when_used="json")
    def serialize_utc_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
