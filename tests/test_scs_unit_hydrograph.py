import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


SCRIPTS_PATH = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_PATH))

MODULE_PATH = SCRIPTS_PATH / "scs_unit_hydrograph.pyc"
SPEC = importlib.util.spec_from_file_location("scs_unit_hydrograph", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

GENERATOR_PATH = SCRIPTS_PATH / "generate_chart.pyc"
GENERATOR_SPEC = importlib.util.spec_from_file_location("generate_chart", GENERATOR_PATH)
GENERATOR = importlib.util.module_from_spec(GENERATOR_SPEC)
assert GENERATOR_SPEC.loader is not None
GENERATOR_SPEC.loader.exec_module(GENERATOR)


# ---------------------------------------------------------------------------
# NRCS time relations and standard PRF=484 dimensionless unit hydrograph
# ---------------------------------------------------------------------------

def test_nrcs_484_unit_hydrograph_reproduces_table_16_1():
    """NEH 630 Ch.16 table 16-1 ordinates, sampled at Tp=1 h and dt=0.1 h."""
    uh = MODULE.generate_unit_hydrograph(tp=1.0, dt=0.1, duration=5.0)
    ratios = uh / np.max(uh)
    for time_ratio, expected_ratio in zip(
        MODULE.NRCS_484_TIME_RATIOS, MODULE.NRCS_484_DISCHARGE_RATIOS
    ):
        index = int(round(time_ratio / 0.1))
        assert ratios[index] == pytest.approx(expected_ratio, abs=1e-12)
    assert np.argmax(uh) == 10
    assert np.all(np.diff(uh[10:]) <= 1e-14)
    assert np.sum(uh) == pytest.approx(1.0)


def test_dimensional_unit_hydrograph_conserves_one_mm_and_matches_prf():
    area_km2 = 2.5
    dt_h = 0.1
    uh = MODULE.generate_unit_hydrograph(
        tp=1.0, dt=dt_h, duration=5.0, drainage_area_km2=area_km2
    )
    assert np.all(np.isfinite(uh))
    assert np.sum(uh) * dt_h * 3600.0 == pytest.approx(area_km2 * 1000.0)
    # Published table ordinates are rounded; their integrated peak differs from
    # the continuous PRF=484 conversion by about 0.2%.
    theoretical = MODULE.calculate_peak_flow(area_km2, 1.0, runoff_depth_mm=1.0)
    assert np.max(uh) == pytest.approx(theoretical, rel=0.003)


def test_unit_hydrograph_requires_complete_table_tail():
    with pytest.raises(ValueError, match="5×tp"):
        MODULE.generate_unit_hydrograph(tp=1.0, dt=0.1, duration=4.9)
    with pytest.raises(ValueError, match="0.1×tp"):
        MODULE.generate_unit_hydrograph(tp=1.0, dt=0.3, duration=5.0)


def test_nrcs_timing_relations_and_example_16_1_peak():
    # NEH 630 Ch.16 example 16-1: A=4.6 mi², Tc=2.3 h, ΔD≈0.3 h,
    # Tp≈1.53 h and qp≈1455 cfs for one inch of runoff.
    tc_min = 2.3 * 60.0
    assert MODULE.calculate_lag_time(tc_min) == pytest.approx(1.38)
    assert MODULE.calculate_unit_duration(tc_min) == pytest.approx(0.3059)
    tp_h = MODULE.calculate_time_to_peak(tc_min)
    assert tp_h == pytest.approx(1.53295)
    area_km2 = 4.6 * 2.589988110336
    peak_cfs = (
        MODULE.calculate_peak_flow(area_km2, 1.53, runoff_depth_mm=25.4)
        * 35.3146667215
    )
    assert peak_cfs == pytest.approx(1455.0, rel=0.01)


def test_tc_tp_and_optional_unit_duration_must_be_mutually_consistent():
    baseline = MODULE.analyze_flood_hydrograph(
        rainfall=[50], A=1, CN=70, tc=60
    )
    aligned_tp = baseline["tp"]
    assert baseline["unit_duration_target"] == pytest.approx(0.133)
    assert baseline["unit_duration"] == pytest.approx(0.125)
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[50], A=1, CN=70, tc=60, tp=aligned_tp
    )
    assert result["tp"] == pytest.approx(aligned_tp)
    with pytest.raises(ValueError, match="不一致"):
        MODULE.analyze_flood_hydrograph(
            rainfall=[50], A=1, CN=70, tc=60, tp=0.65
        )
    custom_duration = 0.125
    custom_tp = MODULE.calculate_lag_time(60) + custom_duration / 2
    result_custom = MODULE.analyze_flood_hydrograph(
        rainfall=[50],
        A=1,
        CN=70,
        tc=60,
        unit_duration_h=custom_duration,
        tp=custom_tp,
    )
    assert result_custom["unit_duration"] == pytest.approx(custom_duration)
    with pytest.raises(ValueError, match="unit_duration_h 必须精确整除"):
        MODULE.analyze_flood_hydrograph(
            rainfall=[50], A=1, CN=70, tc=60, unit_duration_h=0.12
        )


