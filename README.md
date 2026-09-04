# hydro-analysis v0.3.2

面向 WorkBuddy 等 Agent 的中文水文分析技能：降雨—径流分析（SCS-CN +
NRCS PRF=484 单位线）、基流、Muskingum 河道汇流、水库调洪（Modified
Puls），以及 PNG / 单文件离线 HTML / Excel / Word 四件套报告输出。

v0.3.0 增加严格的结构化降雨和实测流量入口：时间戳、时区、时段定义、单位、
逐点质量标识、测站和数据来源均须明确给出，并在结果与报告中保留输入摘要和
SHA-256；输出 manifest 同时覆盖数据文件和四件套报告。缺测、重复/倒序时间、
未知字段、非法单位和未接受的质量标识会直接
失败；程序不会静默插补、重采样、猜测时区或虚构通用异常阈值。

v0.3.1 在该数据契约上增加显式多事件数据集：事件边界必须由用户给出并对齐
雨量时段，`calibration / validation / blind` 三个集合严格分开，validation 和
blind 只能持前一阶段生成的模型锁运行。每场输出 NSE、KGE-2009、KGE-2012、
MAE 等诊断及事件等权汇总；不会拼接长短不同事件，也不会按单场 NSE/KGE 自动
选择“最佳模型”。本版本没有参数优化，`calibration` 表示率定资料分区的固定
模型评估，而不是自动率定器。

v0.3.2 修复独立河道路由时间步的完整传播：显式 `routing_dt_h` 后，流量、时间、
洪量、洪峰、退水和水库层均使用实际网格。守恒重采样按区间起点平均流量的
`sum(Q) * dt` 契约保留完整末时段；水库显式 `dt_h` 必须与上游实际步长一致，
不一致时直接失败，不会被静默忽略或自动采用未经定义的跨语义重采样。

项目采用 [MIT License](LICENSE)，作者与保留署名见 [NOTICE](NOTICE)。

## 环境要求

| 依赖 | 要求 |
|------|------|
| Python | **CPython 3.13.x** |
| 第三方库 | 见 `requirements.txt`（numpy / matplotlib / openpyxl / python-docx） |

安装依赖：

```bash
pip install -r requirements.txt
```

## 安装（WorkBuddy）

解压本包到用户技能目录（文件夹名保持 `hydro-analysis`）：

```
~/.workbuddy/skills/hydro-analysis/
```

重启会话后 Agent 即可按 `SKILL.md` 自动调用。

## 命令行运行

```bash
# 查看候选版本
python -X utf8 scripts/full_chain.py --version

# 内置演示算例（A=84km², CN=72, Tc=100min 完整五步链条）
python -X utf8 scripts/full_chain.py --demo --out outputs

# 自定义算例（JSON 配置，字段见 SKILL.md / scripts/full_chain.py --help）
python -X utf8 scripts/full_chain.py --config my_case.json --out outputs
```

### 结构化降雨输入（v0.3.0）

结构化路径适合需要可追溯时间、测站、来源和 QC 状态的场景。以下为最小的
等时段雨强示例；`timestamps` 表示各雨量时段的起点：

```json
{
  "area_km2": 84.0,
  "rainfall_data": {
    "schema_version": "1.0",
    "variable": "precipitation",
    "value_type": "intensity",
    "unit": "mm/h",
    "timestamps": [
      "2026-08-01T00:00:00+08:00",
      "2026-08-01T01:00:00+08:00"
    ],
    "time_reference": "interval_start",
    "calendar": "proleptic_gregorian",
    "sampling": {"type": "regular", "interval_h": 1.0},
    "values": [10.0, 20.0],
    "quality": ["unchecked", "unchecked"],
    "station": {"station_id": "P001", "timezone": "Asia/Shanghai"},
    "source": {
      "provider": "example-provider",
      "dataset_id": "event-001",
      "retrieved_at": "2026-08-02T00:00:00Z",
      "processing_level": "quality_controlled"
    },
    "qc": {"accepted_quality": ["unchecked"]}
  },
  "loss": {"method": "scs_cn", "parameters": {"CN": 72.0}},
  "transform": {
    "method": "nrcs_uh_484",
    "parameters": {"tc_min": 100.0, "dt_h": 0.02}
  },
  "baseflow": {"method": "none", "parameters": {}},
  "reach_routing": {"method": "none", "parameters": {}},
  "reservoir": {"method": "none", "parameters": {}}
}
```

