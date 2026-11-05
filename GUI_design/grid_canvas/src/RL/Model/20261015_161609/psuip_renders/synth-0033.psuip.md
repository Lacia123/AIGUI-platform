<layout:grid width="6" gap="16" height="4">
<grid:item x="1" y="1" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="2" y="1" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="3" y="1" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="4" y="1" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="5" y="1" width="2" height="3">
  <contentSummaryCard>
    <coverImage src="https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&h=600" alt="Whiteboard capture"></coverImage>
    <title>Smart Camera</title>
    <description>4 Images captured · Whiteboard 1: Bayes' theorem proof</description>
    <primaryAction>查看全部 4 张</primaryAction>
  </contentSummaryCard>
</grid:item>

<grid:item x="1" y="3" width="3" height="1">
  <textCard>
    <text_title>0714 Advanced Mathematics</text_title>
    <text_subtitle>Room 401 · Professor Zhang</text_subtitle>
  </textCard>
</grid:item>

<grid:item x="4" y="3" width="1" height="2">
  ## Homogeneous Equations

  When $f(x) = 0$, the equation is homogeneous.

  - Real roots → exponential terms
  - Complex roots → $e^{\alpha x}\cos(\beta x)$
</grid:item>

<grid:item x="1" y="4" width="3" height="1">
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
</layout:grid>
