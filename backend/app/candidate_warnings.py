from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models import CandidateEvent, Event
from app.time_utils import DEFAULT_TIMEZONE, utc_to_timezone


@dataclass(frozen=True)
class CandidateWarning:
    type: str
    message: str
    event_id: int
    event_title: str
    event_start: str
    event_end: str


def warnings_for_candidates(
    candidates: list[CandidateEvent],
    db: Session,
) -> dict[int, list[CandidateWarning]]:
    if not candidates:
        return {}

    active_events = (
        db.query(Event)
        .filter(Event.status == "active")
        .all()
    )

    return {
        candidate.id: [
            warning
            for event in active_events
            if (warning := _warning_for_event(candidate, event)) is not None
        ]
        for candidate in candidates
    }


def _warning_for_event(
    candidate: CandidateEvent,
    event: Event,
) -> CandidateWarning | None:
    if event.candidate_event_id == candidate.id:
        return None

    if not _overlaps(candidate, event):
        return None

    if _is_duplicate(candidate, event):
        return CandidateWarning(
            type="duplicate",
            message=f"Likely duplicate of active event #{event.id}.",
            event_id=event.id,
            event_title=event.title,
            event_start=_event_start(event),
            event_end=_event_end(event),
        )

    return CandidateWarning(
        type="conflict",
        message=f"Overlaps active event #{event.id}.",
        event_id=event.id,
        event_title=event.title,
        event_start=_event_start(event),
        event_end=_event_end(event),
    )


def _is_duplicate(candidate: CandidateEvent, event: Event) -> bool:
    if candidate.all_day != event.all_day:
        return False
    if _normalized_title(candidate.title) != _normalized_title(event.title):
        return False
    if (
        candidate.category_id is not None
        and event.category_id is not None
        and candidate.category_id != event.category_id
    ):
        return False
    return True


def _normalized_title(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _overlaps(candidate: CandidateEvent, event: Event) -> bool:
    if not candidate.all_day and not event.all_day:
        return _half_open_overlaps(
            candidate.start_datetime,
            candidate.end_datetime,
            event.start_datetime,
            event.end_datetime,
        )

    if candidate.all_day and event.all_day:
        return _half_open_overlaps(
            candidate.start_date,
            candidate.end_date,
            event.start_date,
            event.end_date,
        )

    if candidate.all_day:
        event_start, event_end = _timed_local_date_interval(
            event.start_datetime,
            event.end_datetime,
            event.timezone_name,
        )
        return _half_open_overlaps(
            candidate.start_date,
            candidate.end_date,
            event_start,
            event_end,
        )

    candidate_start, candidate_end = _timed_local_date_interval(
        candidate.start_datetime,
        candidate.end_datetime,
        candidate.timezone_name,
    )
    return _half_open_overlaps(
        candidate_start,
        candidate_end,
        event.start_date,
        event.end_date,
    )


def _half_open_overlaps(
    start: date | datetime | None,
    end: date | datetime | None,
    other_start: date | datetime | None,
    other_end: date | datetime | None,
) -> bool:
    if start is None or end is None or other_start is None or other_end is None:
        return False
    return end > other_start and start < other_end


def _timed_local_date_interval(
    start_datetime: datetime | None,
    end_datetime: datetime | None,
    timezone_name: str | None,
) -> tuple[date, date]:
    timezone_name = timezone_name or DEFAULT_TIMEZONE
    return (
        _local_date_from_instant(start_datetime, timezone_name),
        _exclusive_local_date_from_instant(end_datetime, timezone_name),
    )


def _local_date_from_instant(value: datetime | None, timezone_name: str) -> date:
    if value is None:
        raise ValueError("Timed interval is missing a start datetime.")
    return utc_to_timezone(value, timezone_name).date()


def _exclusive_local_date_from_instant(
    value: datetime | None,
    timezone_name: str,
) -> date:
    if value is None:
        raise ValueError("Timed interval is missing an end datetime.")
    local_value = utc_to_timezone(value, timezone_name)
    if local_value.timetz().replace(tzinfo=None) == time.min:
        return local_value.date()
    return local_value.date() + timedelta(days=1)


def _event_start(event: Event) -> str:
    if event.all_day:
        return event.start_date.isoformat()
    return _utc_string(event.start_datetime)


def _event_end(event: Event) -> str:
    if event.all_day:
        return event.end_date.isoformat()
    return _utc_string(event.end_datetime)


def _utc_string(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
