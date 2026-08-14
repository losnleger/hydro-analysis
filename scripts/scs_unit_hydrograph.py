#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCS单位线法计算核心脚本
用于推算出口断面的洪水过程线

作者：盛
日期：2026-03-27

CN 值取值依据与引用（REFERENCES）：
[TR-55]      USDA SCS, "Urban Hydrology for Small Watersheds", Technical Release 55,
             2nd ed., June 1986. Tables 2-1 (AMC 分级), 2-2a (城镇用地 CN),
             2-2b (耕作农地 CN), 2-2c (其他农地 CN), 2-2d (干旱半干旱牧场 CN)。
[NEH630-7]   USDA NRCS, National Engineering Handbook Part 630, Chapter 7,
             "Hydrologic Soil Groups" —— 水文土壤组 A/B/C/D 定义。
[NEH630-10]  USDA NRCS, National Engineering Handbook Part 630, Chapter 10,
             "Estimation of Direct Runoff from Storm Rainfall" ——
             AMC I/III 与 AMC II 的 CN 换算公式。
[NEH630-15]  USDA NRCS, National Engineering Handbook Part 630, Chapter 15,
             "Time of Concentration" —— lag = 0.6 Tc；Kirpich 公式与适用样本。
[NEH630-16]  USDA NRCS, National Engineering Handbook Part 630, Chapter 16,
             "Hydrographs" —— 表 16-1 标准 PRF=484 无量纲单位线、
             Tp = ΔD/2 + lag、ΔD = 0.133 Tc。
[NEH630-E]   USDA NRCS, National Engineering Handbook Part 630, Subpart E,
             "Runoff Curve Numbers", amended June 2025 —— HSG/CN 与城镇
             不透水面积综合 CN 的适用边界。
[NEH630-H]   USDA NRCS, National Engineering Handbook Part 630, Subpart H,
             "Estimation of Direct Runoff from Storm Rainfall", amended August
             2025 —— SCS-CN 产流方程及 Ia/S 改变时需重新开发 CN 的限制。
[Woodward2003] Woodward D.E., Hawkins R.H., Jiang R., Hjelmfelt A.T., Van Mullem J.A.,
             Quan Q.D., "Runoff Curve Number Method: Examination of the Initial
             Abstraction Ratio", ASCE World Water & Environmental Resources
             Congress 2003, doi:10.1061/40685(2003)308 —— 半干旱区建议初损率
             λ=0.05（原 SCS 默认 λ=0.2）。
[Feng2021]   冯憬, 卫伟, 冯青郁, "黄土丘陵区SCS-CN模型径流曲线数的计算与校正",
             生态学报, 2021, 41(10): 4170-4181, doi:10.5846/stxb201912082665 ——
             黄土丘陵区 CN 受前期土壤含水量、植被盖度、土地利用、坡度与整地
             工程措施显著影响；水平沟、水平阶、反坡台等整地措施可降低 CN。
