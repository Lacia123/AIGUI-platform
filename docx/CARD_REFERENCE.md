# rl_orchestrator — 动作空间与卡片说明

> 配套阅读：[README.md](./README.md)（实验流程）  
> 卡片示例来源：`RL_env/data/`、`RL_env/docs/README_showcase_cards.md`、`RL_env/slab-comp.txt`  
> 分块选卡实现：`tools/md_cut.py`（`cut_for_rl` / `select_card_type_for_group`）

模型每步选一个 **mode**；mode 映射到 **card + layout**；槽位由 `fill.py` 规则填充。

> **注意**：动作维已变为 **12**（含 `markdown_passthrough`），旧 checkpoint 与 `OBS_DIM` 不兼容，需重新训练。

---

## 0. card 类型对齐（`md_cut` ↔ 本说明）

两边统一的 **card 类型名**如下（只关心类型名，不关心 layout / 填槽）：

| 类别 | card | 说明 |
|------|------|------|
| Slab ×9 | `targetStatCard` · `mistakesCard` · `showcaseCard` · `summaryCard` · `textCard` · `commonStyleServiceListDesc` · `pairedImageTextCard` · `heroCard` · `contentSummaryCard` | 进 L3 填槽 RL 的组件卡 |
| 透传 | `[table:commonStyle]` | 表格独占块；**无槽可填**，围栏 + 表原样输出，不进填槽 RL |
| 透传 | `__rawMarkdown__` | 复杂块原样 Markdown；对应 mode `markdown_passthrough` |
| 透传 | `Topology` | 知识图谱独占块；**独立 card**，不并入 `__rawMarkdown__`，也不占 RL mode 维 |

`Topology` 由解析器识别 `[Topology\|title=...]` + `@@@` 后在 `md_cut` 中单独成块；表格元素同样被拆成独立 `[table:commonStyle]` 块；`__rawMarkdown__` 用于其余复杂笔记/多结构块。三者均为透传伪卡，**互不归并**。

---

## 1. 动作空间总表（12 个 mode → Slab 组件卡 + 表格透传 + Markdown 透传）

> `contentSummaryCard` 已列入 §0 Slab 词表；本表 mode 维暂未单独占位，布局 RL 经 `card_types.TYPE_NAMES` 识别。

| id | mode | card | layout | 典型用途 |
|----|------|------|--------|----------|
| 0 | `stat_metric` | `targetStatCard` | default | 单一指标数字卡（可连续成 row） |
| 1 | `mistakes_list` | `mistakesCard` | with_title | 薄弱点 / 错题分级列表 |
| 2 | `showcase_preview` | `showcaseCard` | preview | 左文右图预览条 |
| 3 | `showcase_list` | `showcaseCard` | default | 图文/文件列表 |
| 4 | `summary_visual` | `summaryCard` | default | 摘要卡（可上图） |
| 5 | `text_note` | `textCard` | default | 笔记 / 长文 |
| 6 | `service_row` | `commonStyleServiceListDesc` | default | icon + 标题 + 描述行 |
| 7 | `table_block` | `[table:commonStyle]` | default | 表格块（无槽透传，不进 L3） |
| 8 | `paired_media` | `pairedImageTextCard` | default | 双图文并列 |
| 9 | `hero_block` | `heroCard` | default | 页头 Hero |
| 10 | `fallback_column` | `textCard` | fallback | 兜底文本卡 |
| 11 | `markdown_passthrough` | `__rawMarkdown__` | bare | 空白透传：原样 Markdown 直接进父 column（不用 `layout:row`） |

另：`Topology` 不在上表 mode 维中，由 `md_cut` 规则直接产出（见 §0 / §3.11）。`[table:commonStyle]` 虽对应 mode `table_block`，但与 Topology / `__rawMarkdown__` 一样**不进填槽 RL**（见 §3.7）。

定义见 `modes.py` 的 `MODE_TYPES` / `MODE_SPECS`。

---

## 2. action_mask：何时屏蔽某 mode

| 条件 | 屏蔽 |
|------|------|
| 无 table/chart | `table_block` |
| 不像指标块 | `stat_metric` |
| 不像错题块 | `mistakes_list` |
| 图片数 &lt; 2 | `paired_media` |
| 完全无图 | `showcase_preview` / `summary_visual` / `hero_block` |
| 内容偏长 | `stat_metric` / `showcase_preview` |
| 无图、无视频、无 icon | `service_row` |
| **非**复杂块（短且元素少） | `markdown_passthrough` |

`markdown_passthrough` 仅在以下之一时开放：

- `content_risk_long`
- `n_elements >= 6`
- `n_math >= 1`
- 有图且文本中等以上（`n_image >= 1` 且 `text_len_bucket >= 1`）

兜底：至少保留 `text_note` 与 `fallback_column`。

---

## 3. 各 card 最小示例（PSUIP）

### 3.1 `targetStatCard` ← `stat_metric`

```xml
<targetStatCard>
  <subtitle>FOR MAGGIE</subtitle>
  <title>Master Calculus in 14 Days.</title>
  <text>240</text>
  <caption>TOTAL PROBLEMS</caption>
</targetStatCard>
```

