from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

DEFAULT_TIMEZONE = "Europe/Amsterdam"


class TimeSemanticsError(ValueError):
    """Raised when a value cannot be represented by the event time contract."""


def get_timezone(timezone_name: str) -> ZoneInfo:
    if not timezone_name:
        raise TimeSemanticsError("timezone_name is required for timed events.")

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise TimeSemanticsError("timezone_name must be a valid IANA timezone.") from error


def _valid_local_folds(value: datetime, zone: ZoneInfo) -> list[datetime]:
    candidates = []
    for fold in (0, 1):
        local_value = value.replace(tzinfo=zone, fold=fold)
        round_trip = local_value.astimezone(UTC).astimezone(zone)
        if round_trip.replace(tzinfo=None) == value:
            candidates.append(local_value)
    return candidates


def local_naive_to_utc(value: datetime, timezone_name: str) -> datetime:
    """Convert a local wall-clock value to UTC without guessing DST folds."""
    if value.tzinfo is not None and value.utcoffset() is not None:
        raise TimeSemanticsError("Expected a naive local datetime.")

    zone = get_timezone(timezone_name)
    candidates = _valid_local_folds(value, zone)

    if not candidates:
        raise TimeSemanticsError("Local datetime does not exist in timezone due to DST.")

    if len(candidates) == 2 and candidates[0].utcoffset() != candidates[1].utcoffset():
        raise TimeSemanticsError("Local datetime is ambiguous in timezone due to DST.")

    return candidates[0].astimezone(UTC)


def aware_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise TimeSemanticsError("Timed datetimes must include an offset or timezone_name.")
    return value.astimezone(UTC)


def normalize_timed_datetime(value: datetime, timezone_name: str) -> datetime:
    get_timezone(timezone_name)
    if value.tzinfo is None or value.utcoffset() is None:
        return local_naive_to_utc(value, timezone_name)
    return aware_to_utc(value)


def utc_to_timezone(value: datetime, timezone_name: str) -> datetime:
    zone = get_timezone(timezone_name)
    return aware_to_utc(value).astimezone(zone)


def local_date_boundary_to_utc(value: date, timezone_name: str) -> datetime:
    return local_naive_to_utc(datetime.combine(value, time.min), timezone_name)


def utc_to_database_value(value: datetime) -> datetime:
    return aware_to_utc(value).replace(tzinfo=None)


def database_value_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class UTCDateTime(TypeDecorator):
    """Persist UTC as SQLite-naive values while exposing aware UTC datetimes."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=False))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return utc_to_database_value(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return database_value_to_utc(value)
