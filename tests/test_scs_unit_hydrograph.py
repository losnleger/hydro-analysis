import importlib.util
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "scs_unit_hydrograph.py"
SPEC = importlib.util.spec_from_file_location("scs_unit_hydrograph", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_unit_hydrograph_is_finite_and_normalized():
    unit_hydrograph = MODULE.generate_unit_hydrograph(
        tp=1.0, dt=0.133, duration=4.0
    )

    assert np.all(np.isfinite(unit_hydrograph))
    assert np.isclose(np.sum(unit_hydrograph), 1.0)


def test_reference_example_runs_without_nan():
    rainfall = [2, 5, 8, 15, 20, 18, 12, 8, 5, 3, 2, 1, 0.5, 0.5, 0, 0]
    result = MODULE.analyze_flood_hydrograph(
        rainfall=rainfall, runoff_coeff=0.25, A=32.5
    )

    assert np.all(np.isfinite(result["runoff"]))
    assert result["runoff"].shape == (len(rainfall),)
    assert result["peak_time"] == int(np.argmax(result["runoff"]))
    assert np.isclose(np.max(result["runoff"]), result["Qp"])
