#!/usr/bin/env python3
"""生成专业倒置雨量—径流组合图（静态 PNG）。"""

import argparse
import importlib.util
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

try:
    from scs_unit_hydrograph import (
        analyze_flood_hydrograph,
        prepare_precipitation_runoff_plot_data,
    )
except ModuleNotFoundError:
    _CORE_PATH = Path(__file__).with_name("scs_unit_hydrograph.py")
    _SPEC = importlib.util.spec_from_file_location("scs_unit_hydrograph", _CORE_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise RuntimeError("无法加载 scs_unit_hydrograph.py")
    _CORE = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_CORE)
    analyze_flood_hydrograph = _CORE.analyze_flood_hydrograph
    prepare_precipitation_runoff_plot_data = _CORE.prepare_precipitation_runoff_plot_data


TOTAL_RAIN_COLOR = "#5B9BD5"
TOTAL_RAIN_EDGE = "#3979A8"
NET_RAIN_COLOR = "#ED7D31"
NET_RAIN_EDGE = "#A94E13"
FLOW_COLOR = "#27AE60"
PEAK_COLOR = "#C0392B"
GRID_COLOR = "#E5E7EB"


def _default_title(method):
    if str(method).startswith("scs_cn"):
        return "降雨—径流过程线（SCS-CN + NRCS PRF=484）"
    return "降雨—径流过程线（径流系数 + NRCS PRF=484）"


def build_precipitation_runoff_figure(
    result,
    rainfall_display="intensity",
    title=None,
    subtitle=None,
    figsize=(16, 9),
):
    """构建专业组合图并返回 ``(fig, rain_ax, flow_ax, plot_data)``。

    雨柱由顶部零线向下，总雨宽柱与净雨窄柱同中心嵌套；流量由底部零线
    向上，直接使用模型时序，不作平滑或插值。
    """
    plot = prepare_precipitation_runoff_plot_data(result, rainfall_display)
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "Noto Sans CJK SC",
        "SimHei",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, rain_ax = plt.subplots(figsize=figsize, facecolor="white")
    flow_ax = rain_ax.twinx()
    flow_ax.set_zorder(rain_ax.get_zorder() + 1)
    flow_ax.patch.set_visible(False)
    flow_ax.set_axisbelow(True)

    rain_ax.bar(
        plot["rainfall_time_center_h"],
        plot["total_rainfall"],
        width=plot["total_bar_width_h"],
        color=TOTAL_RAIN_COLOR,
        alpha=0.78,
        edgecolor=TOTAL_RAIN_EDGE,
        linewidth=0.7,
        align="center",
        zorder=2,
    )
    rain_ax.bar(
        plot["rainfall_time_center_h"],
        plot["net_rainfall"],
        width=plot["net_bar_width_h"],
        color=NET_RAIN_COLOR,
        alpha=0.92,
        edgecolor=NET_RAIN_EDGE,
        linewidth=0.8,
        align="center",
        zorder=3,
    )
    flow_ax.fill_between(
        plot["flow_time_h"],
        0,
        plot["flow_m3_s"],
        color=FLOW_COLOR,
        alpha=0.12,
        zorder=1,
    )
    flow_line, = flow_ax.plot(
        plot["flow_time_h"],
        plot["flow_m3_s"],
        color=FLOW_COLOR,
        linewidth=2.8,
        solid_joinstyle="round",
        label="流量",
        zorder=5,
    )

    rain_end_h = float(
        plot["rainfall_time_start_h"][-1] + plot["rainfall_interval_h"]
    )
    x_end_h = max(rain_end_h, float(plot["flow_time_h"][-1]))
    rain_max = max(1.0, float(plot["total_rainfall"].max()))
    flow_max = max(1.0, float(plot["flow_m3_s"].max()))
    rain_ax.set_xlim(0, x_end_h)
    rain_ax.set_ylim(rain_max * 1.12, 0)
    flow_ax.set_ylim(0, flow_max * 1.18)

    rain_ax.xaxis.tick_top()
    rain_ax.xaxis.set_label_position("top")
    rain_ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False)
    rain_ax.set_xlabel("时间 (h)", fontsize=12, labelpad=10)
    rain_ax.set_ylabel(plot["rainfall_axis_label"], fontsize=12)
    flow_ax.set_ylabel(plot["flow_axis_label"], fontsize=12)
    flow_ax.grid(axis="y", linestyle="--", linewidth=0.8, color=GRID_COLOR, alpha=0.9)
    rain_ax.grid(False)

    chart_title = title or _default_title(result.get("method"))
    chart_subtitle = subtitle or (
        "总降雨与净雨使用同一 ΔD 和同一单位；流量保持原始计算时序"
    )
    fig.suptitle(chart_title, fontsize=20, fontweight="bold", y=0.975)
    fig.text(0.5, 0.925, chart_subtitle, ha="center", va="center", fontsize=11, color="#6B7280")

    if plot["peak_flow_m3_s"] > 0:
        peak_t = plot["peak_time_h"]
        peak_q = plot["peak_flow_m3_s"]
        flow_ax.scatter([peak_t], [peak_q], color=FLOW_COLOR, s=46, zorder=6)
        put_left = peak_t > 0.68 * x_end_h
        text_x = peak_t - 0.10 * x_end_h if put_left else peak_t + 0.10 * x_end_h
        text_y = min(peak_q + 0.10 * flow_max, 1.12 * flow_max)
        flow_ax.annotate(
            f"洪峰 {peak_q:.2f} m³/s\n峰现 {peak_t:.2f} h",
            xy=(peak_t, peak_q),
            xytext=(text_x, text_y),
            arrowprops={"arrowstyle": "->", "color": PEAK_COLOR, "lw": 1.5},
            color=PEAK_COLOR,
            fontsize=10.5,
            ha="right" if put_left else "left",
            va="bottom",
            zorder=7,
        )

    legend_handles = [
        Patch(
            facecolor=TOTAL_RAIN_COLOR,
            edgecolor=TOTAL_RAIN_EDGE,
            alpha=0.78,
            label="总降雨",
        ),
        Patch(
            facecolor=NET_RAIN_COLOR,
            edgecolor=NET_RAIN_EDGE,
            alpha=0.92,
            label="净雨",
        ),
        flow_line,
    ]
    flow_ax.legend(
        handles=legend_handles,
        loc="upper right",
        frameon=True,
        framealpha=0.95,
    )
    fig.text(
        0.075,
        0.035,
        "时标：t=0 为首个雨量时段起点；雨柱中心位于各 ΔD 时段中点。",
        fontsize=9,
        color="#6B7280",
    )
    fig.subplots_adjust(left=0.075, right=0.925, bottom=0.09, top=0.84)
    return fig, rain_ax, flow_ax, plot


