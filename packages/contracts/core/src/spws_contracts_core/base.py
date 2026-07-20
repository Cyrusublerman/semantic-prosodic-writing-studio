from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Base configuration for durable contract records.

    Strict Python validation is intentional. JSON wire parsing remains available through
    ``model_validate_json`` for UUID, datetime and other JSON-native representations.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        validate_default=True,
        allow_inf_nan=False,
        use_enum_values=False,
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )
