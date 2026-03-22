from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category, Event
from app.schemas import EventCreate, EventRead, EventUpdate

router = APIRouter(prefix="/events", tags=["events"])


def validate_event_times(start_datetime: datetime, end_datetime: datetime) -> None:
    if end_datetime <= start_datetime:
        raise HTTPException(
            status_code=400,
            detail="end_datetime must be later than start_datetime.",
        )


@router.post("/", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    validate_event_times(payload.start_datetime, payload.end_datetime)

    if payload.category_id is not None:
        category = db.query(Category).filter(Category.id == payload.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="category_id does not exist.")

    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/", response_model=list[EventRead])
def list_events(
    start_from: datetime | None = Query(default=None),
    end_to: datetime | None = Query(default=None),
    category_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Event)

    if start_from is not None:
        query = query.filter(Event.start_datetime >= start_from)

    if end_to is not None:
        query = query.filter(Event.end_datetime <= end_to)

    if category_id is not None:
        query = query.filter(Event.category_id == category_id)

    return query.order_by(Event.start_datetime.asc()).all()


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

    data = payload.model_dump(exclude_unset=True)

    new_start = data.get("start_datetime", event.start_datetime)
    new_end = data.get("end_datetime", event.end_datetime)
    validate_event_times(new_start, new_end)

    if "category_id" in data and data["category_id"] is not None:
        category = db.query(Category).filter(Category.id == data["category_id"]).first()
        if not category:
            raise HTTPException(status_code=400, detail="category_id does not exist.")

    for key, value in data.items():
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