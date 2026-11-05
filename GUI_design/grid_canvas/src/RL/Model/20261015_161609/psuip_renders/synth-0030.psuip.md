<layout:grid width="3" gap="16" height="6">
<grid:item x="1" y="1" width="3" height="1">
  <textCard>
    <text_title>0714 Advanced Mathematics</text_title>
    <text_subtitle>Room 401 · Professor Zhang</text_subtitle>
  </textCard>
</grid:item>

<grid:item x="1" y="2" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="2" y="2" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="3" y="2" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="1" y="4" width="3" height="1">
  <heroCard>
    <cover_image src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1600&h=900"></cover_image>
    <badge>热门目的地</badge>
    <title>发现你的下一站旅行</title>
    <subtitle>个性化行程推荐，AI 智能规划，帮你找到更合适的旅程节奏。</subtitle>
    <metrics>⭐ 4.9 · 128K 用户</metrics>
    <cta_primary href="https://example.com/plan">开始计划</cta_primary>
    <cta_secondary href="https://example.com/destinations">查看目的地</cta_secondary>
  </heroCard>
</grid:item>

<grid:item x="1" y="5" width="1" height="2">
  [Topology|title=导数与微分知识图谱]
  @@@
  {
    "nodes": [
      {"id":"Chapter:导数与微分","labels":["Chapter"],"props":{"name":"导数与微分"}},
      {"id":"Topic:导数的概念","labels":["Topic"],"props":{"name":"导数的概念"}},
      {"id":"KP:导数的定义","labels":["KnowledgePoint"],"props":{"name":"导数的定义"}}
    ],
    "edges": [
      {"id":"e1","type":"HAS_TOPIC","source":"Chapter:导数与微分","target":"Topic:导数的概念"},
      {"id":"e2","type":"HAS_KP","source":"Topic:导数的概念","target":"KP:导数的定义"}
    ]
  }
  @@@
</grid:item>

<grid:item x="2" y="5" width="2" height="1">
  <summaryCard>
    <icon></icon>
    <title title="悬停显示完整标题">生成岗位JD完成</title>
    <commit>查看过程</commit>
    <text>已生成完整岗位说明，包含岗位职责、任职要求及加分项。</text>
  </summaryCard>
</grid:item>
</layout:grid>
