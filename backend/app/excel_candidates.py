from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import json
import re
from typing import Any

from app.time_utils import DEFAULT_TIMEZONE, TimeSemanticsError, normalize_timed_datetime

HEADER_ALIASES = {
    "title": {"title", "event", "summary", "name"},
    "date": {"date", "start_date"},
    "start_time": {"start_time", "start", "from"},
    "end_time": {"end_time", "end", "to"},
    "end_date": {"end_date", "last_day"},
    "all_day": {"all_day", "all day", "is_all_day"},
    "category": {"category"},
    "location": {"location"},
    "description": {"description", "notes"},
    "timezone_name": {"timezone", "timezone_name"},
}


class CandidateGenerationError(ValueError):
    pass


@dataclass(frozen=True)
class ImportRowInput:
    id: int
    row_index: int
    raw_data_json: str | None
    raw_text: str | None


@dataclass(frozen=True)
class CandidateDraft:
    import_row_id: int
    source_row_index: int
    title: str
    description: str | None
    all_day: bool
    start_datetime: datetime | None
    end_datetime: datetime | None
    start_date: date | None
    end_date: date | None
    timezone_name: str | None
    location: str | None
    category_id: int | None


@dataclass(frozen=True)
class RowIssue:
    import_row_id: int
    row_index: int
    status: str
    message: str


@dataclass(frozen=True)
class CandidateGenerationResult:
    header_row_id: int
    header_row_index: int
    rows_inspected: int
    candidates: list[CandidateDraft]
    row_issues: list[RowIssue]


def _normalized_header_name(value: Any) -> str:
    return re.sub(r"[\s\-]+", "_", str(value).strip().casefold())


def _alias_lookup() -> dict[str, str]:
    lookup = {}
    for canonical_name, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            lookup[_normalized_header_name(alias)] = canonical_name
    return lookup


def _load_row_values(row: ImportRowInput) -> list[Any]:
    payload = row.raw_data_json or row.raw_text
    if payload is None:
        raise CandidateGenerationError("Row has no raw JSON values.")

    values = json.loads(payload)
    if not isinstance(values, list):
        raise CandidateGenerationError("Row raw JSON must be a list.")
    return values


def _field_map_from_header(values: list[Any]) -> dict[str, int]:
    aliases = _alias_lookup()
    field_map = {}
    for index, value in enumerate(values):
        if value is None or str(value).strip() == "":
            continue

        canonical_name = aliases.get(_normalized_header_name(value))
        if canonical_name and canonical_name not in field_map:
            field_map[canonical_name] = index
    return field_map


def _cell(values: list[Any], field_map: dict[str, int], field_name: str) -> Any:
    index = field_map.get(field_name)
    if index is None or index >= len(values):
        return None

    value = values[index]
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0

    normalized = str(value).strip().casefold()
    return normalized in {"1", "true", "yes", "y", "all_day", "all day", "x"}


def _parse_date(value: Any, field_name: str) -> date:
    if value is None:
        raise CandidateGenerationError(f"{field_name} is required.")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    try:
        if "T" in text or " " in text:
            return datetime.fromisoformat(text).date()
        return date.fromisoformat(text)
    except ValueError as error:
        raise CandidateGenerationError(f"{field_name} must be an ISO date.") from error


def _parse_time(value: Any, field_name: str) -> time:
    if value is None:
        raise CandidateGenerationError(f"{field_name} is required.")
    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    if isinstance(value, int | float):
        if 0 <= value < 1:
            total_seconds = round(value * 24 * 60 * 60)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return time(hours % 24, minutes, seconds)
        if 0 <= value < 24 and float(value).is_integer():
            return time(int(value), 0)

    text = str(value).strip()
    try:
        if "T" in text or " " in text:
            return datetime.fromisoformat(text).time().replace(tzinfo=None)
        return time.fromisoformat(text).replace(tzinfo=None)
    except ValueError as error:
        raise CandidateGenerationError(f"{field_name} must be an ISO time.") from error


def _category_id(value: Any, categories_by_name: dict[str, int]) -> int | None:
    category_name = _text(value)
    if category_name is None:
        return None
    return categories_by_name.get(category_name.casefold())


