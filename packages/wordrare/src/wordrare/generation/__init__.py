"""
Generation module for poem creation.
"""

from .annotator import PoemAnnotator
from .engine import GeneratedPoem, PoemGenerator
from .generation_spec import GenerationSpec, create_default_spec
from .line_realizer import LineRealizer, WordSelector
from .prose_rewrite import ProseRewriter
from .scaffolding import LineScaffold, PoemScaffold, Scaffolder
from .theme_selector import ThemeSelector

__all__ = [
    "GenerationSpec",
    "create_default_spec",
    "ThemeSelector",
    "Scaffolder",
    "PoemScaffold",
    "LineScaffold",
    "LineRealizer",
    "WordSelector",
    "PoemGenerator",
    "GeneratedPoem",
    "PoemAnnotator",
    "ProseRewriter",
]
