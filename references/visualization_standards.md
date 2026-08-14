# 水文可视化图表标准

本文档详细描述专业水文降雨-径流图表的制作规范。

## 目录

- [1. 降雨-径流双轴图](#1-降雨-径流双轴图)
- [2. 数据表格规范](#2-数据表格规范)
- [3. 报告页面布局](#3-报告页面布局)
- [4. 导出格式](#4-导出格式)
- [5. 常见问题与解决方案](#5-常见问题与解决方案)
- [更新记录](#更新记录)

## 1. 降雨-径流双轴图

### 1.1 专业图式

默认使用单窗双 Y 轴组合图，形态与常用水文降雨—径流过程图一致：

```text
            时间 (h) —— 单一共享连续时间轴，置顶
0 ─────────────────────────────────────────  降雨零线
      ███████      █████████                 总降雨：宽柱，向下
        ███          █████                   净雨：窄柱，同中心嵌套
                         ● 真实洪峰
                     ／   ＼                  流量：向上、完整退水
0 ─────────────────────────────────────────  流量零线
```

- 左 Y 轴是倒置雨量轴，0 在顶部；右 Y 轴是正常流量轴，0 在底部。
- 总降雨和净雨从同一个雨量零线起画。所谓“嵌套”仅指水平方向同中心、净雨柱
  更窄且位于上层；不得并排、相加堆叠、垂直居中或从总雨柱底部起画。
- 流量过程线和雨柱必须使用同一个连续时间坐标范围。雨量结束后仍显示完整退水。
- 图题必须写真实方法，例如“SCS-CN + NRCS PRF=484”，不得照抄参考图中的
  “Nash Model”等不相符名称。

### 1.2 数据、单位和时标契约

先对 `analyze_flood_hydrograph()` 结果调用：

```python
plot = prepare_precipitation_runoff_plot_data(result)
```

默认返回同单位的总雨强和净雨强：

```text
total_intensity = rainfall_depth_unit_mm / ΔD   [mm/h]
net_intensity   = net_rainfall_depth_mm / ΔD    [mm/h]
bar_center      = interval_start + ΔD/2          [h]
```

如需画时段雨深，传 `rainfall_display="depth"`，总雨和净雨必须同时使用
`mm/ΔD`。严禁把输入总雨强 `mm/h` 与净雨深 `mm` 直接叠在同一轴上。

| 绘图字段 | 含义 |
|----------|------|
| `rainfall_time_center_h` | 每个 ΔD 雨量时段的中心时刻 |
| `total_rainfall` | 与净雨同单位的总降雨 |
| `net_rainfall` | 与总雨同单位的有效降雨 |
| `total_bar_width_h` | `0.80ΔD` |
| `net_bar_width_h` | `0.45ΔD` |
| `flow_time_h` | 原模型连续时间，不得改成类别索引 |
| `flow_m3_s` | 未经绘图平滑修改的流量过程 |

绘图前必须满足：数组有限、非负、雨量时间从 0 起按 ΔD 递增，且同一时段
`0 ≤ net_rainfall ≤ total_rainfall`。`time_h=0` 是第一个雨量时段起点；柱子
位于时段中点，不能误画在时段起点。

### 1.3 坐标与几何

- X 轴使用数值/时间轴，不用可能造成错位的独立类别轴。主时间轴置顶并显示
  “时间 (h)”。若版式同时显示底轴，必须与顶轴共享同一范围、刻度和变换。
- X 轴范围至少覆盖 `max(最后一个雨量时段终点, flow_time_h[-1])`。
- 左雨量轴倒置；标签只能是 helper 返回的 `rainfall_axis_label`。
- 右流量轴单位固定为 `m³/s`，0 在底部，最大值留出约 10%–15% 标注空间。
- 总雨柱和净雨柱使用相同 `rainfall_time_center_h`，各自采用 helper 返回的
  小时宽度；净雨层级高于总雨，流量线层级高于面积填充。
- 洪峰箭头只能指向真实 `peak_time_h/peak_flow_m3_s`。

### 1.4 线型、配色和可访问性

| 元素 | 颜色 | 透明度/线型 | 层级 |
|------|------|-------------|------|
| 总降雨柱 | `#5B9BD5` | 0.75–0.80，宽柱 | 2 |
| 净雨柱 | `#ED7D31` | 0.88–0.92，窄柱 | 3 |
| 流量曲线 | `#27AE60` | 2.5–3 px 实线 | 5 |
| 曲线填充 | `#27AE60` | 0.10–0.15 | 1 |
| 网格线 | `#E5E7EB` | 浅灰虚线 | 0 |

默认使用原始折线，设置 `smooth: false`。三次样条、Bezier 或普通平滑可能移动
峰现时间、产生峰值过冲或负流量；除非使用形状保持插值并明确标注，否则禁止。
灰度打印时给总雨柱加浅边框、净雨柱加深边框或纹理，不能只依赖颜色区分。

### 1.5 ECharts 实现骨架

使用一个共享的 value 型 X 轴；雨柱用 custom 系列，以“小时”为实际宽度：

```javascript
function rainRect(params, api) {
  const t = api.value(0), rain = api.value(1), widthH = api.value(2);
  const p0 = api.coord([t, 0]);
  const p1 = api.coord([t, rain]);
  const x0 = api.coord([t - widthH / 2, 0])[0];
  const x1 = api.coord([t + widthH / 2, 0])[0];
  return {
    type: 'rect',
    shape: {
      x: x0,
      y: Math.min(p0[1], p1[1]),
      width: x1 - x0,
      height: Math.abs(p1[1] - p0[1])
    },
    style: api.style()
  };
}

const option = {
  xAxis: {type: 'value', position: 'top', name: '时间 (h)'},
  yAxis: [
    {type: 'value', inverse: true, name: plot.rainfall_axis_label},
    {type: 'value', name: '流量 (m³/s)'}
  ],
  series: [
    {name: '总降雨', type: 'custom', renderItem: rainRect, yAxisIndex: 0,
     data: totalRainData, z: 2},
    {name: '净雨', type: 'custom', renderItem: rainRect, yAxisIndex: 0,
     data: netRainData, z: 3},
    {name: '流量', type: 'line', yAxisIndex: 1, data: flowData,
     smooth: false, showSymbol: false, z: 5}
  ]
};
```

Matplotlib 采用同一 X 轴的 `twinx()`；雨轴执行 `invert_yaxis()`，柱宽直接使用
helper 返回的小时值，流量用 `plot(flow_time_h, flow_m3_s)`，不得另行平滑。

### 1.6 图表尺寸与导出

| 用途 | 尺寸 | 分辨率 | 备注 |
|------|------|--------|------|
| 屏幕展示 | ≥1280×720 px | 96–144 dpi | 16:9，自适应 |
| 打印输出 | ≥3840×2160 px | 300 dpi | A4横向适配 |
| 嵌入报告 | ≥1800×1013 px | 200 dpi | 保持文字可读 |

### 1.7 出图验收清单

- [ ] 降雨向下、流量向上，两个零点位置正确。
- [ ] 总雨和净雨同单位、同 ΔD、同中心，净雨窄柱完整位于总雨宽柱内。
- [ ] X 轴为连续小时，雨柱位于时段中心，流量使用原 `time_h`。
- [ ] 流量未被普通平滑改变，洪峰标注等于计算结果。
- [ ] 完整退水未被雨量序列长度截断。
- [ ] 图题方法、轴单位、图例、时标约定均与本次计算一致。
- [ ] 灰度打印和 300 dpi 输出仍可辨认。

## 2. 数据表格规范

### 2.1 表格样式

```css
/* 表头 */
thead tr {
    background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
    color: #fff;
}

/* 时间列 */
.time-cell {
    background: #ecf0f1;
    font-weight: 600;
}

/* 数据列配色 */
.rain-cell { color: #3498db; }
.net-cell { color: #e67e22; }
.flow-cell { color: #27ae60; font-weight: 600; }

/* 洪峰行高亮 */
.peak-row {
    background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%);
}

/* 悬停效果 */
tbody tr:hover {
    background: #e8f4fc;
}
```

### 2.2 双列布局

将16个时段数据分为两列展示：

```
| 时段 | 降雨 | 净雨 | 流量 | 时段 | 降雨 | 净雨 | 流量 |
|------|------|------|------|------|------|------|------|
|  0   |  2   | 0.5  | 0.00 |  8   |  5   | 1.25 | 95.86|
|  1   |  5   | 1.25 | 0.01 |  9   |  3   | 0.75 | 53.21|
| ...  | ...  | ...  | ...  | ...  | ...  | ...  | ...  |
```

### 2.3 洪峰标注

在第6时段（洪峰）添加峰值标签：

```html
<span class="peak-badge">峰值</span>
```

```css
.peak-badge {
    background: linear-gradient(135deg, #f39c12, #e67e22);
    color: #fff;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    margin-left: 5px;
}
```

## 3. 报告页面布局

### 3.1 整体结构

```
┌─────────────────────────────────────┐
│           页面头部（渐变背景）         │
│   标题 + 副标题 + 元信息卡片           │
├─────────────────────────────────────┤
│                                      │
│           图表区域                    │
│      （16:9比例，520px高）            │
│                                      │
├─────────────────────────────────────┤
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐   │
│  │卡片1│ │卡片2│ │卡片3│ │卡片4│   │
│  └─────┘ └─────┘ └─────┘ └─────┘   │
├─────────────────────────────────────┤
│           数据表格                    │
│      （双列布局，洪峰高亮）            │
├─────────────────────────────────────┤
│              页脚                     │
│    方法说明 | 生成信息                 │
└─────────────────────────────────────┘
```

### 3.2 统计卡片

```html
<div class="stat-card blue">
    <div class="stat-label">总降雨量</div>
    <div class="stat-value">100.0<span class="stat-unit">mm</span></div>
</div>
```

四个卡片配色：
- 卡片1（总降雨）：蓝色边框
- 卡片2（净雨量）：橙色边框
- 卡片3（洪峰流量）：绿色边框
- 卡片4（峰现时间）：紫色边框

## 4. 导出格式

### 4.1 文件清单

| 格式 | 文件名 | 用途 |
|------|--------|------|
| HTML | precipitation_runoff_chart.html | 交互式展示 |
| PNG | precipitation_runoff_chart.png | 打印输出（300dpi） |
| DOCX | Flood_Hydrograph_Report.docx | 完整报告 |
| XLSX | Flood_Hydrograph_Report.xlsx | 数据存档 |

### 4.2 图片导出规范

```python
# matplotlib导出
plt.savefig('chart.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')

# ECharts截图（可选）
chart.getDataURL({
    type: 'png',
    pixelRatio: 3,
    backgroundColor: '#fff'
})
```

## 5. 常见问题与解决方案

### Q1: 柱子并排显示，如何叠在内部？

使用 1.5 节的 custom 系列；两组数据必须使用相同的时段中心和 Y 轴，分别采用
`total_bar_width_h` 与 `net_bar_width_h`，不要依赖默认 bar 自动排布。

### Q2: 降雨柱向上而不是向下？

确保左侧Y轴设置 `inverse: true`。

### Q3: 流量曲线与雨柱时间错位？

只使用一个共享的 value 型 X 轴。雨柱用 `rainfall_time_center_h`，流量用
`flow_time_h`；不能把两者分别放到未绑定的类别轴。

### Q4: 打印时图表模糊？

确保导出 PNG 时设置 `dpi=300` 或 `pixelRatio=3`。

### Q5: 净雨柱看起来比总雨柱还长？

通常是把总雨强 `mm/h` 与净雨深 `mm` 混在了一起。必须使用
`prepare_precipitation_runoff_plot_data()` 同时转换两者；函数还会拒绝
`净雨>总雨` 的非物理嵌套数据。

### Q6: 平滑后洪峰比计算结果高或峰现时间变了？

关闭 `smooth/spline/bezier`，直接绘制 `flow_time_h` 与 `flow_m3_s`。洪峰标注
必须来自 helper 返回的真实峰值，不能从平滑后的显示曲线重新求取。

## 更新记录

- 2026-03-27: 初始版本，完整记录可视化标准
- 2026-08-14: 按专业倒置雨量—径流组合图强化同单位 ΔD 数据契约、连续时间轴、
  嵌套柱几何、禁止失真平滑和 300 dpi 出图验收规则
