# v0.3.1 显式多事件与分阶段评价契约

## 1. 能力与边界

该工作流把同一流域的结构化降雨和实测流量按用户给出的事件边界切为
`calibration`、`validation`、`blind` 三个互斥集合。它用于固定模型配置的分阶段
诊断和数据泄漏防护，不执行参数优化，也不根据 NSE、KGE 或其他单个指标自动
选择“最佳模型”。每场仍是独立事件模拟，事件间不传递土壤含水、基流、积雪或
其他连续状态。

本版不提供自动事件识别。dry-gap、最小场次雨量、雨强阈值和前后无雨窗具有区域、
资料分辨率和研究目的依赖性；没有明确来源与敏感性分析时，程序不会自行猜测。

## 2. event-dataset 1.0

顶层只接受以下必填字段，未知字段失败关闭：

| 字段 | 含义 |
|---|---|
| `schema_version` | 固定为 `1.0` |
| `dataset_id` | 稳定、非空的数据集 ID |
| `basin_id` | 稳定、非空的流域 ID |
| `rainfall_data` | `references/data_contract.md` 的完整 precipitation 契约 |
| `observed_data` | 同一文档的完整 discharge 契约 |
| `events` | 显式事件数组 |
| `segmentation` | 显式切分方法和边界语义 |

每个 `events[]` 只允许：

```json
{
  "event_id": "E-001",
  "start_utc": "2026-08-01T00:00:00+08:00",
  "end_utc": "2026-08-01T12:00:00+08:00",
  "role": "calibration"
}
```

`event_id` 全局唯一；事件按起点严格递增且不得重叠。role 只能是
`calibration`、`validation`、`blind`，三个集合均至少一场。边界采用
`[start,end)`，必须显式携带 `Z` 或数值 UTC offset，并与规范化雨量时段边界
精确对齐，因此不会切开一个雨量记录或在相邻事件间重复计数。

`segmentation` 固定为：

```json
{
  "method": "explicit_boundaries",
  "boundary_semantics": "[start,end)",
  "parameters": {}
}
```

每场至少包含一个正雨量时段和两个区间内实测点。所有正雨量时段必须恰好属于
一场；事件外零雨时段允许存在并被计数。事件外正雨量、少观测点、边界未对齐、
重复 ID、空分区和未知字段均直接失败，不插补、重采样或自动扩窗。

## 3. 指标定义

模拟流量只线性插值到同一事件的观测时刻，评价两者时间重叠段；不重采样观测，
也不把多个事件首尾拼成一条长序列。

设 `s`、`o` 分别为同一组时刻的模拟和实测流量：

- `KGE-2009 = 1 - sqrt((r-1)^2 + (alpha-1)^2 + (beta-1)^2)`；
  `alpha=std(s)/std(o)`，`beta=mean(s)/mean(o)`；
- `KGE-2012 = 1 - sqrt((r-1)^2 + (gamma-1)^2 + (beta-1)^2)`；
  `gamma=CV(s)/CV(o)`；
- `MAE_m3_s = mean(abs(s-o))`。

观测均值、观测标准差或模拟标准差恰为零时，KGE 所需分量不可定义；输出为
`None` 和具体 status，不写 NaN/Inf，也不加入任意 epsilon。KGE 不继承 NSE=0
的“以观测均值为基准”解释，不能把二者阈值直接互换。

跨事件只对每场已经算出的标量指标做等权 `mean/median/min/max`，并记录定义成功
场数。长事件不会因观测点更多而获得更大权重；汇总仍是诊断，不是自动选模规则。

## 4. 阶段顺序和模型锁

固定模型配置的标准顺序为：

1. `prepare` 只验证、规范化、切片和生成数据身份，不运行模型；
2. calibration 可无锁运行；
3. 由 calibration run 生成 validation 锁；
4. validation 只能用该锁和完全一致的数据集、切分、模型配置及面积运行；
5. 由 validation run 生成 blind 锁；
6. blind 只能使用该锁运行，其结果不得回流更新参数或重新生成 validation 锁。

锁记录 dataset normalized hash、split hash、config hash、面积、前置 run hash 和目标
事件 ID。任一不一致都会失败关闭。hash 用于内容身份和工作流误用防护，不是数字
签名、权限系统或独立数据托管；有意伪造仍需外部版本库、只读存储或组织审计控制。

## 5. 命令行

```bash
python -X utf8 scripts/event_workflow.py prepare \
  --dataset events.json --out prepared.json

python -X utf8 scripts/event_workflow.py evaluate \
  --dataset prepared.json --config model.json --area-km2 84 \
  --role calibration --out calibration.json

python -X utf8 scripts/event_workflow.py lock \
  --dataset prepared.json --config model.json \
  --prerequisite-run calibration.json --target validation \
  --out validation-lock.json

python -X utf8 scripts/event_workflow.py evaluate \
  --dataset prepared.json --config model.json --area-km2 84 \
  --role validation --lock validation-lock.json --out validation.json
```

validation 完成后以其 run 生成 `--target blind` 锁，再运行 blind。CLI 使用严格
JSON：重复键、NaN/Inf、schema 拼写错误或不受支持字段都会失败关闭。

## 6. 验证等级

本地自动测试验证公式手算值、JSON/schema、边界、hash、阶段顺序、软件守恒和
源码/原生结果等价，最高为 L2。没有真实流域多事件率定、跨时期独立预测检验、
测站资料认证或外部专业审查，因此不构成 L4/L5、工程模型验收或设计成果审定。

主要公式/流程来源：Gupta et al. (2009), DOI
`10.1016/j.jhydrol.2009.08.003`；Kling et al. (2012), DOI
`10.1016/j.jhydrol.2012.01.011`；Willmott & Matsuura (2005), DOI
`10.3354/cr030079`；Klemes (1986), DOI `10.1080/02626668609491024`。
