# Layout RL

顺序网格布局：给定画布与 **card type 队列**，逐步预测每张卡的 `(w, h)`。
环境每步选择空白区最上方一行的最左空格作为左上锚点，卡片向右、向下扩展。
输入不含尺寸提示或专家坐标；专家完整框仅用于训练奖励和评估。

```
RL/
  config.py          # 超参、路径、layout-check 开关
  env.py             # Gym 环境（状态机）
  layout.py          # 动作编解码 / 掩码 / 观测
  reward.py          # compute_reward 分项
  policy.py          # CNN + 卡片 Transformer 特征
  card_types.py      # 类型词表与观测 State 契约
  data.py            # 读 data/*.jsonl
  layout_check.py    # 内容尺寸：layout-check（够不够）/ growth-check（最小尺寸）
  psuip_content.py   # 从源稿切裸 PSUIP
  train.py           # MaskablePPO 训练 + 评估
  test_model.py      # 加载权重评估
  test_state_obs.py  # 观测 shape / 无专家泄漏测试
  data/              # jsonl 数据集
  Model/             # 训练输出 Model/<时间戳>/
  tools/             # 数据导出与格式工具
```

## 任务与接口

| 项 | 说明 |
|------|------|
| 动作 | 离散 `(w,h)`；`x,y` 由左上空白锚点确定；mask 过滤越界/碰撞、长宽比超过 3:1 的细长条、按剩余卡目标面积预留空格；首张 `textCard` 强制通栏且高1～2格 |
| 观测 | 见下方「观测 State」 |
| 终止 | 全部放完 → `terminated`；连续非法 / 无合法动作 → `truncated` |
| 奖励 | 面积份额、终局空白、终局整页成行/分割线复用，三项同量级；不再给恒定 +100；专家模仿、`packability`、逐步邻卡对齐、`layout_wh` 与 `logic` 均关闭 |

训练期 `expert_x/y/w/h` 只进奖励；`build_obs()` 不读取专家几何。

## 观测 State

**约束**：expert `(x,y,w,h)` **永不**进入 observation。

| 键 | 形状 | 含义与归一化 |
|----|------|----------------|
| `spatial` | `(7, MAX_ROWS, MAX_COLS)` | 占用、已放类型、页内掩码、左右/向下连续空闲、当前左上锚点 |
| `cards` | `(MAX_CARDS, 19)` | 原字段外增加从该卡起连续同类型段长度；未放几何为 0 |
| `grid` | `(5,)` | `cols_n, rows_n, free_ratio, remain_count/max_cards, progress` |
| `cursor` | `(1,)` | 归一化进度 `cursor/total_cards` ∈ `[0,1]` |

策略侧：卡片 Transformer（3 层）+ 画布 embedding + 当前卡对棋盘的 cross-attention；融合为 5-token 混合 + 2 块残差 MLP。同类型靠序列角色与内容特征区分。

训练采样：卡多 / 小屏 / `1/sqrt` 稀有棋盘（上限 5）/ 同型异布局 / 易堵死页 / 尺寸易打偏页加权。
评估：面积占比误差、成行率、空白率、1×1 数量。训练默认在线抽样序列，synth 只作 held-out；先用 Beam Search 行为克隆，再用 PPO。推理默认策略引导 Beam Search。训练结束额外跑 `EVAL_EXTRA_SOURCES`。

数据 clean schema v3：

- `card_queue: [{id,type,label?,psuip?}]`：模型输入，不含几何。
- `expert_cards: [{id,x,y,w,h}]`：训练答案，不进入 State。

观测 schema v5，动作改为左上锚点 `(w,h)`。旧 checkpoint（含右上锚点）不兼容，必须重训。

## 安装与训练

```powershell
cd GUI_design\grid_canvas\src
pip install -r RL\requirements.txt
python -m RL.train
# 或
python -m RL
```

常用超参在 `config.py`：

- `SOURCE`：训练数据（默认 `all` = sample + handcrafted）
- `EVAL_EXTRA_SOURCES`：训练结束额外评估源（当前 `testdata`，4×6 手工页）
- `TIMESTEPS` / `N_ENVS`：总训练量（默认 50 万步；更新次数 ≈ TIMESTEPS/(N_STEPS×N_ENVS)）
- `N_EPOCHS` / `LEARNING_RATE` / `ENT_COEF` / `TARGET_KL` / `N_STEPS` / `BATCH_SIZE` …：PPO 与网络超参
- `TRAIN_LOG_EVERY_EPISODES` / `TRAIN_LOG_EVERY_UPDATES`：训练中详细日志频率
- `LAYOUT_CHECK_*` / `GRID_GROWTH_CHECK_URL`：单卡内容尺寸接口（默认连 `http://localhost:3001`）

奖励权重在 `reward.py` 顶部常量。训练中打印 `[train:ep]` / `[train:reward]` / `[train:update]`，并写入 `Model/<时间戳>/train_detail.log`。

