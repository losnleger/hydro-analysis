#!/usr/bin/env python3
"""Load one ABI-matched native sibling for the public command shims."""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import re
import sys


_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_native_module(module_name, caller_file):
    if not isinstance(module_name, str) or not _MODULE.fullmatch(module_name):
        raise ImportError(f"invalid native module name: {module_name!r}")
    directory = Path(caller_file).resolve().parent
    matches = list(dict.fromkeys(
        (directory / f"{module_name}{suffix}").resolve()
        for suffix in importlib.machinery.EXTENSION_SUFFIXES
        if (directory / f"{module_name}{suffix}").is_file()
    ))
    if len(matches) != 1:
        raise ImportError(
            f"expected one ABI-compatible native module {module_name!r}, got {matches}"
        )
    selected = matches[0]
    existing = sys.modules.get(module_name)
    if existing is not None:
        origin = getattr(existing, "__file__", None)
        if origin is None or Path(origin).resolve() != selected:
            raise ImportError(f"module name {module_name!r} is occupied by {origin!r}")
        return existing
    spec = importlib.util.spec_from_file_location(module_name, selected)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create native module spec for {selected}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if sys.modules.get(module_name) is module:
            del sys.modules[module_name]
        raise
    return module
