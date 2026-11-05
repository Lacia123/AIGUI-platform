# GUI_design2：可解释的自适应布局搜索

本目录为一组保持原始顺序的 Card 生成 `row` / `column` 布局树。当前只有
少量人工布局，因此实现不依赖神经网络或强化学习，而采用：

```text
Card-only PSUIP
      ↓
解析类型、文本量和元素数
      ↓
受约束 beam search 生成布局树
      ↓
几何展开与可解释评分
      ↓
Top-K AST + PSUIP
      ↓
记录人工选择，逐步积累真实数据
```

## 设计约束

- Card 顺序固定，不预测 Card ID。
- 每张 Card 恰好出现一次。
- 容器只能是 `row` 或 `column`。
- 非根容器至少有两个子节点。
- 相同方向容器不直接嵌套。
- 搜索限制最大深度（默认 5）和每个区间的候选数；剪枝一半名额给代理分
  最好的树、一半按顶层切法保多样性，避免同一切法的变体挤掉侧栏/画廊树。
- Card 超过 9 张时限深 4 层、Beam 收窄到 64，否则候选量指数膨胀。

因此搜索结果天然是合法布局，不需要通过训练学习语法。

## 目录

```text
tools_layout/
  domain.py       AST、Card、Canvas 和 PSUIP 渲染
  parser.py       Card-only PSUIP 解析与特征提取
  candidates.py   有序候选树 beam search
  geometry.py     布局树到 Card 矩形的递归展开
  scoring.py      可解释布局评分
  pipeline.py     Top-K 排序与结果写出
  evaluation.py   在已有 48 条布局上计算排名指标
  cli.py          命令行入口
  tests/          单元测试

src/data/         原始内容和 Card-only PSUIP
layout2data/      已有布局数据与后续人工选择记录
```

旧 Transformer、规则教师和 RL 相关实现已经移除。数据资产均保留。

## 快速使用

在 `GUI_design2` 目录运行：

```powershell
python -m tools_layout.cli generate `
  src/data/cards/math_final_dashboard.cards.psuip.md `
  --width 1440 `
  --height 900 `
  --top-k 3 `
  --output output/math-final
```

输出：

```text
output/math-final/
  candidates.json
  candidate-1.psuip.md
  candidate-2.psuip.md
  candidate-3.psuip.md
```

`candidates.json` 同时包含：

- 每个候选的 AST；
- 总分；
- 各项惩罚明细；
- 完整 PSUIP；
- `gridSequence`：量化到平台格子（228×216/16）的前端布局序列
  `grid:CxR;(w,h,x,y,type)...`，可直接粘贴到平台首页渲染；画布对不上
  平台格子时为 `null`。

分数越低越好。

## 评分含义

当前评分由以下可解释项组成：

- `overflow`：估计内容高度超过分配高度；
- `too_narrow`：Card 宽度低于该类型的建议最小宽度；
- `aspect_ratio`：图片、图表等视觉 Card 的宽高比偏差；
- `excess_space`：Card 获得明显过多的高度；
- `complexity`：容器数量过多；
- `depth`：嵌套超过三层；
- `row_mismatch`：长文本、表格类被强行塞入横排（Hero/showcase 横排是
  画廊与侧栏，不罚）；
- `mobile_row_root`：窄屏使用整页横排根布局；
- `header`：队首 `textCard` 没有通栏；
- `type_group`：连续同类 Card 没有成为同一容器的直接子节点（指标成行、
  错题成叠、画廊成排）；
- `thin_banner`：非标题/指标的大 Card 被压成通栏细条。

几何展开时每棵子树先保底最小宽高，剩余空间再按固有尺寸分配，不再按
比例把子块压到最小尺寸以下。

权重集中在 `tools_layout/scoring.py` 的 `ScoreWeights`，可以根据实际渲染
效果调整，而不需要重新训练模型。

## 记录人工选择

生成候选后可记录用户最终选择：

```powershell
python -m tools_layout.cli select `
  output/math-final/candidates.json `
  --rank 2 `
  --output layout2data/selections.jsonl
```

选择记录可用于后续学习排序。积累到数百条真实选择之前，不建议引入
LightGBM；积累到上千条完整布局之前，不建议重新引入 Transformer。

## 评估已有布局

```powershell
python -m tools_layout.cli evaluate
```

评估输出：

- `candidateCoverage`：人工树是否被候选生成器覆盖；
- `top1` / `top3` / `top5`：人工树的评分排名；
- `meanCoveredRank`：被覆盖样本的平均排名；
- `meanHumanScore` / `meanTop1Score` / `meanScoreGap`：人工树与 Top1 的
  评分差距，衡量评分与人工布局的对齐程度；
- `missingIds`：搜索空间未覆盖的样本；
- `uncoverableIds`：叶子顺序与空间顺序不一致等原因导致有序切分根本
  搜不到的样本，与 Beam 剪枝失败分开统计。

现有数据中的 Card 只有类型和简短 label，评估主要用于检查候选覆盖率与调整
基础评分；真正的视觉质量仍应通过浏览器渲染和用户选择验证。

## 测试

```powershell
python -m unittest discover -s tools_layout/tests -v
```

项目运行只需要 Python 3.11+ 标准库。
