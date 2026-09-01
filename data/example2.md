# 全组件类型网格示例

在弹性网格布局中展示全部组件类型。网格单位固定 i=456px / j=216px，每个 grid 显式指定 width/height，m×n 由 grid 自身尺寸推导（width=1880px 时 m=4），不依赖容器；容器不是整数倍时，余数自动摊平到格子上（格子 = i+δ）。

## 分区一 · 通栏 hero + 指标行（4×3）

<layout:grid width="1880px" gap="16" height="680px">

<!-- heroCard：cover_image / badge / title / subtitle / metrics / cta_primary / cta_secondary -->
<grid:item x="1" y="1" width="4" height="2">
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

<!-- 指标行：4 个 1×1 小卡（metricCard / summaryCard / textCard） -->
<grid:item x="1" y="3" width="1" height="1">
<metricCard>
  <status>NORMAL</status>
  <time_range>本月</time_range>
  <metric_label>Learning inventory</metric_label>
  <metric_value>4 模块 · 28 知识点</metric_value>
  <trend_value>+2</trend_value>
</metricCard>
</grid:item>

<grid:item x="2" y="3" width="1" height="1">
<summaryCard>
  <icon></icon>
  <title title="悬停显示完整标题">生成岗位JD完成</title>
  <commit>查看过程</commit>
  <text>已生成完整岗位说明，包含岗位职责、任职要求及加分项。</text>
</summaryCard>
</grid:item>

<!-- textCard：text_title / text_subtitle / text_text / cta -->
<grid:item x="3" y="3" width="1" height="1">
<textCard>
  <text_title>限时</text_title>
  <text_subtitle>年终大促活动</text_subtitle>
  <text_text>联想、苹果和荣耀作为 AI-PC 头部品牌。</text_text>
  <cta href="https://example.com/promo">按钮</cta>
</textCard>
</grid:item>

<grid:item x="4" y="3" width="1" height="1">
<summaryCard>
  <title title="任务状态">生成岗位JD完成</title>
  <commit>查看过程</commit>
  <text>请确保在截止日期前完成任务。</text>
</summaryCard>
</grid:item>
</layout:grid>

## 分区二 · 列表卡 + 双子卡 + 表格（4×6）

<layout:grid width="1880px" gap="16" height="1400px">

<!-- mistakesCard：title + mistakesCardItem（type=normal/warning/error） -->
<grid:item x="1" y="1" width="1" height="3">
<mistakesCard>
<title>Weak Spots</title>
<mistakesCardItem type="normal">
<title>Multivariable Calculus</title>
<text>38% Mastery</text>
<caption>12 Mistakes</caption>
</mistakesCardItem>

<mistakesCardItem type="warning">
<title>Linear Algebra</title>
<text>52% Mastery</text>
<caption>8 Mistakes</caption>
</mistakesCardItem>

<mistakesCardItem type="error">
<title>Vector Spaces</title>
<text>31% Mastery</text>
<caption>15 Mistakes</caption>
</mistakesCardItem>
</mistakesCard>
</grid:item>

<!-- showcaseCard：title / subtitle / toggle / caption + 列表子槽（imageTextItem / commonListItem） -->
<grid:item x="2" y="1" width="1" height="3">
<showcaseCard>
<title>相关文件</title>
<subtitle>4 个相关文件</subtitle>
<toggle></toggle>
<imageTextItem>
<image src="https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=1200&h=800" alt="企业会议与数字化方案讨论"></image>
    <title>专利分享合集</title>
    <text>14MB · 张教授发送</text>
</imageTextItem>
<commonListItem>
  <icon>📄</icon>
  <layout:column>
    <title>专利合集</title>
    <text>1 小时前 · Rebecca 发送</text>
  </layout:column>
</commonListItem>
<caption>4 张图片</caption>
</showcaseCard>
</grid:item>

<!-- targetStatCard：subtitle / title / text / caption / button（内容高，标准 1×2） -->
<grid:item x="3" y="1" width="1" height="2">
<targetStatCard>
  <subtitle>FOR MAGGIE</subtitle>
  <title>Master Calculus in 14 Days.</title>
  <text>240</text>
  <caption>TOTAL PROBLEMS</caption>
  <button nativeEvent="click" data="viewReport">查看报告</button>
</targetStatCard>
</grid:item>

<!-- __rawMarkdown__：整块原文透传（该组件类型尚未注册，当前按原文渲染） -->
<grid:item x="3" y="3" width="1" height="1">
<__rawMarkdown__>
整块原文透传：**粗体** 与 *斜体*
</__rawMarkdown__>
</grid:item>

<!-- showcaseCard：title / toggle / text / loading / button -->
<grid:item x="4" y="1" width="1" height="2">
<showcaseCard>
<title>AI 摘要</title>
<toggle></toggle>
<text>联想 AI Now 是一款前沿的个人 AI 助手，可快速归纳会议要点。</text>
<loading></loading>
<button>✦ 查看 AI 摘要</button>
</showcaseCard>
</grid:item>

<grid:item x="4" y="3" width="1" height="1">
<metricCard>
  <status>PROGRESS</status>
  <time_range>复习进度</time_range>
  <metric_label>Review Progress</metric_label>
  <metric_value>68%</metric_value>
  <trend_value>+12%</trend_value>
</metricCard>
</grid:item>

