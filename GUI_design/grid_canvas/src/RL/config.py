"""训练超参与路径常量。

改学习率、画布上界等训练行为时优先编辑本文件。
奖励在 reward.py 中重写。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent
DATA_DIR = PKG_ROOT / "data"
TEST_DATA_DIR = DATA_DIR / "test_data"
MODEL_SAVE_PATH = PKG_ROOT / "Model"

# 数据：训练用随机画布 synth；结束后额外评估手工页和 testdata
SOURCE = "synth"
# 合成数据含多种网格，不按单一尺寸过滤。
TRAIN_GRID: tuple[int, int] | None = None
# 训练结束后额外评估 held-out。
EVAL_EXTRA_SOURCES: tuple[str, ...] = ("handcrafted", "testdata")

# test_model 默认评估源 / 切分。命令行 --source / --split 会覆盖。
# all / sample / handcrafted / psuip / design / testdata（data/test_data/*.jsonl）
TEST_SOURCE = SOURCE
TEST_SPLIT = "all"

# 环境固定张量尺寸（不同分辨率 episode 做 padding）
# 覆盖官方预设及现有 handcrafted：最大 8×5 / 3×6。
MAX_COLS = 8
MAX_ROWS = 6
MAX_CARDS = 32
# 单卡 w/h 动作上界（格数，1-indexed）；与画布 MAX_COLS/MAX_ROWS 对齐
MAX_CARD_W = MAX_COLS
MAX_CARD_H = MAX_ROWS
MAX_INVALID_STREAK = 20

def action_space_size(
    max_card_w: int = MAX_CARD_W,
    max_card_h: int = MAX_CARD_H,
) -> int:
    """计算仅含卡片宽高的离散动作空间大小。

    输入:
        max_card_w, max_card_h: 单卡宽高动作上界（1-indexed 格数）。
    输出:
        max_card_w * max_card_h。
    逻辑:
        每个整数 action 只对应一组 (w,h)；(x,y) 由环境的左上空白锚点确定。
    """
    return max_card_w * max_card_h

# 内容尺寸校验（同一本地服务上的两个接口，见 layout_check.py）
LAYOUT_CHECK_ENABLED = True
LAYOUT_CHECK_URL = "http://localhost:3001/api/markdown-layout-check"
GRID_GROWTH_CHECK_URL = "http://localhost:3001/api/markdown-grid-growth-check"
LAYOUT_CHECK_TIMEOUT = 15.0

# 难例加权采样：卡多 / phone|tablet 小屏布局训练更频繁
HARD_EPISODE_MIN_CARDS = 7
HARD_EPISODE_WEIGHT = 3.0
# 再按 (cols, rows) 稀有度加权；用 1/sqrt(count) 并设上限，避免 3×6 过度放大
RARE_GRID_WEIGHT = True
RARE_GRID_SQRT = True
RARE_GRID_WEIGHT_CAP = 5.0
# 同页同类型异尺寸 / 历史易堵死样本额外加权
SAME_TYPE_VARIED_WEIGHT = 2.0
NO_LEGAL_MOVES_EPISODE_IDS: tuple[str, ...] = (
    "tablet-gallery",
    "design-tablet-class-over",
    "design-tablet-exam-prep",
)
NO_LEGAL_MOVES_WEIGHT = 2.0
# 当前 best 仍经常尺寸打偏的页：侧栏/大卡/稀有格
HARD_SIZE_EPISODE_IDS: tuple[str, ...] = (
    "desktop-holy-grail",
    "desktop-magazine",
    "desktop-dashboard",
    "square-dashboard",
    "design-desktop-domain",
    "design-tablet-domain",
    "1-1",
    "7",
    "22-1",
)
HARD_SIZE_WEIGHT = 3.0

# 验证集：训练中按面积误差 / 成行率 / 空白率 / 1×1 数量选最优
VAL_RATIO = 0.15
VAL_EVERY_UPDATES = 20
# 空白、面积、结构已同一量级，不再做 running 标准化。
NORMALIZE_REWARD = False
# 训练时每局在线抽样类型队列；synth jsonl 只作固定验证集。
ONLINE_TRAIN = True

# 动作掩码：禁止细长条；按剩余卡目标面积预留空格。
MAX_ASPECT_RATIO = 3.0
AREA_RESERVE_RATIO = 0.7

# 搜索老师：Beam Search 出示范轨迹，先行为克隆再 PPO。
BC_PRETRAIN = True
BC_EPISODES = 200
BC_EPOCHS = 8
BC_BATCH_SIZE = 64
TEACHER_BEAM_WIDTH = 8
# 推理：策略引导 Beam Search。1 = 贪心。
INFER_BEAM_WIDTH = 8
INFER_POLICY_TOP_K = 4

# ---------------------------------------------------------------------------
# 训练量（PPO 用「环境步数」，不是监督学习的 epoch）
# ---------------------------------------------------------------------------
# 总交互步数：learn(total_timesteps=TIMESTEPS)
# 约等于更新次数 ≈ TIMESTEPS / (N_STEPS * N_ENVS)
# 例: 500_000 / (256*4) ≈ 488 次 PPO update
TIMESTEPS = 500_000
N_ENVS = 4
SEED = 42

# ---------------------------------------------------------------------------
# MaskablePPO 超参（全部在此改；勿再依赖 SB3 隐式默认）
# ---------------------------------------------------------------------------
# 每次 update：各环境先各采 N_STEPS 步 → 缓冲大小 = N_STEPS * N_ENVS
# 再把缓冲切成 BATCH_SIZE 的小批，重复打乱训练 N_EPOCHS 轮（这才是「轮次」）
LEARNING_RATE = 1.5e-4
N_STEPS = 256
BATCH_SIZE = 128
N_EPOCHS = 12  # 每个 rollout 上的 SGD 轮数（≠ 总训练轮数）
GAMMA = 0.99
GAE_LAMBDA = 0.95
CLIP_RANGE = 0.2
ENT_COEF = 0.008
VF_COEF = 0.5
MAX_GRAD_NORM = 0.5
TARGET_KL = 0.03  # 动作空间已缩到 48，限制策略抖动以免尺寸来回漂

# 策略网络。层数和宽度压过 6 页模板；最小格走整数 embedding。
FEATURES_DIM = 128
CARD_D_MODEL = 64
CARD_N_LAYERS = 2
CARD_N_HEADS = 4
CARD_FFN_DIM = 128
CARD_DROPOUT = 0.1
SPATIAL_TOKEN_DIM = 64
FUSE_RES_BLOCKS = 1
# Actor/Critic 在特征后的 MLP；None = SB3 默认 [64, 64]
NET_ARCH = None  # 例: dict(pi=[128, 128], vf=[128, 128])

TENSORBOARD_LOG = ""  # 空 = 不写；可填 "log/tensorboard"

# 训练日志：每完成 N 个 episode 打印一次汇总；每 N 次 PPO update 打印学习指标
TRAIN_LOG_EVERY_EPISODES = 20
TRAIN_LOG_EVERY_UPDATES = 1

# 评估：训练结束默认测全集；仅当显式传 episodes=N 时截断
EVAL_EPISODES = 0  # 0 = 全部 episode

# 权重文件名（落在 Model/<训练时间戳>/ 下，避免互相覆盖）
CHECKPOINT_NAME = "layout_maskable_ppo"
BEST_CHECKPOINT_NAME = "layout_maskable_ppo_best"

# test_model 默认加载哪次训练。命令行位置参数 / --ckpt 会覆盖。
# TEST_MODEL 空字符串 = Model/ 下最新时间戳目录；也可填：
#   "20260918_171324"
#   "Model/20260918_171324"
#   "Model/20260918_171324/layout_maskable_ppo_best"
TEST_MODEL = ""
# auto：目录内优先 *_best，否则 final；也可强制 best / final
TEST_CKPT = "auto"


def new_run_dir() -> Path:
    """创建本次训练输出目录 Model/YYYYMMDD_HHMMSS/。

    输出:
        已 mkdir 的新目录 Path。
    """
    run_dir = MODEL_SAVE_PATH / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ppo_update_count(
    timesteps: int | None = None,
    n_steps: int | None = None,
    n_envs: int | None = None,
) -> int:
    """由总步数估算 PPO update（rollout）次数。"""
    timesteps = TIMESTEPS if timesteps is None else timesteps
    n_steps = N_STEPS if n_steps is None else n_steps
    n_envs = N_ENVS if n_envs is None else n_envs
    per = max(1, int(n_steps) * int(n_envs))
    return int(timesteps) // per


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


def psuip_jsonl() -> Path:
    """带类型 PSUIP episode 路径 data/psuip_typed_layouts.jsonl。"""
    return DATA_DIR / "psuip_typed_layouts.jsonl"


def handcrafted_jsonl() -> Path:
    """手工标注 episode 路径 data/handcrafted_layouts.jsonl。"""
    return DATA_DIR / "handcrafted_layouts.jsonl"


def synth_jsonl() -> Path:
    """随机画布合成 episode 路径 data/synth_layouts.jsonl。"""
    return DATA_DIR / "synth_layouts.jsonl"


def test_data_jsonls() -> list[Path]:
    """评估用 jsonl：data/test_data/*.jsonl。"""
    if not TEST_DATA_DIR.is_dir():
        return []
    return sorted(TEST_DATA_DIR.glob("*.jsonl"))


def psuip_source_dir() -> Path:
    """原始带类型稿目录 data/gird_with_cardtype/。"""
    return PKG_ROOT.parents[3] / "data" / "gird_with_cardtype"


def ensure_package_importable() -> None:
    """将 grid_canvas/src 加入 sys.path，支持脚本直接运行。"""
    import sys

    src = str(PKG_ROOT.parent)
    if src not in sys.path:
        sys.path.insert(0, src)
