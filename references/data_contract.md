# v0.3.0 结构化水文时序数据契约

## 1. 目的与边界

该契约用于让 WorkBuddy 等 Agent 在调用事件水文模型前明确回答：数据测于何处、
来自何处、记录代表哪个时刻或时段、原单位是什么、哪些点可接受，以及模型实际
使用了哪一份输入。它是 hydro-analysis 的 strict JSON profile，不生成 WaterML
XML 或 CF-netCDF，因此不宣称 WaterML、CF、WMO 或测站行业规范符合性。

本契约只做可审计的时间/单位规范化与失败关闭校验，不执行缺测插补、时间重采样、
异常值修正、站点时区猜测或自动阈值判定。输入通过契约不代表数据已经完成测站
整编、流域率定、野外验证或工程审查。

## 2. 公共字段

结构化降雨 `rainfall_data` 和结构化实测流量 `observed_data` 均使用 data schema
`1.0`，顶层未知字段会失败关闭。

| 字段 | 要求 | 规则 |
|---|---|---|
| `schema_version` | 必填 | 当前只能为 `1.0` |
| `variable` | 必填 | 降雨为 `precipitation`；流量为 `discharge` |
| `value_type` | 必填 | 降雨为 `intensity` 或 `depth`；流量为 `instantaneous` |
| `unit` | 必填 | 必须来自第 4 节允许表 |
| `timestamps` | 必填 | 每点一个带 `Z` 或数值 UTC offset 的 ISO 8601 datetime |
| `time_reference` | 必填 | 降雨为 `interval_start` 或 `interval_end`；流量为 `instant` |
| `calendar` | 必填 | 当前只接受 `proleptic_gregorian` |
| `sampling` | 必填 | 降雨只接受 regular；流量接受 regular 或明确 irregular |
| `values` | 必填 | 有限、非负数值；不接受布尔值、`null`、NaN 或 Inf |
| `quality` | 必填 | 与 values 等长，每点显式标识 |
| `station` | 必填 | 至少包含 `station_id`；可附 `station_name/timezone/latitude/longitude/elevation_m` |
| `source` | 必填 | 至少包含 `provider/dataset_id/retrieved_at/processing_level` |
| `qc` | 必填 | 至少包含调用方明确选择的 `accepted_quality` |

数组必须非空且 `timestamps/values/quality` 等长。所有对象，包括 `sampling`、
`station`、`source` 和 `qc`，都会拒绝拼写错误或未声明字段。即使原始 JSON
number 有限，若单位换算、总量求和或 datetime 位移发生数值溢出，也会失败关闭；
这属于软件表示能力检查，不是自动异常阈值。

## 3. 时间语义

- 时间戳必须显式携带 `Z` 或 `+08:00` 等数值 offset；不把 naive datetime 当作
  本机时间，也不根据 `station.timezone` 猜测 offset。
- 所有时刻在比较和计算前转为 UTC，并保留原 offset 秒数和原始契约 hash。
- regular sampling 必须给 `sampling.interval_h > 0`，相邻时刻必须与该间隔一致；
  重复、倒序、重叠或间隙均失败，不插值或补零。
- `interval_start` 时间戳就是降雨时段起点；`interval_end` 会明确减去一个
  `interval_h` 转为起点。两种写法代表同一真实时段时，规范化雨量必须相同。
- irregular 仅允许用于瞬时实测流量；只检查时间严格递增，并明确记录无法仅凭
  声明判断记录间是否缺测。
- structured observed 按首个降雨时段起点换算模型相对时刻：
  `time_h = (t_obs_UTC - t_rain_start_UTC) / 3600`。

## 4. 单位与换算

| 变量 | 输入类型 | 允许单位 | 模型规范单位 |
|---|---|---|---|
| precipitation | intensity | `mm/h`, `mm/min`, `m/s`, `in/h` | `mm/h` 与每时段 `mm` |
| precipitation | depth | `mm`, `cm`, `m`, `in` | 每时段 `mm` 与等效 `mm/h` |
| discharge | instantaneous | `m3/s`, `L/s`, `ft3/s` | `m3/s` |

核心映射为：