def test_kirpich_equation_requires_inputs_and_enforces_original_domain():
    area_km2 = 0.1
    length_km = 0.5
    slope = 0.02
    expected = (
        0.007
        * 3.280839895013123 ** 0.77
        * (length_km * 1000.0) ** 0.77
        * slope ** -0.385
    )
    assert MODULE.calculate_concentration_time(
        area_km2, L=length_km, slope=slope
    ) == pytest.approx(expected)
    with pytest.raises(ValueError, match="显式提供"):
        MODULE.calculate_concentration_time(area_km2)
    with pytest.raises(ValueError, match="1.25–112 acre"):
        MODULE.calculate_concentration_time(1.0, L=1.0, slope=0.02)
    assert MODULE.calculate_concentration_time(
        1.0, L=1.0, slope=0.02, allow_extrapolation=True
    ) > 0


def test_auxiliary_method_guards_and_legacy_convolution_slice():
    assert MODULE.calculate_net_rainfall([10, 20], 0.25) == [2.5, 5.0]
    with pytest.raises(ValueError):
        MODULE.calculate_net_rainfall([10, -1], 0.25)
    with pytest.raises(ValueError):
        MODULE.calculate_cn_from_runoff_coeff(0.4, method="unsupported")
    assert MODULE.calculate_concentration_time(4.0, method="area_estimate") == pytest.approx(36.0)
    with pytest.raises(ValueError, match="method"):
        MODULE.calculate_concentration_time(1.0, method="unsupported")
    with pytest.raises(ValueError, match="仅支持"):
        MODULE.calculate_lag_time(60, method="unsupported")
    full = MODULE.convolve_rainfall_runoff([1, 2], [0.25, 0.75], full_output=True)
    sliced = MODULE.convolve_rainfall_runoff([1, 2], [0.25, 0.75], full_output=False)
    assert np.allclose(sliced, full[:2])


# ---------------------------------------------------------------------------
# CN tables, AMC conversion, composite CN, and SCS-CN runoff
# ---------------------------------------------------------------------------

def test_hsg_metadata_uses_neh630_ksat_screening_not_legacy_infiltration():
    assert MODULE.HSG_DEFINITIONS["A"]["screening_ksat_um_s"] == (40.0, None)
    assert MODULE.HSG_DEFINITIONS["B"]["screening_ksat_um_s"] == (10.0, 40.0)
    assert MODULE.HSG_DEFINITIONS["C"]["screening_ksat_um_s"] == (1.0, 10.0)
    assert MODULE.HSG_DEFINITIONS["D"]["screening_ksat_um_s"] == (0.0, 1.0)


def test_select_cn_urban_values():
    assert MODULE.select_cn("商业区(85%不透水)", "A") == 89
    assert MODULE.select_cn("商业区(85%不透水)", "B") == 92
    assert MODULE.select_cn("居住区1/4英亩(38%不透水)", "B") == 75
    assert MODULE.select_cn("不透水面(屋顶/停车场)", "A", "impervious") == 98


def test_select_cn_cultivated_values():
    assert MODULE.select_cn("中耕作物", "B", "poor", "straight") == 81
    assert MODULE.select_cn("中耕作物", "D", "good", "terraced") == 81
    assert MODULE.select_cn("小粒谷物", "C", "good", "contoured") == 81
    assert MODULE.select_cn("密植豆科/轮作牧草", "A", "good", "straight") == 58