雨量也可按时段雨深输入，实测流量可用 `observed_data` 输入；完整字段、允许单位、
`interval_start/interval_end` 含义与失败关闭规则见
`references/data_contract.md`。`qc.valid_min` / `qc.valid_max` 只有在测站制度、数据
提供方或项目规则明确给出时才使用；未给上限会记录 `NOT_CONFIGURED`，不会自动
判定极端暴雨或洪水为异常。

### 显式多事件隔离（v0.3.1）

多事件入口复用上述 `rainfall_data` / `observed_data`，另给稳定事件 ID、带 offset
的 `[start,end)` 边界和 role。三个分区均至少一场，所有正雨量时段必须恰好属于
一场；事件外零雨时段可排除并计数。程序不自行发明 dry-gap、雨量阈值或事件窗。

```bash
# 1. 验证、规范化和切分（不运行模型）
python -X utf8 scripts/event_workflow.py prepare --dataset events.json --out prepared.json

# 2. 固定配置评估率定分区
python -X utf8 scripts/event_workflow.py evaluate --dataset prepared.json \
  --config model.json --area-km2 84 --role calibration --out calibration.json

# 3. 由率定结果签发 validation 锁；validation 完成后以同样方式签发 blind 锁
python -X utf8 scripts/event_workflow.py lock --dataset prepared.json \
  --config model.json --prerequisite-run calibration.json \
  --target validation --out validation-lock.json
python -X utf8 scripts/event_workflow.py evaluate --dataset prepared.json \
  --config model.json --area-km2 84 --role validation \
  --lock validation-lock.json --out validation.json
```

完整 schema、退化指标语义、阶段顺序和专业边界见
`references/event_workflow.md`。

### 独立河道路由时间步（v0.3.2）

`reach_routing.parameters.routing_dt_h` 可与转换层 `dt` 不同。路由前会把上游
等间隔过程按时段体积守恒映射到目标网格；目标总历时不能整除源总历时时，最后
一个目标时段只在越过源时域的部分补零，不外推流量。最终 `time_h`、洪峰和退水
字段使用河道/水库实际网格；顶层 `dt` 仍表示转换层输出采样步长，实际路由步长
记录在 `layer_outputs.reach_routing.inputs.dt_h`。

水库调洪继续使用节点流量和梯形连续方程。若提供
`reservoir.parameters.dt_h`，它必须等于上游实际步长；本版本不自动把河道的时段
平均流量转换为另一水库节点网格。需要不同水库步长时，应先在外部按经审查的
边界转换方法准备入流，不得依赖静默重采样。

输出（四件套 + 数据层）：

| 文件 | 说明 |
|------|------|
| `full_chain_chart.png` | 倒置总雨/净雨 + 最终模拟流量；完整调洪演示为入库/下泄双过程线（300 dpi） |
| `full_chain_chart.html` | 内联 SVG 单文件离线图，无 CDN 或外部资源依赖 |
| `full_chain_data.xlsx` | 参数、时序和适用于当前模型组合的专业工作表 |
| `full_chain_report.docx` | 与实际方法链一致的分节专业报告 |
| `*_full.json`、`*.csv` | 完整中间结果与序列数据 |

## 目录结构

```
hydro-analysis/
├── SKILL.md            # Agent 技能说明（方法学、调用规范、报告规范）
├── README.md           # 本文件
├── LICENSE             # 使用许可
├── NOTICE              # 作者与署名信息
├── CHANGELOG.md
├── requirements.txt
├── references/         # 方法学参考文档（开放）
└── scripts/            # 运行模块与命令行工具
```

## 方法与验证边界

计算方法与公式出处、单位约定、失败关闭规则见 `SKILL.md` 与
`references/scientific_method.md`；结构化时序输入见
`references/data_contract.md`，多事件隔离见 `references/event_workflow.md`。
内置演示会输出各层质量平衡诊断。v0.3.2 保持既有水文公式、legacy 70 字段、
structured 73 字段和多事件冻结基线不变；本次只修复显式独立路由网格路径及其
失败关闭边界。
这里的“离线”仅指安装后的 HTML 生成与重开，不包含依赖安装。
**未经真实流域率定、测站资料审核或野外验证**，本工具不能直接作为工程验收依据。