## 内容尺寸接口

本地服务 `http://localhost:3001` 提供两个接口，Python 客户端在 `layout_check.py`。两者都吃一张卡的**裸 PSUIP**，不问页面坐标。

| | `markdown-layout-check` | `markdown-grid-growth-check` |
|--|--|--|
| Python | `check_layout(psuip, width, height)` | `check_min_size(psuip, columns, rows)` |
| 问题 | 给定 `w×h`，内容能不能看见？ | 在画布上界内，内容最小要几格？ |
| 用途 | 校验模型刚选出的尺寸（`layout_wh` 奖励） | 给当前内容一个尺寸下限，约束动作/奖励 |
| 不做什么 | 不搜索更小格子 | 不回答「某个任意 w×h 行不行」 |

`check_layout` 是点查询：你先有一个提议尺寸，服务只回答够不够。  
`check_min_size` 是生长搜索：服务从较小格子向外扩，返回最小可展示 `min_w×min_h`（响应字段 `columns`/`rows`）。

```python
from RL.layout_check import check_layout, check_min_size

psuip = "<metricCard>\n  <metric_label>营收</metric_label>\n  <metric_value>28</metric_value>\n</metricCard>"

# 这个 2×1 够不够展示？
check_layout(psuip, 2, 1)
# -> {"reachable": True, "valid": True, "messages": ["通过：无内容缺失"]}

# 在 8×10 上界内，最小展示尺寸是多少？
check_min_size(psuip, 8, 10)
# -> {"reachable": True, "valid": True, "min_w": 2, "min_h": 1, ...}
```

手动 curl：

```bash
# 给定尺寸是否可见
curl -s -X POST http://localhost:3001/api/markdown-layout-check \
  -H "Content-Type: application/json" \
  -d '{"psuip":"<metricCard>\n  <metric_label>营收</metric_label>\n  <metric_value>28</metric_value>\n</metricCard>","type":"grid","width":2,"height":1,"test":true}'

# 当前内容的最小展示尺寸
curl -s -X POST http://localhost:3001/api/markdown-grid-growth-check \
  -H "Content-Type: application/json" \
  -d '{"psuip":"<metricCard>\n  <metric_label>营收</metric_label>\n  <metric_value>28</metric_value>\n</metricCard>","columns":8,"rows":10,"test":true}'
```

growth-check 成功时关键字段：`columns`/`rows` = 最小展示格数；`startColumns`/`startRows` = 生长起点；`maxColumns`/`maxRows` = 请求上界；`tendency` = 优先扩展方向。`test: true` 才会带截图 URL。

开关关掉或服务不可达时，两个客户端都返回 `reachable=False`，不改变训练奖励。`layout_wh_reward` 仍未加入 `REWARD_TERMS`；`check_min_size` 目前只作为客户端，尚未接入奖励。

## 冒烟测试

```powershell
python -c "import sys; sys.path.insert(0,'.'); from RL import LayoutEnv; e=LayoutEnv(); o,i=e.reset(seed=0); print(i); print(o['spatial'].shape, o['grid'].shape); m=e.action_masks(); print(e.step(int(m.argmax()))[1:])"
python -m RL.test_state_obs
```

评估已训模型（PSUIP 推理）:

```powershell
python -m RL.test_model --psuip ..\..\..\data\gird_with_cardtype\tager.psuip.md --preset desktop
python -m RL.test_model Model\<新模型目录> --psuip tager.psuip.md --preset phone
# 不传模型路径时用 config.TEST_MODEL / TEST_CKPT；TEST_MODEL="" 则取最新目录
```

输出末尾有一行可直接粘贴到页面「模型输出序列」的文本，格式：

```text
grid:8x6;(3,3,0,0,"textCard")(5,2,3,4,"targetStatCard")...
```

页面会按 `grid:CxR` 设定大画布尺寸并渲染卡片。

数据集回归:

```powershell
python -m RL.test_model --eval
python -m RL.test_model --eval --source psuip
```

## 数据

| 别名 | 文件 |
|------|------|
| `all` | `sample` + `handcrafted` |
| `handcrafted` | `data/handcrafted_layouts.jsonl` |
| `psuip` | `data/psuip_typed_layouts.jsonl` |
| `design` | `data/design_mockups.jsonl` |
| `sample` / `dataset` | `data/sample_layouts.jsonl` |

当前 `all` 共 44 条，最大网格为 8×6；它是训练全集，不是 held-out 测试集。

重新导出：

```powershell
python -m RL.tools.export_sample_dataset
```

PSUIP 源稿目录：仓库根下 `data/gird_with_cardtype/`（由 `config.psuip_source_dir()` 解析）。

## 代码用法

```python
from RL import LayoutEnv

env = LayoutEnv(source="all")
obs, info = env.reset(seed=0)
obs, reward, term, trunc, info = env.step(int(env.action_masks().argmax()))
print(info.get("reward_components"))
print(env.get_layout_sequence())
```
