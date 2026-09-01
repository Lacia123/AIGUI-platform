"""手算演示：Critic 的 V(s) 与优势 A 怎么来。

用法（在 grid_canvas/src 下）:
  python -m RL.teach_me.advantage_demo

不依赖 SB3 / 真实网络：用「假装已经训好的 Critic」给出的一组 V，
走一条 5 步轨迹，逐步打印 TD δ 和 GAE 优势 A。
"""

from __future__ import annotations

# ---------- 一条假想的 5 步布局轨迹 ----------
# 每步：状态编号、动作（锚点）、环境奖励 r、Critic 估的 V(s)
# V 在真实训练里是神经网络前向出来的；这里直接写成数，方便手算。

STEPS = [
    # t,  动作描述,           r,    V(s_t)
    (0, "放第1张卡 -> (0,0)", 1.0, 3.0),
    (1, "放第2张卡 -> (2,0)", 2.0, 2.5),
    (2, "放第3张卡 -> (0,2)", 0.0, 1.5),  # 这步较差
    (3, "放第4张卡 -> (3,2)", 1.0, 1.2),
    (4, "放第5张卡 -> (5,3)", 3.0, 0.5),  # 最后一步
]

GAMMA = 0.99  # 折扣
LAMBDA = 1.0  # GAE 的 λ；=1 时把后面所有 δ 都折进当前 A


def td_deltas(rewards: list[float], values: list[float], gamma: float) -> list[float]:
    """δ_t = r_t + γ V(s_{t+1}) - V(s_t)；最后一步 V(s_{T+1})=0。"""
    n = len(rewards)
    deltas: list[float] = []
    for t in range(n):
        v_next = 0.0 if t == n - 1 else values[t + 1]
        deltas.append(rewards[t] + gamma * v_next - values[t])
    return deltas


def gae_advantages(deltas: list[float], gamma: float, lam: float) -> list[float]:
    """从后往前：A_t = δ_t + (γλ) A_{t+1}。"""
    n = len(deltas)
    adv = [0.0] * n
    acc = 0.0
    for t in reversed(range(n)):
        acc = deltas[t] + gamma * lam * acc
        adv[t] = acc
    return adv


def main() -> None:
    rewards = [s[2] for s in STEPS]
    values = [s[3] for s in STEPS]

    print("=" * 60)
    print("1) 采样时：每步 Actor 选动作，Critic 只前向出 V(s_t)")
    print("   （此处 V 是假数据，真实代码里是 critic 网络输出）")
    print("=" * 60)
    for t, action, r, v in STEPS:
        print(f"  t={t}  {action}")
        print(f"       r={r:.1f}   V(s_{t})={v:.1f}")

    print()
    print("=" * 60)
    print("2) 整条走完后：算 TD 残差 δ_t = r + γV(s') - V(s)")
    print("=" * 60)
    deltas = td_deltas(rewards, values, GAMMA)
    for t, d in enumerate(deltas):
        v_next = 0.0 if t == len(STEPS) - 1 else values[t + 1]
        print(
            f"  δ_{t} = {rewards[t]:.1f} + {GAMMA}*{v_next:.1f} - {values[t]:.1f}"
            f"  = {d:+.3f}"
        )

    print()
    print("=" * 60)
    print(f"3) GAE：从后往前累加  A_t = δ_t + (γλ)A_{{t+1}}   (λ={LAMBDA})")
    print("=" * 60)
    advantages = gae_advantages(deltas, GAMMA, LAMBDA)
    for t in reversed(range(len(advantages))):
        if t == len(advantages) - 1:
            print(f"  A_{t} = δ_{t} = {advantages[t]:+.3f}")
        else:
            print(
                f"  A_{t} = δ_{t} + {GAMMA * LAMBDA:.2f}*A_{t + 1}"
                f" = {deltas[t]:+.3f} + {GAMMA * LAMBDA:.2f}*{advantages[t + 1]:+.3f}"
                f" = {advantages[t]:+.3f}"
            )

    print()
    print("=" * 60)
    print("4) 含义：A>0 加强该动作；A<0 削弱。同时给 Critic 回归目标 R̂=A+V")
    print("=" * 60)
    for t, action, r, v in STEPS:
        a = advantages[t]
        ret = a + v
        hint = "加强" if a > 0 else ("削弱" if a < 0 else "几乎不动")
        print(
            f"  t={t}  A={a:+.3f} ({hint}「{action}」)   "
            f"R̂={ret:.3f}  (Critic 学着贴近这个数)"
        )

    print()
    print("一句话：V(s) 是网络估的局面分；优势 A = 实际表现 − 这个预期。")


if __name__ == "__main__":
    main()
