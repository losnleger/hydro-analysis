# hydro-analysis

`hydro-analysis` 是一个面向 WorkBuddy 等 Agent 开发与运行的中文水文分析
skill，包含降雨—径流分析、NRCS/SCS-CN 与标准 PRF=484 单位线参考实现，
以及水文可视化规范。

## 当前范围

仓库目前包含：

- `SKILL.md`：面向 WorkBuddy 等 Agent 的技能说明；
- `scripts/scs_unit_hydrograph.py`：参考性的 Python 计算脚本（含基于
  USDA NRCS TR-55/NEH-630 的 CN、AMC、标准表 16-1 单位线、质量平衡诊断
  和专业降雨—径流绘图数据契约）；
- `scripts/generate_chart.py`：生成倒置总雨/净雨嵌套柱与向上流量过程线的
  专业静态 PNG；
- `agents/openai.yaml`：Agent UI 展示名、简述与默认调用提示；
- `references/visualization_standards.md`：降雨—径流图表规范。
- `references/scientific_method.md`：公式、单位、适用边界、修复前反例与验证证据。

当前版本已提供 PNG 图表生成器；`generate_report.py` 及 HTML、Word、Excel
导出器尚未实现。

## 安装与运行

需要 Python 3.9+、NumPy 和 Matplotlib：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\scs_unit_hydrograph.py
```

运行单元测试（开发依赖）：

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## 最小调用示例

```python
from scripts.scs_unit_hydrograph import (
    analyze_flood_hydrograph,
    prepare_precipitation_runoff_plot_data,
)

result = analyze_flood_hydrograph(
    rainfall=[20, 50, 10],  # 等时段雨强，mm/h
    dt_rain_h=1.0,
    A=1.0,                  # km²
    CN=70,                  # 当前场次 CN
    tc=60.0,                # min；也可直接给 Tp，或给 L+slope 使用 Kirpich
)

print(result["peak_flow"], result["peak_time_h"])
print(result["total_volume"], result["mass_balance_relative_error"])

# 供 Matplotlib/ECharts 绘制专业倒置雨量—径流组合图
plot = prepare_precipitation_runoff_plot_data(result)
```

生成静态专业图：

```python
from scripts.generate_chart import generate_precipitation_runoff_chart

generate_precipitation_runoff_chart(
    result,
    "outputs/precipitation_runoff_chart.png",
    dpi=300,
)
```

关键输入契约：

- `rainfall` 是雨强 `mm/h`；程序先乘 `dt_rain_h` 得到输入时段雨深，再按实际
  单位净雨历时 ΔD 划分。只有输入时段雨强时，明确假定该时段内雨强均匀，并在
  ΔD 边界重新计算累计 SCS-CN 产流；
- `tp` 表示单位线峰现时间 `Tp`，不是 watershed lag；返回值另含 `lag`；
- 只给 `tp` 时，程序采用 `ΔD≈0.2Tp` 的显式工程桥接并在 `assumptions` 中标记；
  它不同时严格复现 `ΔD=0.133Tc`。需要严格 NRCS 时间关系时应提供 `tc`；
- `ΔD=0.133Tc` 是 NRCS 目标值。默认会将 ΔD 对齐为 `dt_rain_h` 的精确约数并
  重新计算 `Tp`；结果同时返回 `unit_duration_target`、`unit_duration` 和调整假设。
  显式 `unit_duration_h` 若不能整除 `dt_rain_h`，则失败关闭；
- `dt` 只是过程线输出采样，必须精确整除实际 ΔD 且 `dt≤0.1Tp`。每个净雨增量
  按 ΔD 平移单位线，绝不能把同一条 ΔD-duration 单位线按每个 `dt` 重复施加；
- `time_h=0` 是第一个雨量时段起点，每个雨深作用于其后的时段；该约定也由
  `time_reference` 字段返回；
- 直接给 `CN` 时不需要无关的 `runoff_coeff`；按 `land_use` 查表时必须显式给出
  `hsg`、`hydrologic_condition`、`amc`，耕作地还需 `treatment`；
- CN 路径必须给 `tc`、`tp`，或同时给 Kirpich 的 `L` 与 `slope`。Kirpich 超出
  原始 1.25–112 acre 样本范围时默认失败关闭；
- `peak_flow` 是本场过程线实际洪峰，`Qp` 仍表示 10 mm 单位净雨的理论峰值。

专业图表默认使用同一连续时间轴：总雨蓝色宽柱与净雨橙色窄柱从顶部零线向下，
净雨水平居中嵌在总雨内部；流量从底部零线向上。helper 会把总雨和净雨统一为
同一 ΔD、同一单位并给出时段中心与柱宽，同时保留原始 `time_h` 流量过程。
默认禁止会改变洪峰的普通平滑插值。详细规则见
[`references/visualization_standards.md`](references/visualization_standards.md)。

## 科学边界

这是研究/示例用途的参考实现，不是经过流域率定、独立工程复核或主管部门审查的
设计软件。标准单位线已改为直接插值 USDA NRCS NEH-630 第 16 章表 16-1；
`lag=0.6Tc`、`ΔD=0.133Tc`、`Tp=ΔD/2+lag` 与 PRF=484 峰值换算均有官方
基准测试。代码还会检查非负/有限输入、ΔD 与输出采样网格、完整退水和离散质量平衡。

这些软件证据仍不等于现场适用性。CN 表基于 `Ia=0.2S`；若显式改用 `λ=0.05`，
必须联合重新率定 CN 与 λ。中国补充值、常数径流系数路径和面积估算 Tc 都是明确
标注的工程假设。仓库不附带真实流域数据，也不宣称现场校准、专业验收或设计许可。
请勿把示例输出直接用于防洪设计、调度或安全决策。

## 验证状态

当前测试覆盖 NRCS 表 16-1 全部纵坐标、NEH-630 第 16 章 Example 16-1、
Tc/lag/ΔD/Tp 关系、SCS-CN 公式、雨强到雨深换算、按 ΔD 平移单位线、相容网格
失败关闭、完整退水、质量守恒、异常输入，以及 PNG 的倒置雨轴、嵌套柱几何和
原始流量时序。验证等级为“官方解析基准 + 软件数值/渲染验证”；没有真实流域
过程数据、参数率定或独立专业审查，因此不是专业水文验证。

## 贡献与安全

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。不要
提交真实 DEM、坐标、降雨时序、API 密钥、个人数据或运行输出。

## 许可证

本项目采用 [MIT License](LICENSE)。脚本中的原作者署名保留；如需将本项目用于
工程决策，仍须完成独立的专业复核、率定和适用性审查。
