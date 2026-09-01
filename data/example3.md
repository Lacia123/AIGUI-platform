# 小尺寸网格示例

小尺寸容器（grid 显式指定 width=940px / height=1400px，对应实际业务中常见的半屏内容区），m×n 由 grid 自身尺寸推导：940px → 2 列（格子 ≈462px），1400px → 6 行（格子 ≈220px）。组件以 1×1 / 1×2 为主，通栏组件占 2×2。

<layout:grid width="940px" gap="16" height="1400px">

<!-- heroCard：通栏 2×2 -->
<grid:item x="1" y="1" width="9" height="24">
<heroCard>
  <cover_image src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1600&h=900"></cover_image>
  <badge>热门目的地</badge>
  <title>发现你的下一站旅行</title>
  <subtitle>个性化行程推荐，AI 智能规划，帮你找到更合适的旅程节奏。</subtitle>
  <metrics>⭐ 4.9 · 128K 用户</metrics>
  <metrics>🗺️ 320+ 城市灵感</metrics>
  <cta_primary href="https://example.com/plan">开始计划</cta_primary>
  <cta_secondary href="https://example.com/destinations">查看目的地</cta_secondary>
</heroCard>
</grid:item>

<grid:item x="1" y="3" width="1" height="1">
<summaryCard>
  <icon></icon>
  <title title="悬停显示完整标题">生成岗位JD完成</title>
  <commit>查看过程</commit>
  <text>已生成完整岗位说明，包含岗位职责、任职要求及加分项。</text>
</summaryCard>
</grid:item>

<grid:item x="2" y="3" width="1" height="1">
<metricCard>
  <status>NORMAL</status>
  <time_range>本月</time_range>
  <metric_label>学习清单</metric_label>
  <metric_value>4 模块 · 28 知识点</metric_value>
  <trend_value>+2</trend_value>
</metricCard>
</grid:item>

<!-- mistakesCard：小尺寸下 2 项，1×2 -->
<grid:item x="1" y="4" width="1" height="2">
<mistakesCard>
<title>Weak Spots</title>
<mistakesCardItem type="normal">
<title>Multivariable Calculus</title>
<text>38% Mastery</text>
<caption>12 Mistakes</caption>
</mistakesCardItem>

<mistakesCardItem type="error">
<title>Vector Spaces</title>
<text>31% Mastery</text>
<caption>15 Mistakes</caption>
</mistakesCardItem>
</mistakesCard>
</grid:item>

<!-- showcaseCard：按钮变体 1×2 -->
<grid:item x="2" y="4" width="1" height="2">
<showcaseCard>
<title>AI 摘要</title>
<toggle></toggle>
<text>联想 AI Now 是一款前沿的个人 AI 助手，可快速归纳会议要点。</text>
<loading></loading>
<button>✦ 查看 AI 摘要</button>
</showcaseCard>
</grid:item>

<!-- textCard：不带副标题（default 模式）可 1×1 -->
<grid:item x="1" y="6" width="1" height="1">
<textCard>
  <text_title>限时</text_title>
  <text_text>联想、苹果和荣耀作为 AI-PC 头部品牌。</text_text>
  <cta href="https://example.com/promo">按钮</cta>
</textCard>
</grid:item>

<grid:item x="2" y="6" width="1" height="1">
<summaryCard>
  <title title="任务状态">生成岗位JD完成</title>
  <commit>查看过程</commit>
  <text>基础纵向布局。</text>
</summaryCard>
</grid:item>
</layout:grid>