def test_select_cn_other_and_arid_values():
    assert MODULE.select_cn("林地", "B", "good") == 55
    assert MODULE.select_cn("牧场/草地/放牧地", "D", "poor") == 89
    assert MODULE.select_cn("荒漠灌木(盐灌木/木馏油等)", "D", "good") == 84
    assert MODULE.select_cn("草本植被(草/杂草/低灌丛)", "C", "good") == 85


def test_select_cn_rejects_missing_or_invalid_hsg_and_blanket_residue_rule():
    with pytest.raises(ValueError):
        MODULE.select_cn("草本植被(草/杂草/低灌丛)", "D", "good")
    with pytest.raises(ValueError, match="A/B/C/D"):
        MODULE.select_cn("林地", "E", "good")
    with pytest.raises(ValueError, match="不再使用统一 CN-2"):
        MODULE.select_cn("中耕作物", "B", "good", "straight", crop_residue=True)


def test_select_cn_aliases():
    assert MODULE.select_cn("旱地", "B", "差", "顺坡") == 81
    assert MODULE.select_cn("row crops", "B", "poor", "sr") == 81
    assert MODULE.select_cn("草地", "D", "差") == 89


def test_cn_tables_hsg_ordering():
    for table in (MODULE.CN_URBAN, MODULE.CN_OTHER_AGRICULTURAL):
        for land_use, conditions in table.items():
            for condition, values in conditions.items():
                assert all(a <= b for a, b in zip(values, values[1:])), (
                    land_use,
                    condition,
                    values,
                )


def test_adjust_cn_for_amc_matches_neh_formulas_and_validates_cn():
    assert MODULE.adjust_cn_for_amc(70, "I") == 49
    assert MODULE.adjust_cn_for_amc(70, "II") == 70
    assert MODULE.adjust_cn_for_amc(70, "III") == 84
    for cn in (40, 55, 70, 85, 95):
        assert (
            MODULE.adjust_cn_for_amc(cn, "I")
            < MODULE.adjust_cn_for_amc(cn, "II")
            < MODULE.adjust_cn_for_amc(cn, "III")
        )
    with pytest.raises(ValueError):
        MODULE.adjust_cn_for_amc(0, "II")


def test_composite_cn_area_weighted_and_rejects_nonphysical_segments():
    assert MODULE.composite_cn([(70, 3), (80, 1)]) == 72
    assert MODULE.composite_cn([(50, 0.5), (90, 0.5)]) == 70
    for segments in (
        [],
        [(0, 1)],
        [(101, 1)],
        [(70, -1), (80, 2)],
        [(70, np.nan)],
        [(np.inf, 1)],
    ):
        with pytest.raises(ValueError):
            MODULE.composite_cn(segments)


def test_composite_cn_urban_applies_neh630_30_percent_boundary():
    # Eq. 630E-2 for total impervious area <30%.
    assert MODULE.composite_cn_urban(61, 20, connected_ratio=0.25) == 65.6
    # At >=30%, eq. 630E-1 is used; unconnected adjustment is not credited.
    assert MODULE.composite_cn_urban(61, 30, connected_ratio=0.0) == 72.1
    with pytest.raises(ValueError):
        MODULE.composite_cn_urban(0, 20)
    with pytest.raises(ValueError):
        MODULE.composite_cn_urban(61, np.nan)


def test_cn_to_s_initial_abstraction_and_runoff_formula():
    s = MODULE.cn_to_s_mm(70)
    assert s == pytest.approx(25400.0 / 70.0 - 254.0)
    ia = MODULE.initial_abstraction_mm(70, lam=0.2)
    assert ia == pytest.approx(0.2 * s)
    assert MODULE.direct_runoff_mm(20, 70, lam=0.2) == 0.0
    assert MODULE.direct_runoff_mm(50, 70, lam=0.2) == pytest.approx(
        (50.0 - ia) ** 2 / (50.0 - ia + s)
    )
    for precipitation in (-1.0, np.nan, np.inf):
        with pytest.raises(ValueError):
            MODULE.direct_runoff_mm(precipitation, 70)
    for lam in (-0.1, 0.0, np.nan, 1.1, None):
        with pytest.raises(ValueError):
            MODULE.direct_runoff_mm(50, 70, lam=lam)


