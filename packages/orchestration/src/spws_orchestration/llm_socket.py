"""LLM method-family socket: fail closed until explicitly enabled."""

from __future__ import annotations

import os


class LLMMethodFamilyDisabled(RuntimeError):
    """Raised when an LLM method family is requested without SPWS_ALLOW_LLM=1."""


def assert_method_family_allowed(method_family: str | None) -> None:
    """Refuse ``llm_bounded`` / ``llm_*`` families unless ``SPWS_ALLOW_LLM=1``.

    Deterministic and retrieval families are always allowed.
    """
    if method_family is None:
        return
    family = str(method_family).strip()
    if not family:
        return
    if family == "llm_bounded" or family.startswith("llm_"):
        if os.environ.get("SPWS_ALLOW_LLM", "").strip() == "1":
            return
        raise LLMMethodFamilyDisabled(
            f"method_family={family!r} requires SPWS_ALLOW_LLM=1 "
            "(LLM socket is fail-closed until enabled)"
        )
