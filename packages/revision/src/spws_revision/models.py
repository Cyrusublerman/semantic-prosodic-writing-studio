from __future__ import annotations

from pydantic import Field

from spws_contracts_core.base import ContractModel


class RevisionCandidate(ContractModel):
    candidate_id: str
    line_index: int = Field(ge=0)
    kind: str
    original_line: str
    revised_line: str
    rationale: str
