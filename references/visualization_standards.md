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

### 1.1 核心设计原则

**双轴结构**：
- 上方X轴：降雨柱向下倒置
- 下方X轴：流量曲线向上延伸
- 左侧Y轴：降雨量（向下为正）
- 右侧Y轴：流量（向上为正）

**关键视觉特征**：
```
        时间轴(X轴) ────────────────────────
           ↓               ↓
总降雨  ██████████████████   ← 蓝色宽柱
净雨量      ██████████       ← 橙色窄柱（叠在蓝色内部）
           ↓               ↓
        ────────────────────────────────
       ↗      ↗       ↗       ↗          ← 流量曲线（向上）
```

### 1.2 配色规范

| 元素 | 颜色 | 透明度 | 说明 |
|------|------|--------|------|
| 总降雨柱 | #3498db | 0.75-0.8 | 蓝色，代表降雨总量 |
| 净雨量柱 | #e67e22 | 0.85-0.9 | 橙色，代表有效降雨 |
| 流量曲线 | #27ae60 | 1.0 | 绿色，代表径流 |
| 曲线阴影 | #27ae60 | 0.12-0.15 | 面积填充效果 |
| 背景色 | #ffffff | 1.0 | 纯白背景 |
| 网格线 | #f0f0f0 | 1.0 | 浅灰虚线 |
| 坐标轴 | #bdc3c7 | 1.0 | 浅灰色轴线 |

### 1.3 图表尺寸

| 用途 | 尺寸 | 分辨率 | 备注 |
|------|------|--------|------|
| 屏幕展示 | 1280×720 px | 96 dpi | 16:9比例 |
| 打印输出 | 2800×1575 px | 200 dpi | A4横向适配 |
| 嵌入报告 | 1800×1013 px | 150 dpi | Word兼容 |

### 1.4 ECharts实现要点

```javascript
// 核心配置
{
    xAxis: [
        // 上方X轴（降雨）
        {
            position: 'top',
            axisLabel: { show: false },  // 不显示刻度值
            axisLine: { show: true },
            axisTick: { show: true }
        },
        // 下方X轴（流量）
        {
            position: 'bottom',
            name: '时间(h)',
            nameLocation: 'middle'
        }
    ],
    yAxis: [
        // 左侧Y轴（降雨，倒置）
        {
            inverse: true,  // 关键：反转Y轴
            name: '降雨量(mm/h)'
        },
        // 右侧Y轴（流量）
        {
            name: '流量(m³/s)'
        }
    ],
    series: [
        // 总降雨柱
        {
            type: 'bar',
            barWidth: '40%',  // 宽柱
            itemStyle: { color: '#3498db' }
        },
        // 净雨量柱（叠在内部）
        {
            type: 'bar',
            barWidth: '20%',  // 窄柱
            itemStyle: { color: '#e67e22' }
            // 注意：必须与总降雨使用同一个xAxisIndex
        },
        // 流量曲线
        {
            type: 'line',
            smooth: true,
            yAxisIndex: 1,  // 使用右侧Y轴
            xAxisIndex: 1   // 使用下方X轴
        }
    ]
}
```

### 1.5 自定义渲染（实现柱子叠加）

如果ECharts默认并排显示，使用custom系列：

```javascript
function renderItem(params, api) {
    var categoryIndex = api.value(0);
    var value = api.value(1);
    var isNetRain = api.value(2);

    var pointTop = api.coord([categoryIndex, value]);
    var pointBottom = api.coord([categoryIndex, 0]);

    // 关键：不同宽度
    var barWidth = isNetRain ? 14 : 28;
    var barHalfWidth = barWidth / 2;

    var xCenter = pointTop[0];
    var yTop = pointTop[1];
    var yBottom = pointBottom[1];

    return {
        type: 'rect',
        shape: {
            x: xCenter - barHalfWidth,  // 居中对齐
            y: yTop,
            width: barWidth,
            height: yBottom - yTop
        },
        style: api.style(),
        z: isNetRain ? 2 : 1  // 净雨量在上层
    };
}
```

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
| PNG | precipitation_runoff_chart.png | 打印输出（200dpi） |
| DOCX | Flood_Hydrograph_Report.docx | 完整报告 |
| XLSX | Flood_Hydrograph_Report.xlsx | 数据存档 |

### 4.2 图片导出规范

```python
# matplotlib导出
plt.savefig('chart.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')

# ECharts截图（可选）
chart.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#fff'
})
```

## 5. 常见问题与解决方案

### Q1: 柱子并排显示，如何叠在内部？

使用custom系列自定义渲染，或确保两个bar系列使用相同的xAxisIndex和yAxisIndex，然后调整barWidth。

### Q2: 降雨柱向上而不是向下？

确保左侧Y轴设置 `inverse: true`。

### Q3: 流量曲线和降雨柱重叠？

确保流量曲线使用 `xAxisIndex: 1` 和 `yAxisIndex: 1`（右侧Y轴和下方X轴）。

### Q4: 打印时图表模糊？

确保导出PNG时设置 `dpi=200` 或 `pixelRatio=2`。

## 更新记录

- 2026-03-27: 初始版本，完整记录可视化标准
