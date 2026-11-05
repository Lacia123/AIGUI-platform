<layout:grid width="6" gap="16" height="4">
<grid:item x="1" y="1" width="6" height="1">
  <textCard>
    <text_title>0714 Advanced Mathematics</text_title>
    <text_subtitle>Room 401 · Professor Zhang</text_subtitle>
  </textCard>
</grid:item>

<grid:item x="1" y="2" width="2" height="3">
  <mistakesCard>
  <title>Weak Spots</title>
  <mistakesCardItem type="normal">
  <title>Multivariable Calculus</title>
  <text>38% Mastery</text>
  <caption>12 Mistakes</caption>
  </mistakesCardItem>
  </mistakesCard>
</grid:item>

<grid:item x="3" y="2" width="2" height="3">
  <mistakesCard>
  <title>Weak Spots</title>
  <mistakesCardItem type="normal">
  <title>Multivariable Calculus</title>
  <text>38% Mastery</text>
  <caption>12 Mistakes</caption>
  </mistakesCardItem>
  </mistakesCard>
</grid:item>

<grid:item x="5" y="2" width="2" height="3">
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
