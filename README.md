# hydro-analysis

`hydro-analysis` 是一个面向 WorkBuddy 等 Agent 开发与运行的中文水文分析
skill，包含降雨—径流分析、SCS 单位线计算说明和水文可视化规范。

## 当前范围

仓库目前包含：

- `SKILL.md`：面向 WorkBuddy 等 Agent 的技能说明；
- `scripts/scs_unit_hydrograph.py`：参考性的 Python 计算脚本；
- `references/visualization_standards.md`：降雨—径流图表规范。

原技能说明中提到的 `generate_chart.py` 和 `generate_report.py` 尚未实现，
因此当前版本不提供 HTML、PNG、Word 或 Excel 导出器。

## 安装与运行

需要 Python 3.9+ 和 NumPy：

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

## 科学边界

这是研究/示例用途的参考实现，不是经过率定、独立复核或工程审查的设计软件。
当前代码中的经验参数、Kirpich 汇流时间单位约定、单位线形状、洪峰缩放和体积
换算都需要使用者结合原始资料核验。仓库不附带真实流域数据，也不宣称现场校准、
专业验收或设计许可。请勿把示例输出直接用于防洪设计、调度或安全决策。

本次发布前只修复了两个不改变核心方程的可运行性问题：默认计算时段与
`SKILL.md` 的 `Δt = 0.133 × tp` 保持一致，以及使用 NumPy 安全地定位洪峰；
这不等于数值方法已经完成科学验证。输入、单位、守恒和敏感性仍需独立检查。

## 验证状态

当前 CI/本地测试仅覆盖语法、函数接口、有限值和示例 smoke test。没有官方基准、
专业实测数据或独立率定结果，因此验证等级是“有限 smoke/numerical validation”，
不是专业水文验证。

## 贡献与安全

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。不要
提交真实 DEM、坐标、降雨时序、API 密钥、个人数据或运行输出。

## 许可证

本项目采用 [MIT License](LICENSE)。脚本中的原作者署名保留；如需将本项目用于
工程决策，仍须完成独立的专业复核、率定和适用性审查。
