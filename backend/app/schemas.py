from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class EventBase(BaseModel):
    title: str
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime
    all_day: bool = False
    location: str | None = None
    category_id: int | None = None
    source_type: str = "manual"
    status: str = "active"


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    category_id: int | None = None
    source_type: str | None = None
    status: str | None = None


class EventRead(EventBase):
    id: int

    model_config = ConfigDict(from_attributes=True)