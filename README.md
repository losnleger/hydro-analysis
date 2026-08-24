# hydro-analysis v0.2.0

面向 WorkBuddy 等 Agent 的中文水文分析技能：降雨—径流分析（SCS-CN +
NRCS PRF=484 单位线）、基流、Muskingum 河道汇流、水库调洪（Modified
Puls），以及 PNG / HTML(ECharts) / Excel / Word 四件套报告输出。

> 授权限制以包内 LICENSE 为准。

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
# 内置演示算例（A=84km², CN=72, Tc=100min 完整五步链条）
python -X utf8 scripts/full_chain.pyc --demo --out outputs

# 自定义算例（JSON 配置，字段见 SKILL.md / scripts/full_chain.pyc --help）
python -X utf8 scripts/full_chain.pyc --config my_case.json --out outputs
```

输出（四件套 + 数据层）：

| 文件 | 说明 |
|------|------|
| `full_chain_chart.png` | 倒置雨量柱 + 入库/下泄双过程线（300 dpi） |
| `full_chain_chart.html` | ECharts 交互版 |
| `full_chain_data.xlsx` | 参数 / 完整链条逐时 / 水库曲线 / 调洪试算表 |
| `full_chain_report.docx` | 分节专业报告 |
| `*_full.json`、`*.csv` | 完整中间结果与序列数据 |

## 目录结构

```
hydro-analysis/
├── SKILL.md            # Agent 技能说明（方法学、调用规范、报告规范）
├── README.md           # 本文件
├── LICENSE             # 使用许可
├── CHANGELOG.md
├── requirements.txt
├── references/         # 方法学参考文档（开放）
└── scripts/            # 运行模块与命令行工具
```

## 方法与验证边界

计算方法与公式出处、单位约定、失败关闭规则见 `SKILL.md` 与
`references/scientific_method.md`。内置演示会输出各层质量平衡诊断；
v0.2.0 发布审计已在干净的 CPython 3.13.11 环境完成全链演示和四类文件
重开校验。但本包**未经真实流域率定或野外验证**，不能直接作为工程验收依据。