def _build_candidate(
    row: ImportRowInput,
    values: list[Any],
    field_map: dict[str, int],
    categories_by_name: dict[str, int],
) -> CandidateDraft:
    title = _text(_cell(values, field_map, "title"))
    if title is None:
        raise CandidateGenerationError("title is required.")

    start_date = _parse_date(_cell(values, field_map, "date"), "date")
    start_time_value = _cell(values, field_map, "start_time")
    end_time_value = _cell(values, field_map, "end_time")
    timezone_name = _text(_cell(values, field_map, "timezone_name")) or DEFAULT_TIMEZONE
    is_all_day = _parse_bool(_cell(values, field_map, "all_day"))
    has_start_time = start_time_value is not None
    has_end_time = end_time_value is not None

    if is_all_day or (not has_start_time and not has_end_time):
        inclusive_last_day = _parse_date(
            _cell(values, field_map, "end_date"),
            "end_date",
        ) if _cell(values, field_map, "end_date") is not None else start_date
        exclusive_end_date = inclusive_last_day + timedelta(days=1)
        if exclusive_end_date <= start_date:
            raise CandidateGenerationError("end_date must be on or after date.")

        return CandidateDraft(
            import_row_id=row.id,
            source_row_index=row.row_index,
            title=title,
            description=_text(_cell(values, field_map, "description")),
            all_day=True,
            start_datetime=None,
            end_datetime=None,
            start_date=start_date,
            end_date=exclusive_end_date,
            timezone_name=None,
            location=_text(_cell(values, field_map, "location")),
            category_id=_category_id(_cell(values, field_map, "category"), categories_by_name),
        )

    start_time = _parse_time(start_time_value, "start_time")
    end_time = _parse_time(end_time_value, "end_time")
    end_date = (
        _parse_date(_cell(values, field_map, "end_date"), "end_date")
        if _cell(values, field_map, "end_date") is not None
        else start_date
    )

    try:
        start_datetime = normalize_timed_datetime(
            datetime.combine(start_date, start_time),
            timezone_name,
        )
        end_datetime = normalize_timed_datetime(
            datetime.combine(end_date, end_time),
            timezone_name,
        )
    except TimeSemanticsError as error:
        raise CandidateGenerationError(str(error)) from error

    if end_datetime <= start_datetime:
        raise CandidateGenerationError("end_datetime must be later than start_datetime.")

    return CandidateDraft(
        import_row_id=row.id,
        source_row_index=row.row_index,
        title=title,
        description=_text(_cell(values, field_map, "description")),
        all_day=False,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        start_date=None,
        end_date=None,
        timezone_name=timezone_name,
        location=_text(_cell(values, field_map, "location")),
        category_id=_category_id(_cell(values, field_map, "category"), categories_by_name),
    )


def generate_candidate_drafts(
    rows: list[ImportRowInput],
    categories_by_name: dict[str, int],
) -> CandidateGenerationResult:
    if not rows:
        raise CandidateGenerationError("Batch has no extracted rows.")

    header_row = rows[0]
    header_values = _load_row_values(header_row)
    field_map = _field_map_from_header(header_values)
    if "title" not in field_map or "date" not in field_map:
        raise CandidateGenerationError("Header row must include title and date columns.")

    candidates = []
    row_issues = [
        RowIssue(
            import_row_id=header_row.id,
            row_index=header_row.row_index,
            status="skipped",
            message="Header row skipped during candidate generation.",
        )
    ]

    for row in rows[1:]:
        try:
            values = _load_row_values(row)
            candidates.append(
                _build_candidate(row, values, field_map, categories_by_name)
            )
        except (CandidateGenerationError, TypeError, ValueError, json.JSONDecodeError) as error:
            row_issues.append(
                RowIssue(
                    import_row_id=row.id,
                    row_index=row.row_index,
                    status="failed",
                    message=str(error),
                )
            )

    return CandidateGenerationResult(
        header_row_id=header_row.id,
        header_row_index=header_row.row_index,
        rows_inspected=max(len(rows) - 1, 0),
        candidates=candidates,
        row_issues=row_issues,
    )
