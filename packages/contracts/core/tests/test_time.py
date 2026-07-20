from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from spws_contracts_core.time import TimeWindow, UtcDateTime, format_rfc3339_utc


def test_utc_datetime_normalises_offset():
    adapter = TypeAdapter(UtcDateTime)
    value = adapter.validate_python(datetime(2026, 7, 17, 10, tzinfo=timezone(timedelta(hours=10))))
    assert value == datetime(2026, 7, 17, 0, tzinfo=UTC)
    assert format_rfc3339_utc(value).endswith("Z")


def test_utc_datetime_rejects_naive():
    with pytest.raises(ValidationError):
        TypeAdapter(UtcDateTime).validate_python(datetime(2026, 7, 17))


def test_time_window_order_and_contains(now):
    window = TimeWindow(start=now, end=now + timedelta(hours=1))
    assert window.contains(now + timedelta(minutes=30))
    assert not window.contains(now - timedelta(seconds=1))
    with pytest.raises(ValidationError):
        TimeWindow(start=now, end=now - timedelta(seconds=1))
