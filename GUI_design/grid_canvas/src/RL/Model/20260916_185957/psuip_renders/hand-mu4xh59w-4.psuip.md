<layout:grid width="4" gap="16" height="6">
<grid:item x="1" y="3" width="2" height="3">
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

<grid:item x="1" y="1" width="3" height="1">
  [table:commonStyle]
  | DingOS版本号 | 设备数量 | 操作 |
  |------|------|------|
  | AWS | 美国、亚洲、亚太 | ⟳  ⋮ |
  | Azure | 全球20+区域 | ⟳  ⋮ |
  | 阿里云 | 中国大陆主要城市 | ⟳  ⋮ |
  | 私有云 | 定制化部署 | ⟳  ⋮ |
</grid:item>
</layout:grid>
