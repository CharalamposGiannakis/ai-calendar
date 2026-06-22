from datetime import UTC, datetime

import pytest

from app.time_utils import TimeSemanticsError, local_naive_to_utc


def test_normal_amsterdam_winter_time_converts_to_utc():
    result = local_naive_to_utc(datetime(2026, 1, 15, 9, 0), "Europe/Amsterdam")

    assert result == datetime(2026, 1, 15, 8, 0, tzinfo=UTC)


def test_normal_amsterdam_summer_time_converts_to_utc():
    result = local_naive_to_utc(datetime(2026, 7, 15, 9, 0), "Europe/Amsterdam")

    assert result == datetime(2026, 7, 15, 7, 0, tzinfo=UTC)


def test_nonexistent_amsterdam_spring_time_is_rejected():
    with pytest.raises(TimeSemanticsError, match="does not exist"):
        local_naive_to_utc(datetime(2026, 3, 29, 2, 30), "Europe/Amsterdam")


def test_ambiguous_amsterdam_autumn_time_is_rejected():
    with pytest.raises(TimeSemanticsError, match="ambiguous"):
        local_naive_to_utc(datetime(2026, 10, 25, 2, 30), "Europe/Amsterdam")


def test_invalid_timezone_is_rejected():
    with pytest.raises(TimeSemanticsError, match="valid IANA"):
        local_naive_to_utc(datetime(2026, 1, 15, 9, 0), "Invalid/Zone")