def test_region_values_are_advisory_and_alpine_is_unsupported():
    assert MODULE.initial_abstraction_ratio_for_region("湿润区") == 0.2
    assert MODULE.initial_abstraction_ratio_for_region("半干旱区") == 0.05
    assert MODULE.initial_abstraction_ratio_for_region("高寒区") is None
    with pytest.raises(ValueError, match="高寒区"):
        MODULE.analyze_flood_hydrograph(
            rainfall=[50], A=1, CN=70, tc=60, region="高寒区"
        )


# ---------------------------------------------------------------------------
# End-to-end rainfall-depth conversion, aligned time grid, and mass balance
# ---------------------------------------------------------------------------

def test_cn_mode_no_longer_requires_irrelevant_runoff_coefficient():
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[20, 50, 10], A=1.0, CN=70, tc=60.0
    )
    assert result["method"] == "scs_cn_direct"
    assert np.all(np.isfinite(result["runoff"]))
    assert result["runoff"].size > result["net_rainfall"].size


@pytest.mark.parametrize("dt_rain_h", [0.5, 1.0, 2.0])
def test_rainfall_intensity_is_converted_to_depth(dt_rain_h):
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[50.0], A=1.0, CN=70, tc=60.0, dt_rain_h=dt_rain_h
    )
    expected_depth = MODULE.direct_runoff_mm(50.0 * dt_rain_h, 70, lam=0.2)
    assert np.sum(result["rainfall_depth_mm"]) == pytest.approx(50.0 * dt_rain_h)
    assert np.allclose(
        result["rainfall_depth_unit_mm"],
        50.0 * result["unit_duration"],
    )
    expected_cumulative = np.array(
        [
            MODULE.direct_runoff_mm(depth, 70, lam=0.2)
            for depth in np.cumsum(result["rainfall_depth_unit_mm"])
        ]
    )
    expected_increments = np.diff(np.concatenate(([0.0], expected_cumulative)))
    assert np.allclose(result["net_rainfall"], expected_increments)
    assert np.sum(result["net_rainfall"]) == pytest.approx(expected_depth)
    assert result["total_volume"] == pytest.approx(expected_depth * 1000.0)


def test_default_grid_preserves_exact_rainfall_duration_and_mass():
    rainfall = [15.0, 40.0, 5.0]
    result = MODULE.analyze_flood_hydrograph(
        rainfall=rainfall, A=3.2, CN=75, tc=80.0, dt_rain_h=0.7
    )
    represented_duration = len(result["net_rainfall"]) * result["unit_duration"]
    assert represented_duration == pytest.approx(len(rainfall) * 0.7)
    assert result["runoff_volume"] == pytest.approx(result["total_volume"], rel=1e-12)
    assert result["mass_balance_relative_error"] <= 1e-12


def test_output_grid_must_divide_unit_duration():
    with pytest.raises(ValueError, match="unit_duration_h"):
        MODULE.analyze_flood_hydrograph(
            rainfall=[50, 20], A=1, CN=70, tc=180, dt_rain_h=1.0, dt=0.03
        )


def test_unit_excess_is_shifted_by_delta_d_not_every_output_step():
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[5, 10],
        runoff_coeff=1.0,
        A=1,
        tp=1.0,
        unit_duration_h=0.2,
        dt_rain_h=0.2,
        dt=0.1,
    )
    steps = result["model_steps_per_unit_period"]
    excess_grid = result["excess_depth_on_model_grid_mm"]
    assert steps == 2
    assert np.allclose(result["net_rainfall"], [1.0, 2.0])
    assert np.allclose(excess_grid, [1.0, 0.0, 2.0])
    assert np.allclose(excess_grid[::steps], result["net_rainfall"])
    assert np.all(excess_grid[1::steps] == 0.0)
    uh = MODULE.generate_unit_hydrograph(
        result["tp"], result["dt"], 5.0 * result["tp"], drainage_area_km2=1.0
    )
    expected = np.zeros(len(uh) + 2)
    expected[:len(uh)] += uh
    expected[2:] += 2.0 * uh
    assert np.allclose(result["runoff"], expected)
    assert result["time_reference"].startswith("interval-start")


