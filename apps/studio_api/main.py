"""Re-export studio API app from hyphenated directory implementation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_IMPL = Path(__file__).resolve().parent.parent / "studio-api" / "main.py"
_NAME = "spws_studio_api_impl"
_spec = importlib.util.spec_from_file_location(_NAME, _IMPL)
_mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_NAME] = _mod
_spec.loader.exec_module(_mod)
for _attr in vars(_mod).values():
    if isinstance(_attr, type) and hasattr(_attr, "model_rebuild"):
        try:
            _attr.model_rebuild()
        except Exception:
            pass
app = _mod.app
create_app = _mod.create_app
