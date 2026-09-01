# 网格布局演示：数学期末复习仪表盘

网格单位固定 i=456px / j=216px。grid 显式指定 width/height（width=1880px 对应 1920 画布内容区），m×n 由 grid 自身尺寸推导，不依赖容器；容器不是整数倍时，余数自动摊平到格子上（1880px 下恰好 4 列 × 3 行）。

## 6 块仪表盘（第一行 4 个 · 第二行 2 个大卡左右分）
<layout:grid width="1880px" gap="16" height="680px">
  <grid:item x="1" y="1" width="1" height="1">
    <metricCard>
      <status>ACTIVE</status>
      <time_range>本月</time_range>
      <metric_label>Learning inventory</metric_label>
      <metric_value>4 模块 · 28 知识点</metric_value>
      <trend_value>+2</trend_value>
    </metricCard>
  </grid:item>
  <grid:item x="2" y="1" width="1" height="1">
    <metricCard>
      <status>NORMAL</status>
      <time_range>历年</time_range>
      <metric_label>Past Exam Papers</metric_label>
      <metric_value>4 套</metric_value>
      <trend_value>+1</trend_value>
    </metricCard>
  </grid:item>
  <grid:item x="3" y="1" width="1" height="1">
    <metricCard>
      <status>ERROR</status>
      <time_range>本周</time_range>
      <metric_label>Error Collection</metric_label>
      <metric_value>32 题</metric_value>
      <trend_value>-5</trend_value>
    </metricCard>
  </grid:item>
  <grid:item x="4" y="1" width="1" height="1">
    <metricCard>
      <status>WARNING</status>
      <time_range>本月</time_range>
      <metric_label>Mock Self-test</metric_label>
      <metric_value>23 题</metric_value>
      <trend_value>+8</trend_value>
    </metricCard>
  </grid:item>
  <grid:item x="1" y="2" width="2" height="2">
    <metricCard>
      <status>PROGRESS</status>
      <time_range>复习进度</time_range>
      <metric_label>Review Progress</metric_label>
      <metric_value>68%</metric_value>
      <trend_value>+12%</trend_value>
      <chart_mini chart="bar" title="各章掌握度（%）">
        | 章节 | 掌握度 |
        |------|--------|
        | 数列的极限 | 82 |
        | 导数与微分 | 74 |
        | 积分应用 | 61 |
        | 常微分方程 | 55 |
      </chart_mini>
    </metricCard>
  </grid:item>
  <grid:item x="3" y="2" width="2" height="2">
    <metricCard>
      <status>WEAK</status>
      <time_range>薄弱分布</time_range>
      // <metric_label>Weak Spots</metric_label>
      <metric_value>3 项</metric_value>
      <trend_value>-3</trend_value>
      <chart_mini chart="pie" title="薄弱知识点占比">
        | 类型 | 占比 |
        |------|------|
        | 多元微积分 | 38% |
        | 线性代数 | 32% |
        | 向量空间 | 30% |
      </chart_mini>
    </metricCard>
  </grid:item>
</layout:grid>