@pytest.mark.parametrize(
    "bad_rainfall",
    [[], [-1.0, 2.0], [np.nan, 2.0], [np.inf], [[1.0, 2.0]]],
)
def test_analyze_rejects_invalid_rainfall(bad_rainfall):
    with pytest.raises(ValueError):
        MODULE.analyze_flood_hydrograph(
            rainfall=bad_rainfall, A=1.0, CN=70, tc=60.0
        )


def test_land_use_path_fails_closed_on_missing_metadata_and_runs_when_complete():
    with pytest.raises(ValueError, match="缺少必填参数"):
        MODULE.analyze_flood_hydrograph(
            rainfall=[30, 40], A=1, land_use="林地", tc=60
        )
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[30, 40],
        A=1,
        land_use="林地",
        hsg="B",
        hydrologic_condition="good",
        amc="II",
        tc=60,
    )
    direct = MODULE.analyze_flood_hydrograph(
        rainfall=[30, 40], A=1, CN=55, tc=60
    )
    assert result["CN"] == 55
    assert np.allclose(result["runoff"], direct["runoff"])


def test_nonstandard_lambda_is_explicit_and_region_does_not_override_default():
    standard = MODULE.analyze_flood_hydrograph(
        rainfall=[100], A=1, CN=70, tc=60, region="半干旱区"
    )
    assert standard["lambda"] == 0.2
    assert any("未自动套用" in note for note in standard["assumptions"])
    adapted = MODULE.analyze_flood_hydrograph(
        rainfall=[100], A=1, CN=70, tc=60, region="半干旱区", lam=0.05
    )
    assert adapted["lambda"] == 0.05
    assert any("联合重新率定" in note for note in adapted["assumptions"])
    assert adapted["total_volume"] > standard["total_volume"]


def test_legacy_runoff_coefficient_path_now_conserves_volume_and_keeps_full_tail():
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[10, 10],
        runoff_coeff=0.3,
        A=1.0,
        tp=2.0,
        dt_rain_h=2.0,
        dt=0.2,
    )
    expected_volume = 2 * 10.0 * 2.0 * 0.3 * 1000.0
    assert result["total_volume"] == pytest.approx(expected_volume)
    assert result["runoff_volume"] == pytest.approx(expected_volume)
    assert result["runoff"].size > result["net_rainfall"].size
    assert result["CN"] is None
    assert "常数径流系数法" in result["assumptions"][0]


def test_zero_runoff_coefficient_returns_zero_hydrograph_without_invalid_cn():
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[10, 10], runoff_coeff=0.0, A=1.0, tp=2.0
    )
    assert result["CN"] is None
    assert np.all(result["runoff"] == 0)
    assert result["total_volume"] == 0
    plot = MODULE.prepare_precipitation_runoff_plot_data(result)
    assert plot["peak_index"] == 0
    assert plot["peak_time_h"] == 0
    assert plot["peak_flow_m3_s"] == 0


def test_reported_peak_and_durations_are_hours_not_array_indices():
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[20, 60, 10], A=1, CN=75, tc=60, dt=0.0625
    )
    assert result["peak_index"] == int(np.argmax(result["runoff"]))
    assert result["peak_time"] == pytest.approx(result["peak_index"] * result["dt"])
    assert result["rise_duration"] == pytest.approx(result["peak_time"])
    assert result["recession_duration"] >= 0
    assert result["peak_flow"] == pytest.approx(np.max(result["runoff"]))
    assert result["peak_modulus"] == pytest.approx(result["peak_flow"] / 1.0)


def test_plot_data_contract_aligns_nested_rain_bars_and_flow_time():
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[20, 60, 10], A=1, CN=75, tc=60, dt=0.0625
    )
    plot = MODULE.prepare_precipitation_runoff_plot_data(result)
    delta_d = result["unit_duration"]
    assert plot["rainfall_unit"] == "mm/h"
    assert np.allclose(
        plot["total_rainfall"], result["rainfall_depth_unit_mm"] / delta_d
    )
    assert np.allclose(
        plot["net_rainfall"], result["net_rainfall_depth_mm"] / delta_d
    )
    assert np.all(plot["net_rainfall"] <= plot["total_rainfall"] + 1e-12)
    assert np.allclose(
        plot["rainfall_time_center_h"],
        result["net_rainfall_time_h"] + 0.5 * delta_d,
    )
    assert plot["total_bar_width_h"] == pytest.approx(0.80 * delta_d)
    assert plot["net_bar_width_h"] == pytest.approx(0.45 * delta_d)
    assert np.allclose(plot["flow_time_h"], result["time_h"])
    assert np.allclose(plot["flow_m3_s"], result["runoff"])
    assert plot["peak_time_h"] == pytest.approx(result["peak_time_h"])
    assert plot["rainfall_axis_inverted"] is True
    assert plot["flow_smoothing"] is False

    depth_plot = MODULE.prepare_precipitation_runoff_plot_data(
        result, rainfall_display="depth"
    )
    assert depth_plot["rainfall_unit"] == "mm/ΔD"
    assert np.allclose(depth_plot["total_rainfall"], result["rainfall_depth_unit_mm"])


