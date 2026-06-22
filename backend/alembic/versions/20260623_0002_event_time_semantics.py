"""Add explicit timed and all-day event semantics.

Revision ID: 20260623_0002
Revises: 20260619_0001
Create Date: 2026-06-23 00:00:00
"""
from datetime import UTC, date, datetime, time, timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.time_utils import DEFAULT_TIMEZONE, TimeSemanticsError, local_naive_to_utc, utc_to_timezone


revision: str = "20260623_0002"
down_revision: Union[str, Sequence[str], None] = "20260619_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _as_datetime(value: datetime | str | None, event_id: int) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise RuntimeError(f"Event {event_id} has an invalid datetime value.") from error
    raise RuntimeError(f"Event {event_id} has a missing datetime value.")


def _upgrade_existing_events() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, all_day, start_datetime, end_datetime FROM events ORDER BY id"
        )
    ).mappings()

    for row in rows:
        event_id = row["id"]
        start = _as_datetime(row["start_datetime"], event_id)
        end = _as_datetime(row["end_datetime"], event_id)

        if row["all_day"]:
            bind.execute(
                sa.text(
                    """
                    UPDATE events
                    SET start_datetime = NULL,
                        end_datetime = NULL,
                        start_date = :start_date,
                        end_date = :end_date,
                        timezone_name = NULL
                    WHERE id = :event_id
                    """
                ),
                {
                    "event_id": event_id,
                    "start_date": start.date(),
                    "end_date": end.date() + timedelta(days=1),
                },
            )
            continue

        try:
            start_utc = local_naive_to_utc(start.replace(tzinfo=None), DEFAULT_TIMEZONE)
            end_utc = local_naive_to_utc(end.replace(tzinfo=None), DEFAULT_TIMEZONE)
        except TimeSemanticsError as error:
            raise RuntimeError(f"Event {event_id} cannot be migrated: {error}") from error

        bind.execute(
            sa.text(
                """
                UPDATE events
                SET start_datetime = :start_datetime,
                    end_datetime = :end_datetime,
                    start_date = NULL,
                    end_date = NULL,
                    timezone_name = :timezone_name
                WHERE id = :event_id
                """
            ),
            {
                "event_id": event_id,
                "start_datetime": start_utc.replace(tzinfo=None),
                "end_datetime": end_utc.replace(tzinfo=None),
                "timezone_name": DEFAULT_TIMEZONE,
            },
        )


def _downgrade_existing_events() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, all_day, start_datetime, end_datetime, start_date, end_date,
                   timezone_name
            FROM events
            ORDER BY id
            """
        )
    ).mappings()

    for row in rows:
        event_id = row["id"]
        if row["all_day"]:
            start_date = date.fromisoformat(str(row["start_date"]))
            end_date = date.fromisoformat(str(row["end_date"]))
            bind.execute(
                sa.text(
                    """
                    UPDATE events
                    SET start_datetime = :start_datetime,
                        end_datetime = :end_datetime
                    WHERE id = :event_id
                    """
                ),
                {
                    "event_id": event_id,
                    "start_datetime": datetime.combine(start_date, time.min),
                    "end_datetime": datetime.combine(
                        end_date - timedelta(days=1), time(23, 59, 59)
                    ),
                },
            )
            continue

        start_utc = _as_datetime(row["start_datetime"], event_id).replace(tzinfo=UTC)
        end_utc = _as_datetime(row["end_datetime"], event_id).replace(tzinfo=UTC)
        timezone_name = row["timezone_name"]
        if not timezone_name:
            raise RuntimeError(f"Event {event_id} has no timezone for downgrade.")

        bind.execute(
            sa.text(
                """
                UPDATE events
                SET start_datetime = :start_datetime,
                    end_datetime = :end_datetime
                WHERE id = :event_id
                """
            ),
            {
                "event_id": event_id,
                "start_datetime": utc_to_timezone(start_utc, timezone_name).replace(tzinfo=None),
                "end_datetime": utc_to_timezone(end_utc, timezone_name).replace(tzinfo=None),
            },
        )


def upgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.alter_column(
            "start_datetime",
            existing_type=sa.DateTime(timezone=False),
            nullable=True,
        )
        batch_op.alter_column(
            "end_datetime",
            existing_type=sa.DateTime(timezone=False),
            nullable=True,
        )
        batch_op.add_column(sa.Column("start_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("end_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("timezone_name", sa.String(length=64), nullable=True))

    _upgrade_existing_events()

    with op.batch_alter_table("events") as batch_op:
        batch_op.create_check_constraint(
            "ck_events_timed_shape",
            "all_day = 1 OR (start_datetime IS NOT NULL AND end_datetime IS NOT NULL "
            "AND timezone_name IS NOT NULL AND start_date IS NULL AND end_date IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_events_all_day_shape",
            "all_day = 0 OR (start_date IS NOT NULL AND end_date IS NOT NULL "
            "AND start_datetime IS NULL AND end_datetime IS NULL AND timezone_name IS NULL)",
        )
        batch_op.create_check_constraint(
            "ck_events_timed_order",
            "all_day = 1 OR end_datetime > start_datetime",
        )
        batch_op.create_check_constraint(
            "ck_events_all_day_order",
            "all_day = 0 OR end_date > start_date",
        )


def downgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_constraint("ck_events_all_day_order", type_="check")
        batch_op.drop_constraint("ck_events_timed_order", type_="check")
        batch_op.drop_constraint("ck_events_all_day_shape", type_="check")
        batch_op.drop_constraint("ck_events_timed_shape", type_="check")

    _downgrade_existing_events()

    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_column("timezone_name")
        batch_op.drop_column("end_date")
        batch_op.drop_column("start_date")
        batch_op.alter_column(
            "end_datetime",
            existing_type=sa.DateTime(timezone=False),
            nullable=False,
        )
        batch_op.alter_column(
            "start_datetime",
            existing_type=sa.DateTime(timezone=False),
            nullable=False,
        )
