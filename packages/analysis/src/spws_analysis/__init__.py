from __future__ import annotations

from spws_contracts_core import PKLResult

from .diagnosis import RevisionDiagnosis, diagnose_poem
from .models import LineAnnotation, PoetryAnalysisResult
from .poetry import analyze_poem
from .suite import analyse_document

__all__ = [
    "LineAnnotation",
    "PoetryAnalysisResult",
    "RevisionDiagnosis",
    "analyze_poem",
    "analyse_document",
    "diagnose_poem",
    "PKLResult",
]