- 雨强到雨深：`P_mm[i] = I_mm_h[i] * interval_h`；
- 雨深到雨强：`I_mm_h[i] = P_mm[i] / interval_h`；
- `L/s × 0.001 = m3/s`；
- `ft3/s × 0.028316846592 = m3/s`。

规范化记录换算因子、总雨深及软件质量平衡误差。原始 `input_sha256` 识别调用方
提交的精确 JSON 身份；`normalized_sha256` 只使用 UTC 时刻、规范单位数值、
规范化 QC、测站、来源和逐点质量。因此物理等价的雨强/雨深或流量单位表达具有
相同 normalized hash，但仍保留不同 raw input hash。`1e-12` 是浮点实现守恒门槛，
不是测量误差、站点精度或异常判别阈值。

## 5. 质量、来源与 QC

逐点 `quality` 只接受本地集合：`good`、`suspect`、`estimate`、`poor`、
`unchecked`。`qc.accepted_quality` 必须由调用方明确给出；某点不在接受集合时，
整个输入失败，程序不会静默删除或替换它。

`source.processing_level` 只接受 `raw`、`quality_controlled`、`derived`、
`synthetic`。这些标签描述来源方声明，软件不会把 `quality_controlled` 解释为
独立认证。

`qc.valid_min` 和 `qc.valid_max` 是可选的显式项目规则。只有调用方或数据提供方
给出时才检查；未给上限时结果记录 `upper_bound_check = NOT_CONFIGURED`。软件不
根据示例数据、区域经验或历史最大值自动发明雨量/流量上限。

## 6. 示例

```json
{
  "schema_version": "1.0",
  "variable": "precipitation",
  "value_type": "depth",
  "unit": "mm",
  "timestamps": [
    "2026-08-01T01:00:00+08:00",
    "2026-08-01T02:00:00+08:00"
  ],
  "time_reference": "interval_end",
  "calendar": "proleptic_gregorian",
  "sampling": {"type": "regular", "interval_h": 1.0},
  "values": [10.0, 20.0],
  "quality": ["good", "good"],
  "station": {
    "station_id": "P001",
    "station_name": "示例雨量站",
    "timezone": "Asia/Shanghai"
  },
  "source": {
    "provider": "example-provider",
    "dataset_id": "event-001",
    "retrieved_at": "2026-08-02T00:00:00Z",
    "processing_level": "quality_controlled"
  },
  "qc": {
    "accepted_quality": ["good"],
    "valid_min": 0.0,
    "valid_max": 300.0
  }
}
```

若要输入实测流量，把 `variable/value_type/unit/time_reference` 分别设置为
`discharge/instantaneous/m3/s/instant`（或采用允许的流量单位），并使用独立的
流量站与来源 metadata。`rainfall_data` 与 legacy `rainfall_mm_h` 互斥；
`observed_data` 与 legacy `observed` 互斥。

## 7. 输出追溯

structured 运行返回 result schema `1.2.0`，在 legacy 70 字段之外增加：

- `data_contract_schema_version`；
- `input_data_sha256`：降雨与可选实测流量规范化输入的组合 hash；
- `input_data_contract`：原始/规范化 hash、UTC 时间、单位转换、站点、来源和 QC
  摘要。

报告 summary 保留输入 hash、站点/来源 ID、事件 UTC 起点和 QC 检查状态；输出
manifest schema `1.1` 同时记录输入 hash，以及数据文件和 PNG/HTML/XLSX/DOCX
四件套中每个生成文件的 SHA-256。hash 用于
识别普通内容变化，不替代数字签名、原始数据库审计或法定资料认证。

## 8. 参考原则

- [CF Conventions 1.13：time coordinate 与 missing/valid-range metadata](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html)
- [OGC WaterML 2.0 Part 1：time series point metadata、quality、source 与 processing](https://docs.ogc.org/is/10-126r4/10-126r4.pdf)
- [ISO 8601 日期时间表示概述](https://www.iso.org/iso-8601-date-and-time-format.html)
- [WMO：水文监测资料、metadata 与可逆质量控制原则](https://wmo.int/media/magazine-article/5-essential-elements-of-hydrological-monitoring-programme)

上述来源用于约束本项目字段和失败关闭原则；本地 JSON profile 与这些标准并非
一一对应，实现通过测试也不等于标准符合性认证或专业数据验收。