要点：`text` 是**关键数字**，不是正文。可选 `button`。

来源：`RL_env/docs/README_showcase_cards.md`

---

### 3.2 `mistakesCard` ← `mistakes_list`

```xml
<mistakesCard>
  <title>Weak Spots</title>
  <mistakesCardItem type="normal">
    <title>Multivariable Calculus</title>
    <text>38% Mastery</text>
    <caption>12 Mistakes</caption>
  </mistakesCardItem>
  <mistakesCardItem type="error">
    <title>Linear Algebra</title>
    <text>12% Mastery</text>
    <caption>28 Mistakes</caption>
  </mistakesCardItem>
</mistakesCard>
```

要点：`type` 为 `normal` / `warning` / `error` 三选一；本项目填槽时按掌握度从低到高映射。

来源：同上 docs

---

### 3.3 `showcaseCard` ← `showcase_preview` / `showcase_list`

**preview（左右布局，与默认中间区互斥）：**

```xml
<showcaseCard>
  <title>Related files</title>
  <preview src="https://example.com/preview.png"></preview>
  <caption>4 Images</caption>
</showcaseCard>
```

**default（列表）：**

```xml
<showcaseCard>
  <title>📁 Related files</title>
  <imageTextItem>
    <image src="https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1200&h=900" alt="..."></image>
    <title>Patent sharing collection</title>
    <text>14MB Sent by Professor Zhang</text>
  </imageTextItem>
  <commonListItem>
    <icon>📘</icon>
    <title>LSM AI notebooks</title>
    <text>Maggie created on July 18</text>
  </commonListItem>
  <caption>4 Related Files</caption>
</showcaseCard>
```

来源：`RL_env/data/showcase_classroom_dashboard.md`、docs

---

### 3.4 `summaryCard` ← `summary_visual`

```xml
<summaryCard>
  <topImage src="https://example.com/cover.png"></topImage>
  <title>生成岗位JD完成</title>
  <text>摘要正文……</text>
  <commitWide>查看过程</commitWide>
</summaryCard>
```

要点：`commit` 与 `commitWide` 互斥；`topImage` 与 `backgroundImage` 互斥。

来源：`RL_env/slab-comp.txt`

---

### 3.4.1 `contentSummaryCard`

内容摘要卡（与 `summaryCard` 区分：偏正文/要点汇总，而非带图摘要条）。

```xml
<contentSummaryCard>
  <title>本节要点</title>
  <text>关键概念与适用边界……</text>
</contentSummaryCard>
```

---

### 3.5 `textCard` ← `text_note` / `fallback_column`

```xml
<textCard>
  <text_title>限时</text_title>
  <text_subtitle>年终大促活动</text_subtitle>
  <text_text>联想、苹果和荣耀作为 AI-PC 市场的头部品牌……</text_text>
  <cta href="https://example.com/promo">按钮</cta>
</textCard>
```

要点：无**可重复**槽；`cta` 单例；`text_text` 可吸收多段进同一槽。

来源：`RL_env/slab-comp.txt`

---

### 3.6 `commonStyleServiceListDesc` ← `service_row`

```xml
<commonStyleServiceListDesc>
  <icon>📄</icon>
  <title>AWS</title>
  <desc>美国、亚洲、亚太</desc>
</commonStyleServiceListDesc>
```

来源：`RL_env/slab-comp.txt`

---

### 3.7 `[table:commonStyle]` ← `table_block`（表格透传，独立 card）

**不是** Slab 填槽卡：没有 `title` / `table` 等组件槽。解析出的 `table` 元素独占成块，输出围栏 + 原表 Markdown，**不进 L3 填槽 RL**（与 `Topology` / `__rawMarkdown__` 同类）。

源 Markdown 形态（解析器只吃管道表；围栏由 `md_cut` 还原）：

```markdown
[table:commonStyle]
| DingOS版本号 | 设备数量 | 操作 |
|------|------|------|
| AWS | 美国、亚洲、亚太 | ⟳  ⋮ |
| Azure | 全球20+区域 | ⟳  ⋮ |
| 阿里云 | 中国大陆主要城市 | ⟳  ⋮ |
```

| 项 | 说明 |
|----|------|
| 产出 | `md_cut.cut_for_rl` → `card_type=[table:commonStyle]`，表格元素单独成块 |
| 与 `__rawMarkdown__` | **独立类型**，有表时不并入 raw Markdown |
| 填槽 RL | 跳过（`PASSTHROUGH_CARDS` / `PASSTHROUGH_CARD_TYPES`） |
| 常量 | `tools.md_cut.TABLE_CARD` |

来源：`RL_env/slab-comp.txt`

---

### 3.8 `pairedImageTextCard` ← `paired_media`

```xml
<pairedImageTextCard>
  <title>致力于提供最先进的数字化解决方案</title>
  <content>我们围绕技术、团队与服务能力，为客户提供可持续的数字化支持。</content>
  <primaryItem>
    <image src="https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=1200&h=800" alt="企业" />
    <title>关于企业</title>
    <body>……</body>
  </primaryItem>
  <secondaryItem>
    <image src="https://images.unsplash.com/photo-1556761175-b413da4baf72?w=1200&h=800" alt="团队" />
    <title>关于团队</title>
    <body>……</body>
  </secondaryItem>
</pairedImageTextCard>
```

