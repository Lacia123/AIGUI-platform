<layout:grid width="3" gap="16" height="6">
<grid:item x="1" y="1" width="3" height="1">
  <textCard>
    <text_title>0714 Advanced Mathematics</text_title>
    <text_subtitle>Room 401 · Professor Zhang</text_subtitle>
  </textCard>
</grid:item>

<grid:item x="1" y="2" width="3" height="1">
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

<grid:item x="1" y="3" width="3" height="2">
  <summaryCard>
    <icon></icon>
    <title title="悬停显示完整标题">生成岗位JD完成</title>
    <commit>查看过程</commit>
    <text>已生成完整岗位说明，包含岗位职责、任职要求及加分项。</text>
  </summaryCard>
</grid:item>
</layout:grid>
