#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCS单位线法计算核心脚本
用于推算出口断面的洪水过程线

作者：盛
日期：2026-03-27
"""

import numpy as np
import math

def calculate_net_rainfall(rainfall, runoff_coefficient):
    """
    计算净雨量

    参数:
        rainfall: 逐时段降雨列表 [mm/h]
        runoff_coefficient: 径流系数

    返回:
        净雨量列表 [mm/h]
    """
    if not 0 <= runoff_coefficient <= 1:
        raise ValueError("runoff_coefficient must be between 0 and 1")
    return [r * runoff_coefficient for r in rainfall]

def calculate_cn_from_runoff_coeff(runoff_coeff, method='empirical'):
    """
    从径流系数估算CN值

    参数:
        runoff_coeff: 径流系数 (0-1)
        method: 估算方法

    返回:
        CN值
    """
    # 经验关系：CN ≈ 100 * C / (1 + 0.4 * C)
    # 适用于中等流域
    cn = 100 * runoff_coeff / (1 + 0.4 * runoff_coeff)
    return int(round(cn / 5) * 5)  # 取最接近的5的倍数

def calculate_concentration_time(A, L=None, slope=0.015, method='kirpich'):
    """
    计算汇流时间

    参数:
        A: 流域面积 (km²)
        L: 主河道长度 (km)，默认按面积估算
        slope: 主河道坡度 (m/m)
        method: 计算方法

    返回:
        汇流时间 (min)
    """
    if L is None:
        # 按面积估算河长：L ≈ 1.5 * A^0.5
        L = 1.5 * math.sqrt(A)

    if method == 'kirpich':
        # Kirpich公式（适用于山区小流域）
        slope_m_per_km = slope * 1000  # 转换为m/km
        tc = 0.0195 * (L ** 0.77) * (slope_m_per_km ** (-0.385)) * 60
        return tc
    else:
        # 简化估算：tc ≈ 0.3 * A^0.5 (小时)
        return 0.3 * math.sqrt(A) * 60

def calculate_lag_time(tc, method='scs'):
    """
    计算滞后时间

    参数:
        tc: 汇流时间 (min)
        method: 计算方法

    返回:
        滞后时间 (h)
    """
    if method == 'scs':
        # SCS方法：tp = tc/120
        return tc / 120
    else:
        # 经验值：半干旱地区tp ≈ 1.5-2.5h
        return max(1.5, tc / 120)

def calculate_peak_flow(A, tp):
    """
    计算洪峰流量

    参数:
        A: 流域面积 (km²)
        tp: 滞后时间 (h)

    返回:
        洪峰流量 (m³/s)
    """
    # SCS洪峰流量公式
    Qp = 2.08 * A / tp
    return Qp

def generate_unit_hydrograph(tp, dt, duration):
    """
    生成SCS单位线

    参数:
        tp: 滢后时间 (h)
        dt: 时段长 (h)
        duration: 总历时 (h)

    返回:
        单位线纵坐标列表
    """
    if tp <= 0:
        raise ValueError("tp must be positive")
    if dt <= 0:
        raise ValueError("dt must be positive")
    if duration <= 0:
        raise ValueError("duration must be positive")

    t = np.arange(0, duration + dt, dt)

    # SCS无量纲单位线
    Tp = tp  # 峰现时间
    Tb = 2.67 * tp  # 基底时间

    # 单位线纵坐标
    Q = np.zeros(len(t))
    for i, ti in enumerate(t):
        if ti < Tp:
            Q[i] = (ti / Tp) ** 2.5
        elif ti <= Tb:
            Q[i] = (ti / Tp) ** 2.5 * np.exp(-(ti - Tp) / tp)
        else:
            Q[i] = 0

    # 归一化
    total = np.sum(Q)
    if not np.isfinite(total) or total <= 0:
        raise ValueError(
            "unit hydrograph has no positive support; choose a smaller dt or a longer duration"
        )
    Q = Q / total * 1.0  # 单位线总和为1

    return Q

def convolve_rainfall_runoff(net_rainfall, unit_hydrograph):
    """
    卷积计算洪水过程线

    参数:
        net_rainfall: 净雨量列表 [mm/h]
        unit_hydrograph: 单位线纵坐标

    返回:
        流量过程线 [m³/s]
    """
    # 卷积
    runoff = np.convolve(net_rainfall, unit_hydrograph, mode='full')

    # 截取前n个时段（n为降雨时段数）
    runoff = runoff[:len(net_rainfall)]

    return runoff

def analyze_flood_hydrograph(rainfall, runoff_coeff, A, **kwargs):
    """
    完整的洪水过程线分析

    参数:
        rainfall: 逐时段降雨 [mm/h]
        runoff_coeff: 径流系数
        A: 流域面积 (km²)
        **kwargs: 可选参数
            - CN: 曲线数
            - tc: 汇流时间 (min)
            - tp: 滞后时间 (h)
            - dt: 计算时段 (h)

    返回:
        dict: 包含所有计算结果
    """
    # 计算净雨量
    net_rainfall = calculate_net_rainfall(rainfall, runoff_coeff)

    # 确定参数
    CN = kwargs.get('CN', calculate_cn_from_runoff_coeff(runoff_coeff))
    tc = kwargs.get('tc', calculate_concentration_time(A))
    tp = kwargs.get('tp', calculate_lag_time(tc))
    # Keep the documented default Δt = 0.133 × tp from SKILL.md.  The
    # previous 1-hour lower bound skipped the entire response for small basins.
    dt = kwargs.get('dt', 0.133 * tp)

    # 计算洪峰流量
    Qp = calculate_peak_flow(A, tp)

    # 生成单位线
    duration = len(rainfall) * dt
    UH = generate_unit_hydrograph(tp, dt, duration)

    # 卷积计算洪水过程线
    runoff = convolve_rainfall_runoff(net_rainfall, UH)

    # 缩放到实际洪峰
    runoff_peak = float(np.max(runoff))
    if runoff_peak > 0:
        scale_factor = Qp / runoff_peak
        runoff = runoff * scale_factor

    # 计算洪水特征
    peak_idx = int(np.argmax(runoff))
    total_volume = sum(net_rainfall) * A * 1000  # m³

    # 洪峰模数
    qm = Qp / A

    return {
        'rainfall': rainfall,
        'net_rainfall': net_rainfall,
        'runoff': runoff,
        'CN': CN,
        'tc': tc,
        'tp': tp,
        'dt': dt,
        'Qp': Qp,
        'peak_time': peak_idx,
        'peak_modulus': qm,
        'total_volume': total_volume,
        'rise_duration': peak_idx,
        'recession_duration': len(runoff) - peak_idx
    }

# 测试代码
if __name__ == '__main__':
    # 示例数据
    rainfall = [2, 5, 8, 15, 20, 18, 12, 8, 5, 3, 2, 1, 0.5, 0.5, 0, 0]
    A = 32.5
    runoff_coeff = 0.25

    result = analyze_flood_hydrograph(rainfall, runoff_coeff, A)

    print("=" * 60)
    print("洪水过程线分析结果")
    print("=" * 60)
    print(f"流域面积: {A} km²")
    print(f"径流系数: {runoff_coeff}")
    print(f"CN值: {result['CN']}")
    print(f"汇流时间: {result['tc']:.1f} min")
    print(f"滞后时间: {result['tp']:.2f} h")
    print(f"洪峰流量: {result['Qp']:.2f} m³/s")
    print(f"峰现时间: 第{result['peak_time']}小时")
    print(f"洪峰模数: {result['peak_modulus']:.3f} m³/s/km²")
    print(f"洪水总量: {result['total_volume']:.0f} m³")
    print("=" * 60)