本项目填槽用拍平槽名：`primary_image` / `primary_title` / …

来源：`RL_env/slab-comp.txt`

---

### 3.9 `heroCard` ← `hero_block`

```xml
<heroCard>
  <cover_image src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1600&h=900"></cover_image>
  <badge>热门目的地</badge>
  <title>发现你的下一站旅行</title>
  <subtitle>个性化行程推荐，AI 智能规划。</subtitle>
  <metrics>⭐ 4.9 · 128K 用户</metrics>
  <cta_primary href="https://example.com/plan">开始计划</cta_primary>
  <cta_secondary href="https://example.com/destinations">查看目的地</cta_secondary>
</heroCard>
```

来源：`RL_env/slab-comp.txt`

---

### 3.10 `__rawMarkdown__` ← `markdown_passthrough`（空白透传）

**不是** Slab 组件卡：不填组件槽；还原块内原始 Markdown，**直接挂在父 `layout:column` 下**（不用 `layout:row`，避免 MD 被拆成多个 flex 子项）。

适用：笔记正文、引用、多小节+插图等塞进组件槽会丢结构或 uncovered 时。

```markdown
## Homogeneous Equations

When $f(x) = 0$, the equation is homogeneous.

![board](https://example.com/board.png)

- Real roots → exponential terms
- Complex roots → $e^{\alpha x}\cos(\beta x)$
```

| 项 | 说明 |
|----|------|
| fill | 单槽 `markdown`，`sources` 覆盖块内全部可覆盖元素 |
| render | `render_fill_snippet` → 仅输出原文 |
| validate | `markdown` 允许多 sources；缺正文 → hard `missing:markdown` |
| mask | 仅复杂块开放（见 §2） |

对齐人工：页头可用 `textCard`，其后笔记原样 Markdown。

`md_cut`：在专用结构卡（表格透传 / Topology / 指标 / 错题 / showcase / 双图等）未命中时，若块满足上述复杂条件，强规则选 `__rawMarkdown__`。

---

### 3.11 `Topology`（知识图谱透传，独立 card）

**不是** Slab 组件卡，也**不是** `__rawMarkdown__`：专用于解析器产出的 `topology` 元素独占块。

源 Markdown 形态：

```markdown
[Topology|title=示例知识图谱]
@@@
{"nodes":[{"id":"a","label":"概念A"}],"edges":[{"from":"a","to":"b"}]}
@@@
```

| 项 | 说明 |
|----|------|
| 产出 | `md_cut.cut_for_rl` → `card_type=Topology`，单独成块 |
| 与 `__rawMarkdown__` | **独立类型**，不合并、不互相替代 |
| RL mode | 不占用 12 维动作空间；分块后原样透传 |
| 常量 | `tools.md_cut.TOPOLOGY_CARD` / `PASSTHROUGH_CARD_TYPES` |

---

## 4. 本项目填槽主槽位（`schema.py`）

| card | 主要合法槽 |
|------|------------|
| `targetStatCard` | subtitle, title, text, caption, button |
| `mistakesCard` | title + `mistakesCardItem_{sev}_{field}` |
| `showcaseCard` | title/subtitle/caption/preview/… + list 子槽 |
| `summaryCard` | title, text, commit/commitWide, topImage, … |
| `contentSummaryCard` | title, text, … |
| `textCard` | text_title, text_subtitle, text_text, cta |
| `commonStyleServiceListDesc` | icon, title, desc |
| `[table:commonStyle]` | 无组件槽；整块原文透传（`[table:commonStyle]` 围栏 + 表） |
| `pairedImageTextCard` | title, content, primary_*, secondary_* |
| `heroCard` | cover_image, badge, title, subtitle, metrics, cta_* |
| `__rawMarkdown__` | markdown（整块原文） |
| `Topology` | 无组件槽；整块原文透传（`raw` / Topology 围栏） |

校验硬规则见 `validate.py`：合法槽、互斥、单例不重复、**可覆盖元素必须用尽**。

---

## 5. 相关文件

| 路径 | 内容 |
|------|------|
| `modes.py` | mode 列表、mask、规则选 mode |
| `fill.py` | 规则填槽（含 `_fill_markdown_passthrough`） |
| `schema.py` | 槽契约 |
| `render_psuip.py` | FillResult → PSUIP |
| `../tools/md_cut.py` | Markdown 分块 + card 类型判定（含 `Topology` / 表格 / `__rawMarkdown__` 透传） |
| `../RL_env/PSUIP代码生成提示词.md` | layout + Markdown 降级说明 |

---

## 6. 本地冒烟

```bash
python -m rl_orchestrator.demo_run eeeeee/math_final_dashboard.md

python temp_test/run_fill_random.py --illegal --html-check \
  --files data/knowledge_card data/schedule data/session_menu

# 解析 + 分块选卡（含 card_type）
python3.11 temp_test/markdown_p_pipline.py
```
