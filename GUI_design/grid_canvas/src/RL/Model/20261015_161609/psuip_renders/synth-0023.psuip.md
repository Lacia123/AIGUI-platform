<layout:grid width="7" gap="16" height="3">
<grid:item x="1" y="1" width="4" height="1">
  <textCard>
    <text_title>0714 Advanced Mathematics</text_title>
    <text_subtitle>Room 401 · Professor Zhang</text_subtitle>
  </textCard>
</grid:item>

<grid:item x="5" y="1" width="1" height="2">
  <showcaseCard>
  <title>Related files</title>
  <subtitle>4 Related Files</subtitle>
  <imageTextItem>
  <image src="https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800&h=600" alt="Lecture slides"></image>
      <title>Lecture Slides - Ch7</title>
      <text>14MB · Sent by Professor Zhang</text>
  </imageTextItem>
  <commonListItem>
    <icon>📄</icon>
    <layout:column>
      <title>Definite Integral Notes.docx</title>
      <text>1.2MB · Sent by u0_a204</text>
    </layout:column>
  </commonListItem>
  <commonListItem>
    <icon>📊</icon>
    <layout:column>
      <title>Practice Problems.xlsx</title>
      <text>856KB · Sent by u0_a204</text>
    </layout:column>
  </commonListItem>
  <commonListItem>
    <icon>📕</icon>
    <layout:column>
      <title>Midterm Review.pdf</title>
      <text>2.3MB · Sent by u0_a204</text>
    </layout:column>
  </commonListItem>
  <caption>4 Files · Courseware & Homework</caption>
  </showcaseCard>
</grid:item>

<grid:item x="6" y="1" width="1" height="2">
  <targetStatCard>
    <subtitle>FOR MAGGIE</subtitle>
    <title>Master Calculus in 14 Days.</title>
    <text>240</text>
    <caption>TOTAL PROBLEMS</caption>
    <button nativeEvent="click" data="viewReport">查看报告</button>
  </targetStatCard>
</grid:item>

<grid:item x="7" y="1" width="1" height="2">
  ## Homogeneous Equations

  When $f(x) = 0$, the equation is homogeneous.

  - Real roots → exponential terms
  - Complex roots → $e^{\alpha x}\cos(\beta x)$
</grid:item>

<grid:item x="1" y="2" width="3" height="1">
  <summaryCard>
    <icon></icon>
    <title title="悬停显示完整标题">生成岗位JD完成</title>
    <commit>查看过程</commit>
    <text>已生成完整岗位说明，包含岗位职责、任职要求及加分项。</text>
  </summaryCard>
</grid:item>

<grid:item x="4" y="2" width="1" height="2">
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