def test_plot_data_contract_rejects_mixed_units_or_non_nested_rain():
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[20, 30], runoff_coeff=0.3, A=1, tc=60
    )
    invalid = result.copy()
    invalid["net_rainfall_depth_mm"] = (
        np.asarray(result["rainfall_depth_unit_mm"]) + 1.0
    )
    with pytest.raises(ValueError, match="净雨深不得大于总雨深"):
        MODULE.prepare_precipitation_runoff_plot_data(invalid)
    with pytest.raises(ValueError, match="intensity.*depth"):
        MODULE.prepare_precipitation_runoff_plot_data(result, rainfall_display="mixed")
    shifted_time = result.copy()
    shifted_time["time_h"] = np.asarray(result["time_h"]) + result["dt"]
    with pytest.raises(ValueError, match="从 0 开始"):
        MODULE.prepare_precipitation_runoff_plot_data(shifted_time)
    missing_dt = result.copy()
    missing_dt.pop("dt")
    with pytest.raises(ValueError, match="缺少绘图字段"):
        MODULE.prepare_precipitation_runoff_plot_data(missing_dt)


def test_static_chart_generator_enforces_professional_geometry(tmp_path):
    result = MODULE.analyze_flood_hydrograph(
        rainfall=[20, 60, 10], A=1, CN=75, tc=60, dt=0.0625
    )
    fig, rain_ax, flow_ax, plot = GENERATOR.build_precipitation_runoff_figure(result)
    try:
        count = len(plot["total_rainfall"])
        assert rain_ax.yaxis_inverted()
        assert rain_ax.xaxis.get_ticks_position() == "top"
        assert len(rain_ax.patches) == 2 * count
        total_patches = rain_ax.patches[:count]
        net_patches = rain_ax.patches[count:]
        for index, (total_patch, net_patch) in enumerate(zip(total_patches, net_patches)):
            total_center = total_patch.get_x() + 0.5 * total_patch.get_width()
            net_center = net_patch.get_x() + 0.5 * net_patch.get_width()
            assert total_center == pytest.approx(plot["rainfall_time_center_h"][index])
            assert net_center == pytest.approx(total_center)
            assert net_patch.get_width() < total_patch.get_width()
            assert net_patch.get_height() <= total_patch.get_height() + 1e-12
        assert len(flow_ax.lines) == 1
        assert np.allclose(flow_ax.lines[0].get_xdata(), result["time_h"])
        assert np.allclose(flow_ax.lines[0].get_ydata(), result["runoff"])
        assert "SCS-CN + NRCS PRF=484" in fig._suptitle.get_text()
    finally:
        GENERATOR.plt.close(fig)

    output = tmp_path / "professional_hydrograph.png"
    generated = GENERATOR.generate_precipitation_runoff_chart(result, output, dpi=96)
    assert generated == output.resolve()
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output.stat().st_size > 10_000
    with pytest.raises(ValueError, match="仅支持 .png"):
        GENERATOR.generate_precipitation_runoff_chart(result, tmp_path / "chart.jpg")


def test_reference_example_runs_without_nan_with_explicit_tc():
    rainfall = [2, 5, 8, 15, 20, 18, 12, 8, 5, 3, 2, 1, 0.5, 0.5, 0, 0]
    result = MODULE.analyze_flood_hydrograph(
        rainfall=rainfall, runoff_coeff=0.25, A=32.5, tc=90.0
    )
    assert np.all(np.isfinite(result["runoff"]))
    assert result["runoff_volume"] == pytest.approx(result["total_volume"], rel=1e-12)
    assert result["validation_level"].startswith("software numerical checks")
