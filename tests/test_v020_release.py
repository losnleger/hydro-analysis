import importlib
import json
from pathlib import Path
import sys

import pytest


SCRIPTS_PATH = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_PATH))


def test_all_distributed_runtime_modules_import():
    modules = sorted(path.stem for path in SCRIPTS_PATH.glob("*.pyc"))
    assert len(modules) == 19
    for module_name in modules:
        importlib.import_module(module_name)


def test_unknown_legacy_parameters_fail_closed():
    hydro = importlib.import_module("scs_unit_hydrograph")
    common = {"rainfall": [50], "A": 1, "CN": 70, "tc": 60}
    with pytest.raises(ValueError, match="tcc"):
        hydro.analyze_flood_hydrograph(**common, tcc=60)
    with pytest.raises(ValueError, match="unit_duratin_h"):
        hydro.analyze_flood_hydrograph(**common, unit_duratin_h=0.1)


def test_string_boolean_is_rejected():
    hydro = importlib.import_module("scs_unit_hydrograph")
    with pytest.raises(ValueError, match="allow_kirpich_extrapolation"):
        hydro.analyze_flood_hydrograph(
            rainfall=[50],
            A=1,
            CN=70,
            tc=60,
            allow_kirpich_extrapolation="False",
        )


def test_result_json_is_strict_and_contains_agent_report_fields():
    hydro = importlib.import_module("scs_unit_hydrograph")
    result = hydro.analyze_flood_hydrograph(
        rainfall=[20, 50, 10],
        A=1,
        CN=70,
        tc=60,
    )

    def reject_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    roundtrip = json.loads(
        hydro.result_to_json(result),
        parse_constant=reject_constant,
    )
    required = {
        "S_mm",
        "Ia_mm",
        "total_rainfall_depth_mm",
        "total_excess_depth_mm",
        "event_runoff_coefficient",
        "recession_duration_h",
        "cn_provenance",
    }
    assert required <= roundtrip.keys()
