from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, Field, field_serializer, model_validator
from typing_extensions import TypeAliasType

from .base import ContractModel


def _normalise_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


UtcDateTime = TypeAliasType(
    "UtcDateTime",
    Annotated[
        datetime,
        AfterValidator(_normalise_utc),
        Field(json_schema_extra={"format": "date-time", "x-spws-timezone": "UTC"}),
    ],
)


def format_rfc3339_utc(value: datetime) -> str:
    value = _normalise_utc(value)
    text = value.isoformat(timespec="microseconds")
    if text.endswith("+00:00"):
        text = text[:-6] + "Z"
    return text


class TimeWindow(ContractModel):
    start: UtcDateTime | None = None
    end: UtcDateTime | None = None

    @model_validator(mode="after")
    def validate_order(self) -> "TimeWindow":
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("time-window end must not precede start")
        return self

    @field_serializer("start", "end", when_used="json")
    def serialise_time(self, value: datetime | None) -> str | None:
        return None if value is None else format_rfc3339_utc(value)

    def contains(self, instant: datetime) -> bool:
        instant = _normalise_utc(instant)
        return (self.start is None or instant >= self.start) and (
            self.end is None or instant <= self.end
        )