<!-- pairedImageTextCard：label / title / content + primaryItem / secondaryItem（图片 4:3，需 y=3） -->
<grid:item x="1" y="4" width="2" height="3">
<pairedImageTextCard>
  <label>公司简介</label>
  <title>致力于提供最先进的数字化解决方案</title>
  <content>我们围绕技术、团队与服务能力，为客户提供可持续的数字化支持。</content>
  <primaryItem>
    <image src="https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=1200&h=800" alt="企业会议与数字化方案讨论" />
    <title>关于企业</title>
    <body>我们是一家专注于人工智能和大数据领域的创新科技公司。</body>
  </primaryItem>
  <secondaryItem>
    <image src="https://images.unsplash.com/photo-1556761175-b413da4baf72?w=1200&h=800" alt="团队协作会议" />
    <title>关于团队</title>
    <body>我们拥有一支充满活力和创新精神的技术团队。</body>
  </secondaryItem>
</pairedImageTextCard>
</grid:item>

<!-- [table:commonStyle]：常规列表表格 -->
<grid:item x="3" y="4" width="1" height="2">
## 设备列表

[table:commonStyle]
| DingOS版本号 | 设备数量 | 操作 |
|------|------|------|
| AWS | 美国、亚洲、亚太 | ⟳  ⋮ |
| Azure | 全球20+区域 | ⟳  ⋮ |
| 阿里云 | 中国大陆主要城市 | ⟳  ⋮ |
| 私有云 | 定制化部署 | ⟳  ⋮ |
</grid:item>

<!-- summaryCard：topImage / icon / title / text / commitWide -->
<grid:item x="4" y="4" width="1" height="2">
<summaryCard>
  <topImage src="https://sop-cdn.dingcloud.com/aigui/file/rzrcm49z88yo6gnja2ehg7r87s9m72tt20260210101743900.png?w=200&h=200"></topImage>
  <icon></icon>
  <title title="标题提示">图片在上方的摘要卡</title>
  <text>顶部图片 + 底部宽按钮布局。</text>
  <commitWide>查看过程</commitWide>
</summaryCard>
</grid:item>

<!-- summaryCard：backgroundImage 变体 -->
<grid:item x="3" y="6" width="1" height="1">
<summaryCard>
  <backgroundImage src="https://sop-cdn.dingcloud.com/aigui/file/rzrcm49z88yo6gnja2ehg7r87s9m72tt20260210101743900.png?w=400&h=400"></backgroundImage>
  <title title="背景卡片标题">背景图摘要卡</title>
  <text>图片作为整卡背景。</text>
  <commitWide>查看过程</commitWide>
</summaryCard>
</grid:item>

<grid:item x="4" y="6" width="1" height="1">
<summaryCard>
  <title title="任务状态">生成岗位JD完成</title>
  <commit>查看过程</commit>
  <text>基础纵向布局。</text>
</summaryCard>
</grid:item>
</layout:grid>

## 分区三 · 知识图谱（4×3 通栏）

<layout:grid width="1880px" gap="16" height="680px">

<!-- Topology：无组件槽，整块原文透传（[Topology|title=...] + @@@ 围栏） -->
<grid:item x="1" y="1" width="4" height="3">
[Topology|title=导数与微分知识图谱]
@@@
{
  "nodes": [
    {"id":"Chapter:导数与微分","labels":["Chapter"],"props":{"name":"导数与微分","ord":1,"chapter":"第三章"}},
    {"id":"Topic:导数的概念","labels":["Topic"],"props":{"name":"导数的概念","ord":1}},
    {"id":"Topic:微分与近似","labels":["Topic"],"props":{"name":"微分与近似","ord":2}},
    {"id":"KP:导数的定义","labels":["KnowledgePoint"],"props":{"name":"导数的定义","ord":1}},
    {"id":"KP:基本求导法则","labels":["KnowledgePoint"],"props":{"name":"基本求导法则","ord":2}},
    {"id":"KP:链式法则","labels":["KnowledgePoint"],"props":{"name":"链式法则","ord":3}},
    {"id":"KP:隐函数求导","labels":["KnowledgePoint"],"props":{"name":"隐函数求导","ord":4}},
    {"id":"KP:微分定义","labels":["KnowledgePoint"],"props":{"name":"微分定义","ord":5}},
    {"id":"Example:幂函数求导","labels":["Example"],"props":{"name":"幂函数求导","ord":1}},
    {"id":"Example:复合函数求导","labels":["Example"],"props":{"name":"复合函数求导","ord":2}}
  ],
  "edges": [
    {"id":"e1","type":"HAS_TOPIC","source":"Chapter:导数与微分","target":"Topic:导数的概念","props":{"ord":1,"type":"direct"}},
    {"id":"e2","type":"HAS_TOPIC","source":"Chapter:导数与微分","target":"Topic:微分与近似","props":{"ord":2,"type":"direct"}},
    {"id":"e3","type":"HAS_KP","source":"Topic:导数的概念","target":"KP:导数的定义","props":{"ord":1}},
    {"id":"e4","type":"HAS_KP","source":"Topic:导数的概念","target":"KP:基本求导法则","props":{"ord":2}},
    {"id":"e5","type":"HAS_KP","source":"Topic:导数的概念","target":"KP:链式法则","props":{"ord":3}},
    {"id":"e6","type":"HAS_KP","source":"Topic:导数的概念","target":"KP:隐函数求导","props":{"ord":4}},
    {"id":"e7","type":"HAS_KP","source":"Topic:微分与近似","target":"KP:微分定义","props":{"ord":1}},
    {"id":"e8","type":"HAS_EXAMPLE","source":"KP:导数的定义","target":"Example:幂函数求导","props":{"ord":1}},
    {"id":"e9","type":"HAS_EXAMPLE","source":"KP:链式法则","target":"Example:复合函数求导","props":{"ord":1}},
    {"id":"e10","type":"PREREQUISITE","source":"KP:链式法则","target":"KP:基本求导法则","props":{}}
  ]
}
@@@
</grid:item>
</layout:grid>