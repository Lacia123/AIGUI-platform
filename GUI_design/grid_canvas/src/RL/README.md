# Layout RL

结构参考 `Lenovo_rlmodel/rl_train`，保持简单：

```
RL/
  config.py     # 超参常量
  env.py        # Gym 环境（薄封装）
  reward.py     # 奖励函数
  layout.py     # 几何 / 掩码 / 观测
  data.py       # 读 data/*.jsonl
  train.py      # MaskablePPO 训练入口
  data/         # 训练数据
  Model/        # 权重输出
  tools/        # 数据生成与导出
```

任务：已知画布与卡片建议尺寸，顺序预测 `(x,y,w,h)`（均在画布格数范围内）。

## 安装与训练

```powershell
cd GUI_design\grid_canvas\src
pip install -r RL\requirements.txt
python -m RL.train
# 或
python -m RL
```

改超参：编辑 `config.py`（`SOURCE` / `TIMESTEPS` / 奖励系数等）。

## 冒烟测试

```powershell
python -c "import sys; sys.path.insert(0,'.'); from RL import LayoutEnv; e=LayoutEnv(); o,i=e.reset(seed=0); print(i); m=e.action_masks(); print(e.step(int(m.argmax()))[1:])"
```

## 重新导出数据

```powershell
python -m RL.tools.export_sample_dataset
```

## 代码用法

```python
from RL import LayoutEnv

env = LayoutEnv(source="design")
obs, info = env.reset(seed=0)
obs, reward, term, trunc, info = env.step(int(env.action_masks().argmax()))
print(env.get_layout_sequence())
```
