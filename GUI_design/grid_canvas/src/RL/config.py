"""训练超参与路径常量。

改学习率、奖励权重、画布上界等训练行为时优先编辑本文件。
权重含义见各常量旁注释；奖励计算公式见 reward.py。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent
DATA_DIR = PKG_ROOT / "data"
MODEL_SAVE_PATH = PKG_ROOT / "Model"

# 数据：design = design_mockups.jsonl；sample = sample_layouts.jsonl
# 训练只用 SOURCE；训练结束后还会额外评估 EVAL_EXTRA_SOURCES
SOURCE = "design"
# 训练结束后追加评估的数据源；classic = sample 中非 design- 的经典布局
EVAL_EXTRA_SOURCES = ("classic",)

# 环境固定张量尺寸（不同分辨率 episode 做 padding）
# 对齐默认 80 单位格 + 16 gap：dashboard 19×7、tablet 8×10 为当前上界
MAX_COLS = 19
MAX_ROWS = 10
MAX_CARDS = 32
# 单卡 w/h 动作上界（格数，1-indexed）；与画布 MAX_COLS/MAX_ROWS 对齐
MAX_CARD_W = MAX_COLS
MAX_CARD_H = MAX_ROWS
MAX_INVALID_STREAK = 20


def action_space_size(
    max_cols: int = MAX_COLS,
    max_rows: int = MAX_ROWS,
    max_card_w: int = MAX_CARD_W,
    max_card_h: int = MAX_CARD_H,
) -> int:
    """计算离散动作空间大小（编码维度，非合法动作数）。

    输入:
        max_cols, max_rows: 动作编码用的画布上界（与观测 padding 一致）。
        max_card_w, max_card_h: 单卡宽高动作上界（1-indexed 格数）。
    输出:
        max_cols * max_rows * max_card_w * max_card_h。
    逻辑:
        每个整数 action 对应一组 (x,y,w,h)；实际合法组合由 action_masks 过滤。
    """
    return max_cols * max_rows * max_card_w * max_card_h

# 合法性奖励
LEGAL_VALID_REWARD = 0.2
LEGAL_INVALID_PENALTY = -1.0
REWARD_SUCCESS = 10.0
REWARD_FAIL = -5.0
REWARD_DENSITY = 2.0

# 样式奖励
# edge: 鼓励新卡与已放卡共享边缘，减少零散布局
# alignment: 鼓励卡片的左/右/上/下边缘形成对齐线
# parallel: 鼓励尺寸相似的卡紧邻并列且边缘对齐
# order: 鼓励先放的块偏左上、后放的块偏右下（阅读顺序）
# origin: 鼓励第一块落在 (0,0)
# prev_adjacent: 按放置序号，第 k 块应紧贴第 k-1 块，避免散落
STYLE_EDGE_WEIGHT = 0.6
STYLE_ALIGNMENT_WEIGHT = 0.4
STYLE_PARALLEL_WEIGHT = 0.8
STYLE_ORDER_WEIGHT = 0.5
STYLE_ORIGIN_WEIGHT = 3
STYLE_PREV_ADJACENT_WEIGHT = 1.5
# imitation: 贴近设计稿专家坐标，复杂布局关键
IMITATION_WEIGHT = 0
# 放置后剩余卡贪心不可行时的惩罚
PACKABILITY_PENALTY = -1.5
STYLE_SIMILARITY_THRESHOLD = 0.75

# 难例加权采样：卡多 / tablet 布局训练更频繁
HARD_EPISODE_MIN_CARDS = 7
HARD_EPISODE_WEIGHT = 3.0

# MaskablePPO
LEARNING_RATE = 3e-4
N_STEPS = 256
BATCH_SIZE = 128
GAMMA = 0.99
ENT_COEF = 0.01
N_ENVS = 4
SEED = 42
TIMESTEPS = 200_000
TENSORBOARD_LOG = ""  # 空 = 不写；可填 "log/tensorboard"

# 评估：训练结束默认测全集；仅当显式传 episodes=N 时截断
EVAL_EPISODES = 0  # 0 = 全部 episode

# 权重文件名（落在 Model/<训练时间戳>/ 下，避免互相覆盖）
CHECKPOINT_NAME = "layout_maskable_ppo"


def new_run_dir() -> Path:
    """创建本次训练输出目录 Model/YYYYMMDD_HHMMSS/。

    输出:
        已 mkdir 的新目录 Path。
    """
    run_dir = MODEL_SAVE_PATH / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def checkpoint_path(run_dir: Path | None = None) -> Path:
    """返回 checkpoint 文件路径（不含 .zip 后缀，SB3 自动追加）。

    输入:
        run_dir: 目标目录；None 时新建时间戳目录。
    输出:
        run_dir / CHECKPOINT_NAME。
    """
    run_dir = run_dir or new_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / CHECKPOINT_NAME


def design_jsonl() -> Path:
    """设计稿 episode 路径 data/design_mockups.jsonl。"""
    return DATA_DIR / "design_mockups.jsonl"


def sample_jsonl() -> Path:
    """经典/合成 episode 路径 data/sample_layouts.jsonl。"""
    return DATA_DIR / "sample_layouts.jsonl"


def ensure_package_importable() -> None:
    """将 grid_canvas/src 加入 sys.path，支持脚本直接运行。"""
    import sys

    src = str(PKG_ROOT.parent)
    if src not in sys.path:
        sys.path.insert(0, src)