"""

import numpy as np
import math

# ============================================================
# 一、水文土壤组（Hydrologic Soil Group, HSG）
# 依据 NEH-630 第 7 章表 7-1。下列 Ksat 区间只对应“无不透水层、无高水位，
# 评价 0–50 cm 最低透水层”的筛查行；完整分组还必须结合限制层深度、高水位
# 和双重 HSG（A/D、B/D、C/D）。不可把土壤质地或旧最小下渗率阈值直接当成
# NEH-630 的完整判据。
# ============================================================

HSG_A, HSG_B, HSG_C, HSG_D = "A", "B", "C", "D"

HSG_DEFINITIONS = {
    HSG_A: {
        "name": "低产流潜力组",
        "screening_ksat_um_s": (40.0, None),
        "screening_ksat_in_h": (5.67, None),
        "description": "筛查条件下 Ksat > 40 μm/s；完整判定需结合限制层和高水位。",
    },
    HSG_B: {
        "name": "中等产流潜力组",
        "screening_ksat_um_s": (10.0, 40.0),
        "screening_ksat_in_h": (1.42, 5.67),
        "description": "筛查条件下 10 < Ksat ≤ 40 μm/s；完整判定需结合限制层和高水位。",
    },
    HSG_C: {
        "name": "较高产流潜力组",
        "screening_ksat_um_s": (1.0, 10.0),
        "screening_ksat_in_h": (0.14, 1.42),
        "description": "筛查条件下 1 < Ksat ≤ 10 μm/s；完整判定需结合限制层和高水位。",
    },
    HSG_D: {
        "name": "高产流潜力组",
        "screening_ksat_um_s": (0.0, 1.0),
        "screening_ksat_in_h": (0.0, 0.14),
        "description": "筛查条件下 Ksat ≤ 1 μm/s；浅限制层或高水位也可使土壤归入 D/双重 HSG。",
    },
}

# [NEH630-16] Table 16-1, standard NRCS dimensionless curvilinear UH (PRF=484).
# The ordinates are q/qp versus t/Tp.  Keep this table verbatim and interpolate
# between its published nodes; do not replace it with an uncited analytic shape.
NRCS_484_TIME_RATIOS = np.array([
    0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9,
    1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9,
    2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8,
    4.0, 4.5, 5.0,
], dtype=float)
NRCS_484_DISCHARGE_RATIOS = np.array([
    0.000, 0.030, 0.100, 0.190, 0.310, 0.470, 0.660, 0.820, 0.930, 0.990,
    1.000, 0.990, 0.930, 0.860, 0.780, 0.680, 0.560, 0.460, 0.390, 0.330,
    0.280, 0.207, 0.147, 0.107, 0.077, 0.055, 0.040, 0.029, 0.021, 0.015,
    0.011, 0.005, 0.000,
], dtype=float)

KIRPICH_MIN_AREA_KM2 = 1.25 * 0.0040468564224
KIRPICH_MAX_AREA_KM2 = 112.0 * 0.0040468564224

# ============================================================
# 二、前期土壤湿度条件（AMC / ARC）与 CN 换算
# 依据 TR-55 表 2-1（前 5 日累计雨量分级）与 NEH-630 第 10 章换算公式。
# ============================================================

# 前5日累计降雨量分级 (mm)：key = (amc, 季节)
AMC_ANTECEDENT_RAINFALL_MM = {
    "I": {"dormant": (None, 13), "growing": (None, 36)},
    "II": {"dormant": (13, 28), "growing": (36, 53)},
    "III": {"dormant": (28, None), "growing": (53, None)},
}

# ============================================================
# 三、CN 取值表（AMC II 基准）
# 数值来源见文件头 REFERENCES；HSG 列顺序为 (A, B, C, D)。
# 表 2-2d 多数覆被类型只给出 A/B/C 三列。
# ============================================================

# ---- 表 2-2b：耕作农地（TR-55 Table 2-2b）----
# key: (土地利用, 耕作方式); 值为 {水文条件: (A, B, C, D)}
CN_CULTIVATED = {
    ("休耕地(裸地)", "straight"): {"poor": (77, 86, 91, 94)},
    ("中耕作物", "straight"): {"poor": (72, 81, 88, 91), "good": (67, 78, 85, 89)},
    ("中耕作物", "contoured"): {"poor": (70, 79, 84, 88), "good": (65, 75, 82, 86)},
    ("中耕作物", "terraced"): {"poor": (66, 74, 80, 82), "good": (62, 71, 78, 81)},
    ("小粒谷物", "straight"): {"poor": (65, 76, 84, 88), "good": (63, 75, 83, 87)},
    ("小粒谷物", "contoured"): {"poor": (63, 74, 82, 85), "good": (61, 73, 81, 84)},
    ("小粒谷物", "terraced"): {"poor": (61, 72, 79, 82), "good": (59, 70, 78, 81)},
    ("密植豆科/轮作牧草", "straight"): {"poor": (66, 77, 85, 89), "good": (58, 72, 81, 85)},
    ("密植豆科/轮作牧草", "contoured"): {"poor": (64, 75, 83, 85), "good": (55, 69, 78, 83)},
    ("密植豆科/轮作牧草", "terraced"): {"poor": (63, 73, 80, 83), "good": (51, 67, 77, 80)},
}

# ---- 表 2-2c：其他农地（TR-55 Table 2-2c）----
# key: 土地利用; 值为 {水文条件: (A, B, C, D)}
CN_OTHER_AGRICULTURAL = {
    "牧场/草地/放牧地": {"poor": (68, 79, 86, 89), "fair": (49, 69, 79, 84), "good": (39, 61, 74, 80)},
    "割草草地(禁牧)": {"good": (30, 58, 71, 78)},
    "灌木地": {"poor": (48, 67, 77, 83), "fair": (35, 56, 70, 77), "good": (30, 48, 65, 73)},
    "林草组合(果园/苗圃)": {"poor": (57, 73, 82, 86), "fair": (43, 65, 76, 82), "good": (32, 58, 72, 79)},
    "林地": {"poor": (45, 66, 77, 83), "fair": (36, 60, 73, 79), "good": (30, 55, 70, 77)},
    "农村庄院(建筑/场院/道路)": {"good": (59, 74, 82, 86)},
}

# ---- 表 2-2a：城镇用地（TR-55 Table 2-2a）----
CN_URBAN = {
    "开放空间(草坪/公园)": {"poor": (68, 79, 86, 89), "fair": (49, 69, 79, 84), "good": (39, 61, 74, 80)},
    "不透水面(屋顶/停车场)": {"impervious": (98, 98, 98, 98)},
    "铺装道路(路缘石+管网)": {"impervious": (98, 98, 98, 98)},
    "铺装道路(明渠排水)": {"good": (83, 89, 92, 93)},
    "砾石道路": {"good": (76, 85, 89, 91)},
    "土路": {"good": (72, 82, 87, 89)},
    "商业区(85%不透水)": {"good": (89, 92, 94, 95)},
    "工业区(72%不透水)": {"good": (81, 88, 91, 93)},
    "居住区≤1/8英亩(65%不透水)": {"good": (77, 85, 90, 92)},
    "居住区1/4英亩(38%不透水)": {"good": (61, 75, 83, 87)},
    "居住区1/3英亩(30%不透水)": {"good": (57, 72, 81, 86)},
    "居住区1/2英亩(25%不透水)": {"good": (54, 70, 80, 85)},
    "居住区1英亩(20%不透水)": {"good": (51, 68, 79, 84)},
    "居住区2英亩(12%不透水)": {"good": (46, 65, 77, 82)},
    "在建开发区(新平整裸地)": {"good": (77, 86, 91, 94)},
    "荒漠城镇(天然景观)": {"good": (63, 77, 85, 88)},
    "荒漠城镇(人工防草布+砂砾)": {"good": (96, 96, 96, 96)},
}

# ---- 表 2-2d：干旱半干旱牧场（TR-55 Table 2-2d）----
# 注：多数覆被类型原表只给 A/B/C 三列；荒漠灌木给 A/B/C/D 四列。
CN_ARID_RANGELAND = {
    "草本植被(草/杂草/低灌丛)": {"poor": (80, 87, 93), "fair": (71, 81, 89), "good": (62, 74, 85)},
    "栎-山杨山地灌丛": {"poor": (66, 74, 79), "fair": (48, 57, 63), "good": (30, 41, 48)},
    "矮松-刺柏林(草下层)": {"poor": (75, 85, 89), "fair": (58, 73, 80), "good": (41, 61, 71)},
    "蒿草灌丛(带草下层)": {"poor": (67, 80, 85), "fair": (51, 63, 70), "good": (35, 47, 55)},
    "荒漠灌木(盐灌木/木馏油等)": {"poor": (63, 77, 85, 88), "fair": (55, 72, 81, 86), "good": (49, 68, 79, 84)},
}

# ---- 中国补充取值（工程假设，非 TR-55 原表，必须本地率定）----
# SCS-CN 以"先蓄满后产流"的 Horton 产流机制为基础，对长期蓄水的稻田与
# 蓄满产流为主的湿润区适用性差。稻田在淹灌期建议按水面/不透水面处理
# （CN≈98）或改用蓄满产流模型；下值仅用于旱作期粗略估算。
CN_CHINA_SUPPLEMENT = {
    "水田(旱作期)": {"good": (78, 85, 90, 94)},
    "梯田旱地(水平沟/水平阶/反坡台)": {"good": (62, 72, 81, 85)},
}

# ---- 区域初损率建议（依据 Woodward2003、Feng2021 及中国应用文献）----
# 不推荐对 CN 本身做"一刀切"的区域加减——CN 修正应通过初损率 λ 与本地率定完成。
REGION_GUIDANCE = {
    "humid": {
        "name": "湿润区（年降水>800mm，南方地区）",
        "initial_abstraction_ratio": 0.2,
        "note": "TR-55 表按 AMC II 直接查用；注意 SCS-CN 对蓄满产流机制适用性有限，稻田/河网区慎用。",
    },
    "semi_humid": {
        "name": "半湿润区（年降水400-800mm，华北/东北南部）",
        "initial_abstraction_ratio": 0.2,
        "note": "TR-55 表直接查用，需核对设计雨量与 AMC II 前5日雨量假设的一致性。",
    },
    "semi_arid": {
        "name": "半干旱区（年降水200-400mm，黄土高原等）",
        "initial_abstraction_ratio": 0.05,
        "note": "λ=0.05 仅为文献建议，不与按 Ia=0.2S 建立的 NRCS CN 表自动兼容；"
                "必须用当地径流小区/实测资料联合率定 λ 与 CN。",
    },
    "arid": {
        "name": "干旱区（年降水<200mm，西北内陆）",
        "initial_abstraction_ratio": 0.05,
        "note": "优先查表 2-2d；λ=0.05 仅作需联合率定的实验建议，未率定前仅供量级参考。",
    },
    "alpine": {
        "name": "高寒区（青藏高原及周边）",
        "initial_abstraction_ratio": None,
        "note": "冻融过程、冰川积雪产流机制与 SCS-CN 假设差异大，一般不推荐使用，应改用适合高寒区的产流模型。",
    },
}

CN_CONDITION_ALIASES = {
    "poor": "poor", "差": "poor", "p": "poor",
    "fair": "fair", "中": "fair", "f": "fair",
    "good": "good", "好": "good", "g": "good",
    "impervious": "impervious", "不透水": "impervious",
}

CN_TREATMENT_ALIASES = {
    "straight": "straight", "直行": "straight", "sr": "straight", "顺坡": "straight",
    "contoured": "contoured", "等高": "contoured", "c": "contoured",
    "terraced": "terraced", "梯田": "terraced", "ct": "terraced", "等高梯田": "terraced",
}

CN_LANDUSE_ALIASES = {
    "row crops": "中耕作物", "行播作物": "中耕作物", "旱地": "中耕作物",
    "small grain": "小粒谷物", "小粒谷物(小麦等)": "小粒谷物", "小麦": "小粒谷物",
    "legumes": "密植豆科/轮作牧草", "豆科": "密植豆科/轮作牧草", "轮作牧草": "密植豆科/轮作牧草",
    "pasture": "牧场/草地/放牧地", "grassland": "牧场/草地/放牧地", "草地": "牧场/草地/放牧地",
    "meadow": "割草草地(禁牧)", "woodland": "林地", "forest": "林地", "brush": "灌木地",
    "orchard": "林草组合(果园/苗圃)", "farmstead": "农村庄院(建筑/场院/道路)",
    "paddy": "水田(旱作期)", "rice paddy": "水田(旱作期)", "水田": "水田(旱作期)",
    "fallow": "休耕地(裸地)", "休耕地": "休耕地(裸地)",
}


def _validate_finite(value, name):
    """Return *value* as float and reject booleans, NaN, Inf and non-numbers."""
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} 必须是有限数值")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是有限数值") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} 必须是有限数值")
    return result


def _validate_positive(value, name):
    result = _validate_finite(value, name)
    if result <= 0:
        raise ValueError(f"{name} 必须为正")
    return result


def _validate_cn(value, name="CN"):
    result = _validate_finite(value, name)
    if not 0 < result <= 100:
        raise ValueError(f"{name} 必须在 (0, 100] 之间")
    return result


def _validate_lambda(value):
    result = _validate_finite(value, "初损率 λ")
    if not 0 < result <= 1:
        raise ValueError("初损率 λ 必须在 (0, 1] 之间")
    return result


def _as_nonnegative_1d(values, name):
    """Validate a non-empty one-dimensional finite, nonnegative series."""
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} 必须是一维非空序列")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} 不能包含 NaN 或 Inf")
    if np.any(array < 0):
        raise ValueError(f"{name} 不能包含负值")
    return array

def normalize_condition(condition):
    """规范化水文条件（poor/fair/good/impervious）。"""
    key = CN_CONDITION_ALIASES.get(str(condition).strip().lower())
    if key is None:
        raise ValueError(
            f"未知水文条件 {condition!r}；可选：poor/差、fair/中、good/好、impervious/不透水"
        )
    return key

def normalize_treatment(treatment):
    """规范化耕作方式（straight/contoured/terraced）。"""
    key = CN_TREATMENT_ALIASES.get(str(treatment).strip().lower())
    if key is None:
        raise ValueError(
            f"未知耕作方式 {treatment!r}；可选：straight/直行、contoured/等高、terraced/梯田"
        )
    return key

def normalize_land_use(land_use):
    """规范化土地利用名称（中文/英文别名 → 标准键名）。"""
    key = str(land_use).strip()
    return CN_LANDUSE_ALIASES.get(key.lower(), key)

def _pick_hsg(values, hsg):
    """从 (A, B, C[, D]) 取值元组中取出指定土壤组的 CN。"""
    hsg = str(hsg).upper()
    if hsg not in {"A", "B", "C", "D"}:
        raise ValueError(f"未知水文土壤组 {hsg!r}；可选 A/B/C/D")
    idx = {"A": 0, "B": 1, "C": 2, "D": 3}[hsg]
    if idx >= len(values):
        raise ValueError(
            f"该土地利用类型在 TR-55 原表中未给出 {hsg} 组（只给出前 {len(values)} 组）的 CN；"
            "请核实土壤组划分或改用相邻组并说明理由"
        )
    return values[idx]

def select_cn(land_use, hsg=HSG_B, hydrologic_condition="good", treatment="straight",
              crop_residue=False):
    """
    按 TR-55 表 2-2a/2-2b/2-2c/2-2d 查取 AMC II 基准 CN 值。

    参数:
        land_use: 土地利用类型（中文或英文别名，见 CN_LANDUSE_ALIASES）
        hsg: 水文土壤组 'A'/'B'/'C'/'D'
        hydrologic_condition: 水文条件 poor/差、fair/中、good/好、impervious/不透水
        treatment: 耕作方式（仅中耕作物/小粒谷物/豆科牧草需要）
                   straight/直行、contoured/等高、terraced/梯田
        crop_residue: 是否地表常年保留作物残茬（TR-55：残茬覆盖可降低 CN，
                      此处按 -2 计，为工程近似，优先以本地率定为准）

    返回:
        CN 值 (int)
    """
    land_use = normalize_land_use(land_use)
    condition = normalize_condition(hydrologic_condition)

    found = None
    # 1) 耕作农地（表 2-2b）
    if land_use in dict.fromkeys(k[0] for k in CN_CULTIVATED):
        treatment_key = normalize_treatment(treatment)
        try:
            found = CN_CULTIVATED[(land_use, treatment_key)][condition]
        except KeyError:
            raise ValueError(
                f"土地利用 {land_use!r} × 耕作方式 {treatment_key!r} × 水文条件 {condition!r} "
                "组合不存在于表 2-2b"
            )
    # 2) 其他农地（表 2-2c）
    elif land_use in CN_OTHER_AGRICULTURAL:
        try:
            found = CN_OTHER_AGRICULTURAL[land_use][condition]
        except KeyError:
            raise ValueError(
                f"土地利用 {land_use!r} 无水文条件 {condition!r}；可选："
                + "、".join(sorted(CN_OTHER_AGRICULTURAL[land_use]))
            )
    # 3) 城镇用地（表 2-2a）
    elif land_use in CN_URBAN:
        try:
            found = CN_URBAN[land_use][condition]
        except KeyError:
            raise ValueError(
                f"土地利用 {land_use!r} 无水文条件 {condition!r}；可选："
                + "、".join(sorted(CN_URBAN[land_use]))
            )
    # 4) 干旱半干旱牧场（表 2-2d）
    elif land_use in CN_ARID_RANGELAND:
        try:
            found = CN_ARID_RANGELAND[land_use][condition]
        except KeyError:
            raise ValueError(
                f"土地利用 {land_use!r} 无水文条件 {condition!r}；可选："
                + "、".join(sorted(CN_ARID_RANGELAND[land_use]))
            )
    # 5) 中国补充取值（工程假设，需率定）
    elif land_use in CN_CHINA_SUPPLEMENT:
        try:
            found = CN_CHINA_SUPPLEMENT[land_use][condition]
        except KeyError:
            raise ValueError(
                f"土地利用 {land_use!r} 无水文条件 {condition!r}；可选："
                + "、".join(sorted(CN_CHINA_SUPPLEMENT[land_use]))
            )

    if found is None:
        raise ValueError(
            f"未知土地利用类型 {land_use!r}。可用类型（含英文别名）：\n"
            + "耕作农地: " + "、".join(sorted(set(k[0] for k in CN_CULTIVATED))) + "\n"
            + "其他农地: " + "、".join(sorted(CN_OTHER_AGRICULTURAL)) + "\n"
            + "城镇用地: " + "、".join(sorted(CN_URBAN)) + "\n"
            + "干旱半干旱牧场: " + "、".join(sorted(CN_ARID_RANGELAND)) + "\n"
            + "中国补充(需率定): " + "、".join(sorted(CN_CHINA_SUPPLEMENT))
        )

    cn = _pick_hsg(found, hsg)
    if crop_residue:
        raise ValueError(
            "crop_residue=True 不再使用统一 CN-2 近似；TR-55 的残茬处理值随作物、"
            "耕作方式和水文条件变化，请直接选用对应表值或提供本地率定 CN"
        )
    return int(cn)

def adjust_cn_for_amc(cn_ii, amc="II"):
    """
    AMC I/II/III 之间的 CN 换算（NEH-630 第 10 章公式）。

    CN(I)   = 4.2 × CN(II) / (10 - 0.058 × CN(II))
    CN(III) = 23  × CN(II) / (10 + 0.13  × CN(II))

    参数:
        cn_ii: AMC II 基准 CN
        amc: 'I' / 'II' / 'III'（也接受 '1'/'2'/'3' 与 1/2/3）

    返回:
        换算后的 CN (int)
    """
    cn_ii = _validate_cn(cn_ii, "cn_ii")
    alias = {"1": "I", "2": "II", "3": "III", 1: "I", 2: "II", 3: "III"}
    amc = alias.get(amc, str(amc).upper())
    if amc == "II":
        return int(cn_ii)
    if amc == "I":
        denominator = 10 - 0.058 * cn_ii
        if denominator <= 0:
            raise ValueError("CN(II) 过大导致 AMC I 换算公式分母非正")
        return int(round(4.2 * cn_ii / denominator))
    if amc == "III":
        return int(round(23 * cn_ii / (10 + 0.13 * cn_ii)))
    raise ValueError(f"未知 AMC 等级 {amc!r}；可选 I/II/III")

def composite_cn(segments):
    """
    面积加权综合 CN：CNc = Σ(CN_i × A_i) / Σ(A_i)。

    参数:
        segments: [(cn, area), ...] 或 [(cn, area_ratio), ...]

    返回:
        综合 CN (int)
    """
    if not segments:
        raise ValueError("segments 不能为空")
    checked = []
    for index, (cn, area) in enumerate(segments):
        cn_value = _validate_cn(cn, f"segments[{index}].cn")
        area_value = _validate_positive(area, f"segments[{index}].area")
        checked.append((cn_value, area_value))
    total_area = sum(area for _, area in checked)
    weighted = sum(cn * area for cn, area in checked) / total_area
    return int(round(weighted))

def composite_cn_urban(pervious_cn, impervious_percent, connected_ratio=1.0):
    """
    城镇混合区综合 CN（[NEH630-E] eq. 630E-1/630E-2）。

    不透水面积全部连通（connected_ratio=1）时：
        CNc = CNp + (Pimp/100) × (98 - CNp)
    其中 CNp 为透水部分 CN，Pimp 为不透水率(%)。仅当总不透水率 <30%
    时，才按 eq. 630E-2 对不连通面积折减 (1 - 0.5R)；当不透水率
    >=30% 时按 eq. 630E-1 面积加权，不再采用该折减。

    参数:
        pervious_cn: 透水部分 CN
        impervious_percent: 不透水率 (%)
        connected_ratio: 不透水面积中直接连通排水管网的比例 (0-1)

    返回:
        综合 CN (float，保留 1 位小数)
    """
    pervious_cn = _validate_cn(pervious_cn, "pervious_cn")
    impervious_percent = _validate_finite(impervious_percent, "impervious_percent")
    connected_ratio = _validate_finite(connected_ratio, "connected_ratio")
    if not 0 <= impervious_percent <= 100:
        raise ValueError("impervious_percent 必须在 0-100 之间")
    if not 0 <= connected_ratio <= 1:
        raise ValueError("connected_ratio 必须在 0-1 之间")
    pimp = impervious_percent / 100.0
    if impervious_percent >= 30:
        # [NEH630-E] eq. 630E-1: at >=30% imperviousness, use the directly
        # connected/area-weighted relation; remaining pervious storage is not
        # credited through the unconnected-area adjustment.
        cn = pervious_cn + pimp * (98 - pervious_cn)
    else:
        # [NEH630-E] eq. 630E-2, valid only for total impervious area <30%.
        r_unconnected = 1.0 - connected_ratio
        cn = pervious_cn + pimp * (98 - pervious_cn) * (1 - 0.5 * r_unconnected)
    return round(cn, 1)

def cn_to_s_mm(cn):
    """由 CN 计算最大潜在滞留量 S (mm)：S = 25400/CN − 254。"""
    cn = _validate_cn(cn, "CN")
    return 25400.0 / cn - 254.0

def initial_abstraction_mm(cn, lam=0.2):
    """初损量 Ia (mm)：Ia = λ × S；NRCS CN 表的标准 λ 为 0.2。"""
    lam = _validate_lambda(lam)
    return lam * cn_to_s_mm(cn)

def direct_runoff_mm(precipitation_mm, cn, lam=0.2):
    """
    SCS-CN 产流公式（单场次累计雨量 → 直接径流深）。

    Q = (P - Ia)^2 / (P - Ia + S)，当 P > Ia；否则 Q = 0。
    """
    precipitation_mm = _validate_finite(precipitation_mm, "precipitation_mm")
    if precipitation_mm < 0:
        raise ValueError("precipitation_mm 不能为负")
    lam = _validate_lambda(lam)
    s = cn_to_s_mm(cn)
    ia = lam * s
    if precipitation_mm <= ia:
        return 0.0
    return (precipitation_mm - ia) ** 2 / (precipitation_mm - ia + s)

def initial_abstraction_ratio_for_region(region):
    """返回区域文献建议 λ；非 0.2 值不自动与 NRCS CN 表兼容。"""
    alias = {
        "湿润": "humid", "湿润区": "humid", "hum": "humid",
        "半湿润": "semi_humid", "半湿润区": "semi_humid",
        "半干旱": "semi_arid", "半干旱区": "semi_arid",
        "干旱": "arid", "干旱区": "arid",
        "高寒": "alpine", "高寒区": "alpine",
    }
    key = alias.get(str(region).strip(), str(region).strip().lower())
    if key not in REGION_GUIDANCE:
        raise ValueError(f"未知区域类型 {region!r}；可选：湿润区/半湿润区/半干旱区/干旱区/高寒区")
    return REGION_GUIDANCE[key]["initial_abstraction_ratio"]

# ============================================================
# 计算函数与时间离散契约
# ============================================================

def calculate_net_rainfall(rainfall, runoff_coeff):
    """按常数径流系数计算净雨强度 [mm/h]（仅粗略线性路径）。"""
    rain = _as_nonnegative_1d(rainfall, "rainfall")
    runoff_coeff = _validate_finite(runoff_coeff, "runoff_coeff")
    if not 0 <= runoff_coeff <= 1:
        raise ValueError("runoff_coeff 必须在 [0, 1] 之间")
    return (rain * runoff_coeff).tolist()


def calculate_cn_from_runoff_coeff(runoff_coeff, method="empirical"):
    """[已弃用] 无资料时的经验映射；不能替代查表或率定。"""
    if method != "empirical":
        raise ValueError("仅支持 method='empirical'")
    runoff_coeff = _validate_finite(runoff_coeff, "runoff_coeff")
    if not 0 < runoff_coeff <= 1:
        raise ValueError("用于反推 CN 的 runoff_coeff 必须在 (0, 1] 之间")
    cn = 100.0 * runoff_coeff / (1.0 + 0.4 * runoff_coeff)
    return int(min(100, max(1, round(cn / 5.0) * 5)))


def calculate_concentration_time(
    A, L=None, slope=None, method="kirpich", allow_extrapolation=False
):
    """计算汇流时间 Tc [min]。

    `kirpich` 复现 [NEH630-15] eq. 630.15-12：
    Tc = 0.007 L_ft^0.77 S^-0.385。换成 L_m 后系数为约 0.0175。
    该式样本仅覆盖 1.25–112 acre、农村、沟道明确且坡陡的 Tennessee
    流域；超出面积范围默认拒绝，且不再由面积静默推算河长。

    `area_estimate` 保留旧的 Tc_h≈0.3*sqrt(A) h 作为显式工程假设；本 API
    将它换算为 min 返回，不能作为 NRCS/Kirpich 或专业验证结果。
    """
    A = _validate_positive(A, "A")
    method = str(method).strip().lower()
    if method == "kirpich":
        if L is None or slope is None:
            raise ValueError("Kirpich 法必须显式提供 L(km) 与 slope(m/m)")
        L = _validate_positive(L, "L")
        slope = _validate_positive(slope, "slope")
        if not allow_extrapolation and not (KIRPICH_MIN_AREA_KM2 <= A <= KIRPICH_MAX_AREA_KM2):
            raise ValueError(
                "流域面积超出 Kirpich 原始样本 1.25–112 acre；请提供经验证的 Tc，"
                "或仅在有专业依据时设置 allow_extrapolation=True"
            )
        L_m = L * 1000.0
        metric_coefficient = 0.007 * (3.280839895013123 ** 0.77)
        return metric_coefficient * (L_m ** 0.77) * (slope ** -0.385)
    if method == "area_estimate":
        return 0.3 * math.sqrt(A) * 60.0
    raise ValueError("method 可选 'kirpich' 或 'area_estimate'")


def calculate_lag_time(tc, method="nrcs"):
    """由 Tc[min] 计算 watershed lag[h]；[NEH630-15] eq. 630.15-3。"""
    tc = _validate_positive(tc, "tc")
    if str(method).strip().lower() not in {"nrcs", "scs"}:
        raise ValueError("lag 仅支持 NRCS/SCS 的 L=0.6Tc 关系")
    return 0.6 * tc / 60.0


def calculate_unit_duration(tc):
    """由 Tc[min] 计算 NRCS 单位净雨历时 ΔD[h]；[NEH630-16] eq. 16A-13。"""
    tc = _validate_positive(tc, "tc")
    return 0.133 * tc / 60.0


def calculate_time_to_peak(tc, unit_duration_h=None):
    """计算 Tp[h] = ΔD/2 + lag；不可把 Tp 与 lag 混为同一参数。"""
    tc = _validate_positive(tc, "tc")
    lag_h = calculate_lag_time(tc)
    if unit_duration_h is None:
        unit_duration_h = calculate_unit_duration(tc)
    unit_duration_h = _validate_positive(unit_duration_h, "unit_duration_h")
    tp_h = lag_h + 0.5 * unit_duration_h
    if unit_duration_h > 0.25 * tp_h + 1e-12:
        raise ValueError("unit_duration_h 应不大于 0.25×Tp（NEH630-16 时段限制）")
    return tp_h


def calculate_peak_flow(A, tp, runoff_depth_mm=10.0, peak_rate_factor=484.0):
    """NRCS 单位线理论峰值 [m³/s]。

    [NEH630-16] eq. 16A-6 的公制换算为
    qp = (PRF/484) * 0.208333333 * A_km2 * Q_mm / Tp_h。
    默认 Q=10 mm，保持旧 API 中“1 cm 单位线峰值”的语义。
    """
    A = _validate_positive(A, "A")
    tp = _validate_positive(tp, "tp")
    runoff_depth_mm = _validate_positive(runoff_depth_mm, "runoff_depth_mm")
    peak_rate_factor = _validate_positive(peak_rate_factor, "peak_rate_factor")
    return (peak_rate_factor / 484.0) * (5.0 / 24.0) * A * runoff_depth_mm / tp


def generate_unit_hydrograph(tp, dt, duration, drainage_area_km2=None):
    """生成标准 NRCS PRF=484 曲线的离散单位线。

    `tp` 是从单位净雨开始到峰值的 Tp[h]，不是 watershed lag。
    `duration` 必须覆盖表 16-1 的完整 0–5Tp 退水段。未给面积时返回
    离散卷积权重（Σ=1）；给定面积时返回 m³/s per mm，并按离散积分严格
    保证 1 mm 净雨体积 A×10³ m³。表值舍入会使离散峰值与理论 PRF=484
    峰值有约 0.2% 的差异，这是表格精度而非再缩放依据。
    """
    tp = _validate_positive(tp, "tp")
    dt = _validate_positive(dt, "dt")
    duration = _validate_positive(duration, "duration")
    if dt > 0.1 * tp + 1e-12:
        raise ValueError("dt 必须不大于 0.1×tp，以保持表 16-1 的标准采样分辨率")
    if duration + 1e-12 < 5.0 * tp:
        raise ValueError("duration 必须至少为 5×tp，以覆盖 NRCS 表 16-1 的完整退水段")
    if drainage_area_km2 is not None:
        drainage_area_km2 = _validate_positive(drainage_area_km2, "drainage_area_km2")

    n_steps = int(math.ceil(duration / dt - 1e-12))
    time_h = np.arange(n_steps + 1, dtype=float) * dt
    shape = np.interp(
        time_h / tp,
        NRCS_484_TIME_RATIOS,
        NRCS_484_DISCHARGE_RATIOS,
        left=0.0,
        right=0.0,
    )
    total = float(np.sum(shape))
    if not math.isfinite(total) or total <= 0:
        raise ValueError("当前 dt 未解析出正的单位线纵坐标；请减小 dt")
    weights = shape / total
    if drainage_area_km2 is None:
        return weights
    return weights * drainage_area_km2 * 1000.0 / (dt * 3600.0)


def convolve_rainfall_runoff(net_rainfall, unit_hydrograph, full_output=False):
    """卷积模型网格上的净雨深增量[mm]与单位线[m³/s/mm]。"""
    net = _as_nonnegative_1d(net_rainfall, "net_rainfall")
    uh = _as_nonnegative_1d(unit_hydrograph, "unit_hydrograph")
    runoff = np.convolve(net, uh, mode="full")
    if not full_output:
        runoff = runoff[:len(net)]
    return runoff


def _align_unit_duration(dt_rain_h, target_h, *, lag_h=None, tp_h=None, explicit=False):
    """Align ΔD to the rainfall interval without confusing it with output `dt`."""
    target_h = _validate_positive(target_h, "unit_duration_h")

    def is_acceptable(duration_h):
        local_tp = tp_h if tp_h is not None else lag_h + 0.5 * duration_h
        return duration_h <= 0.25 * local_tp + 1e-12

    if explicit:
        ratio = dt_rain_h / target_h
        periods = int(round(ratio))
        if periods < 1 or not math.isclose(ratio, periods, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                "unit_duration_h 必须精确整除 dt_rain_h；否则需用 S 曲线构造任意历时单位线"
            )
        if not is_acceptable(target_h):
            raise ValueError("unit_duration_h 应不大于 0.25×Tp")
        return target_h, periods

    ratio = dt_rain_h / target_h
    lower = max(1, int(math.floor(ratio)))
    upper = max(1, int(math.ceil(ratio)))
    candidates = {lower, upper}
    valid = [
        (abs(dt_rain_h / count - target_h), count, dt_rain_h / count)
        for count in candidates
        if is_acceptable(dt_rain_h / count)
    ]
    if not valid:
        count = upper
        while not is_acceptable(dt_rain_h / count):
            count += 1
        valid.append((abs(dt_rain_h / count - target_h), count, dt_rain_h / count))
    _, periods, duration_h = min(valid)
    return duration_h, periods


def _resolve_timing(A, dt_rain_h, kwargs, professional, assumptions):
    """Resolve and align Tc, lag, ΔD and Tp without conflating them with `dt`."""
    tc_value = kwargs.get("tc")
    tp_value = kwargs.get("tp")
    unit_duration_value = kwargs.get("unit_duration_h")

    if tc_value is None and tp_value is None:
        if kwargs.get("L") is not None or kwargs.get("slope") is not None:
            tc_value = calculate_concentration_time(
                A,
                L=kwargs.get("L"),
                slope=kwargs.get("slope"),
                method="kirpich",
                allow_extrapolation=bool(kwargs.get("allow_kirpich_extrapolation", False)),
            )
        elif professional:
            raise ValueError(
                "CN 专业路径必须提供 tc(min)、tp(h)，或同时提供 Kirpich 的 L(km) 与 slope(m/m)"
            )
        else:
            tc_value = calculate_concentration_time(A, method="area_estimate")
            assumptions.append("Tc 使用 Tc=0.3*sqrt(A) h 的无来源面积估算，仅供粗略路径")

    if tc_value is not None:
        tc_min = _validate_positive(tc_value, "tc")
        lag_h = calculate_lag_time(tc_min)
        standard_duration_h = calculate_unit_duration(tc_min)
        target_duration_h = (
            standard_duration_h
            if unit_duration_value is None
            else _validate_positive(unit_duration_value, "unit_duration_h")
        )
        if unit_duration_value is not None and not math.isclose(
            target_duration_h, standard_duration_h, rel_tol=1e-6, abs_tol=1e-12
        ):
            assumptions.append("用户自定义 ΔD；未采用 NRCS 默认 ΔD=0.133Tc")
        unit_duration_h, unit_periods_per_rain = _align_unit_duration(
            dt_rain_h,
            target_duration_h,
            lag_h=lag_h,
            explicit=unit_duration_value is not None,
        )
        if not math.isclose(unit_duration_h, target_duration_h, rel_tol=1e-6, abs_tol=1e-12):
            assumptions.append(
                f"为使 ΔD 精确整除雨量时段，将 NRCS 目标 ΔD "
                f"从 {target_duration_h:.6g} h 对齐为 {unit_duration_h:.6g} h；"
                "这是已记录的离散化选择"
            )
        computed_tp = calculate_time_to_peak(tc_min, unit_duration_h)
        if tp_value is not None:
            tp_h = _validate_positive(tp_value, "tp")
            if not math.isclose(tp_h, computed_tp, rel_tol=1e-6, abs_tol=1e-9):
                raise ValueError("tp 与 Tp=lag+unit_duration_h/2 不一致")
        else:
            tp_h = computed_tp
        return (
            tc_min,
            lag_h,
            target_duration_h,
            unit_duration_h,
            tp_h,
            unit_periods_per_rain,
        )

    tp_h = _validate_positive(tp_value, "tp")
    if unit_duration_value is None:
        target_duration_h = 0.2 * tp_h
        unit_duration_h, unit_periods_per_rain = _align_unit_duration(
            dt_rain_h, target_duration_h, tp_h=tp_h, explicit=False
        )
        lag_h = tp_h - 0.5 * unit_duration_h
        tc_min = lag_h / 0.6 * 60.0
        assumptions.append(
            "仅给 Tp：以 ΔD≈0.2Tp 并结合雨量时段对齐反推 lag 与 Tc；"
            "这是工程桥接，不同时严格复现 ΔD=0.133Tc，严格 NRCS 时间关系应提供 Tc"
        )
        if not math.isclose(unit_duration_h, target_duration_h, rel_tol=1e-6, abs_tol=1e-12):
            assumptions.append(
                f"为使 ΔD 精确整除雨量时段，将目标 {target_duration_h:.6g} h "
                f"调整为 {unit_duration_h:.6g} h"
            )
    else:
        target_duration_h = _validate_positive(unit_duration_value, "unit_duration_h")
        unit_duration_h, unit_periods_per_rain = _align_unit_duration(
            dt_rain_h, target_duration_h, tp_h=tp_h, explicit=True
        )
        lag_h = tp_h - 0.5 * unit_duration_h
        if lag_h <= 0:
            raise ValueError("unit_duration_h 必须小于 2×tp")
        tc_min = lag_h / 0.6 * 60.0
        assumptions.append("tp 与 unit_duration_h 为用户给定；Tc 仅由 lag=0.6Tc 反推")
    return (
        tc_min,
        lag_h,
        target_duration_h,
        unit_duration_h,
        tp_h,
        unit_periods_per_rain,
    )


def _resolve_model_grid(tp_h, unit_duration_h, requested_dt):
    """Resolve output sampling `dt`; ΔD remains the unit-hydrograph shift."""
    if requested_dt is None:
        steps_per_unit = max(1, int(math.ceil(unit_duration_h / (0.1 * tp_h) - 1e-12)))
        return unit_duration_h / steps_per_unit, steps_per_unit
    dt = _validate_positive(requested_dt, "dt")
    if dt > 0.1 * tp_h + 1e-12:
        raise ValueError("dt 必须不大于 0.1×Tp，以保持表 16-1 的标准采样分辨率")
    ratio = unit_duration_h / dt
    steps_per_unit = int(round(ratio))
    if steps_per_unit < 1 or not math.isclose(ratio, steps_per_unit, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("dt 必须精确整除 unit_duration_h；dt 仅是输出采样，不是单位净雨历时")
    return dt, steps_per_unit


def analyze_flood_hydrograph(rainfall, runoff_coeff=None, A=None, **kwargs):
    """推算直接径流过程线，返回显式单位、假设和质量平衡诊断。

    输入 `rainfall` 是等时段雨强 [mm/h]，每段历时由 `dt_rain_h` 指定。
    给 `CN` 或 `land_use` 时采用 SCS-CN 累计雨深产流；否则采用常数径流
    系数的粗略净雨法。两条路径都使用 NRCS 表 16-1 单位线和完整退水卷积。

    NRCS 单位净雨历时 ΔD 与数值输出采样 `dt` 是两个不同概念：每个 ΔD
    净雨增量只在其时段起点施加一次单位线，过程线按 ΔD 平移；`dt` 仅用于
    采样单位线和输出过程线。若输入雨量时段比 ΔD 粗，默认假定时段内雨强
    均匀，并在 ΔD 网格上重新计算累计 SCS-CN 产流。
    """
    rain_intensity = _as_nonnegative_1d(rainfall, "rainfall")
    A = _validate_positive(A, "A")
    dt_rain_h = _validate_positive(kwargs.get("dt_rain_h", 1.0), "dt_rain_h")
    assumptions = []
    has_cn = kwargs.get("CN") is not None
    has_land_use = kwargs.get("land_use") is not None
    if has_cn and has_land_use:
        raise ValueError("CN 与 land_use 只能选择一种输入方式")
    professional = has_cn or has_land_use

    if has_cn:
        if kwargs.get("amc") is not None:
            raise ValueError("直接给定 CN 时应传入事件 CN；不要同时传 amc")
        CN = _validate_cn(kwargs["CN"], "CN")
        method_name = "scs_cn_direct"
    elif has_land_use:
        required = [name for name in ("hsg", "hydrologic_condition", "amc") if kwargs.get(name) is None]
        normalized_land_use = normalize_land_use(kwargs["land_use"])
        if normalized_land_use in {key[0] for key in CN_CULTIVATED} and kwargs.get("treatment") is None:
            required.append("treatment")
        if required:
            raise ValueError("land_use 专业路径缺少必填参数：" + ", ".join(required))
        CN = select_cn(
            land_use=kwargs["land_use"],
            hsg=kwargs["hsg"],
            hydrologic_condition=kwargs["hydrologic_condition"],
            treatment=kwargs.get("treatment", "straight"),
            crop_residue=kwargs.get("crop_residue", False),
        )
        CN = adjust_cn_for_amc(CN, kwargs["amc"])
        method_name = "scs_cn_land_use"
    else:
        runoff_coeff = _validate_finite(runoff_coeff, "runoff_coeff")
        if not 0 <= runoff_coeff <= 1:
            raise ValueError("runoff_coeff 必须在 [0, 1] 之间")
        # 常数径流系数与事件 CN 不是可互换参数；不得在主分析结果中伪造 CN。
        CN = None
        method_name = "runoff_coefficient_linear"
        assumptions.append("常数径流系数法不表示 SCS-CN 产流，需用实测资料校核")

    if professional and runoff_coeff is not None:
        assumptions.append("已提供 CN/land_use，runoff_coeff 未参与计算")

    (
        tc_min,
        lag_h,
        unit_duration_target_h,
        unit_duration_h,
        tp_h,
        unit_periods_per_rain,
    ) = _resolve_timing(A, dt_rain_h, kwargs, professional, assumptions)
    if kwargs.get("allow_kirpich_extrapolation", False) and not (
        KIRPICH_MIN_AREA_KM2 <= A <= KIRPICH_MAX_AREA_KM2
    ):
        assumptions.append("Kirpich 超出原始 1.25–112 acre 样本范围，结果需独立验证")
    dt, steps_per_unit = _resolve_model_grid(tp_h, unit_duration_h, kwargs.get("dt"))
    rain_depth_mm = rain_intensity * dt_rain_h
    rain_depth_unit_mm = np.repeat(
        rain_depth_mm / unit_periods_per_rain,
        unit_periods_per_rain,
    )
    if unit_periods_per_rain > 1:
        assumptions.append("输入雨强在每个 dt_rain_h 时段内按均匀强度分配到 ΔD 单元")

    lam = None
    if professional:
        region = kwargs.get("region")
        regional_advice = None
        if region is not None:
            regional_advice = initial_abstraction_ratio_for_region(region)
            if regional_advice is None:
                raise ValueError("高寒区冻融/积雪机制不符合本 SCS-CN 实现；请改用适宜模型")
        lam = _validate_lambda(kwargs.get("lam", 0.2))
        if not math.isclose(lam, 0.2, rel_tol=0.0, abs_tol=1e-12):
            assumptions.append(
                "λ!=0.2 是本地适配；NRCS CN 表基于 Ia=0.2S，必须联合重新率定 CN 与 λ"
            )
        elif regional_advice is not None and not math.isclose(regional_advice, 0.2):
            assumptions.append("区域文献建议未自动套用；当前保留 NRCS 标准 λ=0.2")
        p_cum = np.cumsum(rain_depth_unit_mm)
        q_cum = np.array([direct_runoff_mm(p, CN, lam) for p in p_cum], dtype=float)
        net_depth_unit = np.diff(np.concatenate(([0.0], q_cum)))
        if np.any(net_depth_unit < -1e-10):
            raise RuntimeError("累计产流非单调，输入或数值状态无效")
        net_depth_unit = np.maximum(net_depth_unit, 0.0)
    else:
        net_depth_unit = rain_depth_unit_mm * runoff_coeff

    # [NEH630-16] 每个单位净雨增量按 ΔD 平移同一条 ΔD-duration UH。
    # `dt` 仅是输出采样，因此在模型网格上，净雨只出现在每隔 ΔD 的时段起点。
    excess_depth_model = np.zeros(
        (len(net_depth_unit) - 1) * steps_per_unit + 1,
        dtype=float,
    )
    excess_depth_model[::steps_per_unit] = net_depth_unit
    unit_hydrograph = generate_unit_hydrograph(
        tp_h, dt, 5.0 * tp_h, drainage_area_km2=A
    )
    runoff = convolve_rainfall_runoff(excess_depth_model, unit_hydrograph, full_output=True)

    expected_volume_m3 = float(np.sum(net_depth_unit) * A * 1000.0)
    runoff_volume_m3 = float(np.sum(runoff) * dt * 3600.0)
    if expected_volume_m3 == 0:
        mass_balance_relative_error = 0.0 if runoff_volume_m3 == 0 else math.inf
    else:
        mass_balance_relative_error = abs(runoff_volume_m3 - expected_volume_m3) / expected_volume_m3
    if not math.isfinite(mass_balance_relative_error) or mass_balance_relative_error > 1e-10:
        raise RuntimeError("离散卷积未通过质量平衡检查")

    peak_idx = int(np.argmax(runoff))
    peak_flow = float(runoff[peak_idx])
    time_h = np.arange(len(runoff), dtype=float) * dt
    positive = np.flatnonzero(runoff > max(peak_flow * 1e-12, 0.0))
    last_positive_idx = int(positive[-1]) if positive.size else peak_idx
    qp_per_mm = calculate_peak_flow(A, tp_h, runoff_depth_mm=1.0)
    qp_per_10mm = calculate_peak_flow(A, tp_h, runoff_depth_mm=10.0)

    return {
        "method": method_name,
        "rainfall": rain_intensity.copy(),
        "rainfall_intensity_mm_h": rain_intensity.copy(),
        "rainfall_depth_mm": rain_depth_mm,
        "rainfall_depth_unit_mm": rain_depth_unit_mm,
        "net_rainfall": net_depth_unit,
        "net_rainfall_depth_mm": net_depth_unit,
        "net_rainfall_time_h": np.arange(len(net_depth_unit), dtype=float) * unit_duration_h,
        "excess_depth_on_model_grid_mm": excess_depth_model,
        "runoff": runoff,
        "time_h": time_h,
        "CN": CN,
        "lambda": lam,
        "tc": tc_min,
        "lag": lag_h,
        "unit_duration_target": unit_duration_target_h,
        "unit_duration": unit_duration_h,
        "tp": tp_h,
        "dt": dt,
        "dt_rain_h": dt_rain_h,
        "unit_periods_per_rainfall_interval": unit_periods_per_rain,
        "model_steps_per_unit_period": steps_per_unit,
        "substeps_per_rainfall_interval": unit_periods_per_rain * steps_per_unit,
        "Qp": qp_per_10mm,
        "Qp_per_mm": qp_per_mm,
        "peak_flow": peak_flow,
        "peak_index": peak_idx,
        "peak_time": peak_idx * dt,
        "peak_time_h": peak_idx * dt,
        "peak_modulus": peak_flow / A,
        "total_volume": expected_volume_m3,
        "runoff_volume": runoff_volume_m3,
        "mass_balance_relative_error": mass_balance_relative_error,
        "rise_duration": peak_idx * dt,
        "recession_duration": max(0.0, (last_positive_idx - peak_idx) * dt),
        "time_reference": "interval-start; each depth applies over the following interval",
        "assumptions": assumptions,
        "validation_level": (
            "software numerical checks against NRCS analytical references; "
            "not basin-calibrated or field-validated"
        ),
    }

# 测试代码
if __name__ == '__main__':
    import sys
    try:
        # Windows GBK 控制台下无法打印 ²/³ 等字符，统一按 UTF-8 输出
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

    # 示例数据
    rainfall = [2, 5, 8, 15, 20, 18, 12, 8, 5, 3, 2, 1, 0.5, 0.5, 0, 0]
    A = 32.5
    runoff_coeff = 0.25

    # 粗略径流系数示例显式提供 Tc；不再由面积静默推断专业汇流参数。
    result = analyze_flood_hydrograph(rainfall, runoff_coeff, A, tc=90.0)

    print("=" * 60)
    print("洪水过程线分析结果")
    print("=" * 60)
    print(f"流域面积: {A} km²")
    print(f"径流系数: {runoff_coeff}")
    print(f"计算方法: {result['method']}")
    print(f"汇流时间: {result['tc']:.1f} min")
    print(f"滞后时间: {result['lag']:.2f} h")
    print(f"单位线峰现时间 Tp: {result['tp']:.2f} h")
    print(f"过程线洪峰流量: {result['peak_flow']:.2f} m³/s")
    print(f"过程线峰现时间: {result['peak_time']:.2f} h")
    print(f"洪峰模数: {result['peak_modulus']:.3f} m³/s/km²")
    print(f"洪水总量: {result['total_volume']:.0f} m³")
    print("=" * 60)

    # 专业 CN 取值示例：按土地利用 × 水文土壤组 × 水文条件查 TR-55 表
    print("\n专业 CN 取值示例（TR-55 表，AMC II 基准）:")
    print("-" * 60)
    demo_rows = [
        ("林地", HSG_B, "good", "straight"),
        ("中耕作物", HSG_C, "poor", "contoured"),
        ("牧场/草地/放牧地", HSG_D, "fair", "straight"),
        ("商业区(85%不透水)", HSG_B, "good", "straight"),
        ("荒漠灌木(盐灌木/木馏油等)", HSG_A, "good", "straight"),
    ]
    for land_use, hsg, cond, treat in demo_rows:
        cn_ii = select_cn(land_use, hsg=hsg, hydrologic_condition=cond, treatment=treat)
        cn_i = adjust_cn_for_amc(cn_ii, "I")
        cn_iii = adjust_cn_for_amc(cn_ii, "III")
        print(f"{land_use:<18} {hsg}组 {cond:<4} CN(II)={cn_ii:<3} "
              f"CN(I)={cn_i:<3} CN(III)={cn_iii}")
    regional_advice = initial_abstraction_ratio_for_region("半干旱区")
    lam = 0.2
    cn = select_cn("草本植被(草/杂草/低灌丛)", hsg="B", hydrologic_condition="fair")
    print(f"\n半干旱区边界示例：文献建议 λ={regional_advice} 不自动套用；"
          f"未联合率定时保留 λ={lam}。草本植被 B组 中条件 CN={cn}, "
          f"λ={lam}, S={cn_to_s_mm(cn):.1f} mm, Ia={initial_abstraction_mm(cn, lam):.1f} mm, "
          f"P=30mm 时 Q={direct_runoff_mm(30, cn, lam):.1f} mm")
    print("=" * 60)
