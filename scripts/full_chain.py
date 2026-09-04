#!/usr/bin/env python3
"""Command entry point for hydro-analysis."""

from __future__ import annotations

import importlib.util as _importlib_util
from pathlib import Path as _Path
import sys as _sys


_entry_path = _Path(__file__).with_name("_native_entry.py")
_entry_spec = _importlib_util.spec_from_file_location("_hydro_native_entry", _entry_path)
if _entry_spec is None or _entry_spec.loader is None:
    raise ImportError(f"cannot load native entry helper: {_entry_path}")
_entry = _importlib_util.module_from_spec(_entry_spec)
_sys.modules.setdefault("_hydro_native_entry", _entry)
_entry_spec.loader.exec_module(_entry)
_entry.load_native_module("runtime_loader", __file__)
_implementation = _entry.load_native_module("_hydro_full_chain", __file__)

for _name in dir(_implementation):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_implementation, _name)

if __name__ == "__main__":
    raise SystemExit(_implementation.main())