def generate_precipitation_runoff_chart(
    result,
    output_path,
    rainfall_display="intensity",
    title=None,
    subtitle=None,
    dpi=300,
):
    """生成 PNG 并返回绝对路径。"""
    if isinstance(dpi, bool) or not isinstance(dpi, int) or dpi <= 0:
        raise ValueError("dpi 必须是正整数")
    output = Path(output_path)
    if output.suffix.lower() != ".png":
        raise ValueError("当前静态图生成器仅支持 .png")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, _, _, _ = build_precipitation_runoff_figure(
        result,
        rainfall_display=rainfall_display,
        title=title,
        subtitle=subtitle,
    )
    try:
        fig.savefig(
            output,
            dpi=dpi,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
    finally:
        plt.close(fig)
    return output.resolve()


def _demo_result():
    return analyze_flood_hydrograph(
        rainfall=[3, 8, 18, 35, 50, 32, 16, 8, 3],
        dt_rain_h=1.0,
        A=5.0,
        CN=75,
        tc=120.0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="outputs/precipitation_runoff_chart.png",
        help="PNG 输出路径",
    )
    parser.add_argument(
        "--rainfall-display",
        choices=("intensity", "depth"),
        default="intensity",
    )
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()
    output = generate_precipitation_runoff_chart(
        _demo_result(),
        args.output,
        rainfall_display=args.rainfall_display,
        dpi=args.dpi,
    )
    print(output)


if __name__ == "__main__":
    main()
