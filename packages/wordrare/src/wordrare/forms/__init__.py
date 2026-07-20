"""
Forms module for poetic form engines.
"""

from .form_library import FormLibrary, FormSpec, StanzaSpec
from .sound_engine import SoundEngine, RhymeMatch
from .meter_engine import MeterEngine, MeterPattern, LineAnalysis, METER_PATTERNS
from .grammar_engine import GrammarEngine, SyntacticTemplate, POSSlot, TEMPLATES

__all__ = [
    "FormLibrary",
    "FormSpec",
    "StanzaSpec",
    "SoundEngine",
    "RhymeMatch",
    "MeterEngine",
    "MeterPattern",
    "LineAnalysis",
    "METER_PATTERNS",
    "GrammarEngine",
    "SyntacticTemplate",
    "POSSlot",
    "TEMPLATES"
]
