from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category, Event
from app.schemas import EventCreate, EventRead, EventUpdate
from app.time_utils import (
    DEFAULT_TIMEZONE,
    TimeSemanticsError,
    aware_to_utc,
    get_timezone,
    local_date_boundary_to_utc,
    utc_to_timezone,
)

router = APIRouter(prefix="/events", tags=["events"])


def _validation_error(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _normalized_instant(value: datetime, parameter_name: str) -> datetime:
    try:
        return aware_to_utc(value)
    except TimeSemanticsError as error:
        raise _validation_error(f"{parameter_name}: {error}") from error


def _event_payload(event: Event) -> dict:
    return {
        "title": event.title,
        "description": event.description,
        "all_day": event.all_day,
        "start_datetime": event.start_datetime,
        "end_datetime": event.end_datetime,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "timezone_name": event.timezone_name,
        "location": event.location,
        "category_id": event.category_id,
        "source_type": event.source_type,
        "status": event.status,
    }


def _merge_event_update(event: Event, data: dict) -> EventCreate:
    merged = _event_payload(event)

    if "all_day" in data and data["all_day"] != event.all_day:
        if data["all_day"]:
            merged.update(
                {
                    "start_datetime": None,
                    "end_datetime": None,
                    "timezone_name": None,
                }
            )
        else:
            merged.update({"start_date": None, "end_date": None})

    merged.update(data)
    try:
        return EventCreate.model_validate(merged)
    except ValidationError as error:
        messages = "; ".join(item["msg"] for item in error.errors())
        raise _validation_error(messages) from error


def _validate_category(category_id: int | None, db: Session) -> None:
    if category_id is None:
        return
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="category_id does not exist.")


def _local_date_from_instant(value: datetime, timezone_name: str) -> date:
    return utc_to_timezone(value, timezone_name).date()


def _exclusive_local_date_from_instant(value: datetime, timezone_name: str) -> date:
    local_value = utc_to_timezone(value, timezone_name)
    if local_value.timetz().replace(tzinfo=None) == time.min:
        return local_value.date()
    return local_value.date() + timedelta(days=1)


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    _validate_category(payload.category_id, db)

    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=list[EventRead])
def list_events(
    start_from: datetime | None = Query(default=None),
    end_to: datetime | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    timezone_name: str = Query(default=DEFAULT_TIMEZONE),
    category_id: int | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    try:
        get_timezone(timezone_name)
    except TimeSemanticsError as error:
        raise _validation_error(str(error)) from error

    normalized_start = (
        _normalized_instant(start_from, "start_from") if start_from is not None else None
    )
    normalized_end = _normalized_instant(end_to, "end_to") if end_to is not None else None

    if normalized_start is not None and normalized_end is not None:
        if normalized_end <= normalized_start:
            raise _validation_error("end_to must be later than start_from.")
    if date_from is not None and date_to is not None and date_to <= date_from:
        raise _validation_error("date_to must be later than date_from.")

    timed_start = normalized_start
    timed_end = normalized_end
    if timed_start is None and date_from is not None:
        timed_start = local_date_boundary_to_utc(date_from, timezone_name)
    if timed_end is None and date_to is not None:
        timed_end = local_date_boundary_to_utc(date_to, timezone_name)

    all_day_start = date_from
    all_day_end = date_to
    if all_day_start is None and normalized_start is not None:
        all_day_start = _local_date_from_instant(normalized_start, timezone_name)
    if all_day_end is None and normalized_end is not None:
        all_day_end = _exclusive_local_date_from_instant(normalized_end, timezone_name)

    timed_conditions = [Event.all_day.is_(False)]
    if timed_start is not None:
        timed_conditions.append(Event.end_datetime > timed_start)
    if timed_end is not None:
        timed_conditions.append(Event.start_datetime < timed_end)

    all_day_conditions = [Event.all_day.is_(True)]
    if all_day_start is not None:
        all_day_conditions.append(Event.end_date > all_day_start)
    if all_day_end is not None:
        all_day_conditions.append(Event.start_date < all_day_end)

    query = db.query(Event).filter(
        or_(and_(*timed_conditions), and_(*all_day_conditions))
    )
    if category_id is not None:
        query = query.filter(Event.category_id == category_id)

    sort_date = func.coalesce(func.date(Event.start_datetime), Event.start_date)
    query = query.order_by(sort_date.asc(), Event.all_day.asc(), Event.id.asc())

    if limit is not None:
        query = query.limit(limit)

    return query.all()


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event


@router.put("/{event_id}", response_model=EventRead)
def update_event(event_id: int, payload: EventUpdate, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    normalized_payload = _merge_event_update(event, payload.model_dump(exclude_unset=True))
    _validate_category(normalized_payload.category_id, db)

    for key, value in normalized_payload.model_dump().items():
        setattr(event, key, value)

    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    db.delete(event)
    db.commit()
