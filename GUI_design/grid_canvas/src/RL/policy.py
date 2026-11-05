"""MaskablePPO 使用的 Grid 布局特征提取网络。

把 Dict 观测编码成固定维布局状态，Actor/Critic MLP 由 SB3 创建。

结构：
1. Card self-attention：类型 + 画布 / 最小格 embedding + 份额等连续特征
2. 空间 CNN（含左上空白锚点、向右/向下可用跨度）→ HxW token
3. 当前 Card query 对空间 token 做 cross-attention
4. 当前 Card 对剩余/已放 Card 做条件注意力池化
5. 5-token 混合（含 grid/cursor 升维）+ 残差 MLP → features_dim
"""

from __future__ import annotations

import torch
from torch import nn

try:
    from gymnasium import spaces
    from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
except ImportError as exc:  # pragma: no cover
    raise ImportError("需要 stable-baselines3 与 gymnasium") from exc

from . import config as cfg
from .card_types import (
    CARD_IDX_COLS,
    CARD_IDX_MIN_H,
    CARD_IDX_MIN_W,
    CARD_IDX_ROWS,
    CARD_IDX_STATUS,
    CARD_IDX_VALID,
    CARD_OBS_DIM,
    LAYOUT_STATS_DIM,
    SPATIAL_PAGE,
    STATUS_CURRENT,
    TYPE_VOCAB,
)


def _attention_pool(
    query: torch.Tensor,
    keys: torch.Tensor,
    values: torch.Tensor,
    mask: torch.Tensor,
) -> torch.Tensor:
    """当前 Card 作为 query 的单头注意力池化。

    mask: (B, N) True = 可参与。无有效 key 时返回零向量。
    """
    # scores: (B, N)
    scores = (keys * query.unsqueeze(1)).sum(dim=-1) / max(
        1.0, float(keys.size(-1)) ** 0.5
    )
    scores = scores.masked_fill(~mask, -1e9)
    empty = ~mask.any(dim=1)
    weights = torch.softmax(scores, dim=-1)
    weights = torch.where(empty.unsqueeze(-1), torch.zeros_like(weights), weights)
    return (values * weights.unsqueeze(-1)).sum(dim=1)


class _ResidualMLPBlock(nn.Module):
    """PreNorm 残差块：x + Linear(ReLU(Linear(LN(x))))。"""

    def __init__(self, dim: int, hidden: int | None = None) -> None:
        super().__init__()
        width = int(hidden or dim)
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, width)
        self.fc2 = nn.Linear(width, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.fc2(torch.relu(self.fc1(self.norm(x))))


class LayoutFeaturesExtractor(BaseFeaturesExtractor):
    """将环境 Dict 观测编码成 MaskablePPO 使用的固定维度特征。"""

    def __init__(self, observation_space: spaces.Dict, features_dim: int = 256):
        super().__init__(observation_space, features_dim)

        spatial_space = observation_space.spaces["spatial"]
        n_ch, height, width = spatial_space.shape
        cards_space = observation_space.spaces["cards"]
        max_cards = int(cards_space.shape[0])
        max_cols = int(width)
        max_rows = int(height)

        d_model = int(getattr(cfg, "CARD_D_MODEL", 128))
        n_layers = int(getattr(cfg, "CARD_N_LAYERS", 3))
        n_heads = int(getattr(cfg, "CARD_N_HEADS", 4))
        ffn_dim = int(getattr(cfg, "CARD_FFN_DIM", 256))
        spatial_dim = int(getattr(cfg, "SPATIAL_TOKEN_DIM", 64))
        self.d_model = d_model
        self.spatial_dim = spatial_dim
        self.max_cols = max_cols
        self.max_rows = max_rows

        # ------------------------------------------------------------------
        # 空间分支：卷积保留格子 token；输入显式包含当前左上空白锚点。
        # ------------------------------------------------------------------
        dropout = float(getattr(cfg, "CARD_DROPOUT", 0.1))
        self.cnn = nn.Sequential(
            nn.Conv2d(int(n_ch), 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, spatial_dim, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        self.row_emb = nn.Embedding(max_rows, spatial_dim)
        self.col_emb = nn.Embedding(max_cols, spatial_dim)
        self.space_norm = nn.LayerNorm(spatial_dim)

        # ------------------------------------------------------------------
        # Card 序列分支；最小格与画布行列一样走整数 embedding。
        # ------------------------------------------------------------------
        self.type_emb = nn.Embedding(TYPE_VOCAB, 32, padding_idx=0)
        self.cols_emb = nn.Embedding(max_cols + 1, 16)
        self.rows_emb = nn.Embedding(max_rows + 1, 16)
        self.min_w_emb = nn.Embedding(max_cols + 1, 16)
        self.min_h_emb = nn.Embedding(max_rows + 1, 16)
        self.pos_emb = nn.Embedding(max_cards, d_model)

        # 连续字段：去掉 type_id，保留其余 CARD_OBS_DIM-1 维
        self.card_in = nn.Linear(32 + 16 * 4 + (CARD_OBS_DIM - 1), d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=ffn_dim,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.card_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=n_layers,
            enable_nested_tensor=False,
        )

        # 当前 Card → 空间 cross-attention
        self.cross_q = nn.Linear(d_model, spatial_dim)
        self.cross_k = nn.Linear(spatial_dim, spatial_dim)
        self.cross_v = nn.Linear(spatial_dim, spatial_dim)
        self.cross_out = nn.Linear(spatial_dim, d_model)

        # 条件池化投影
        self.pool_k = nn.Linear(d_model, d_model)
        self.pool_v = nn.Linear(d_model, d_model)

        # grid+cursor 升到 d_model，再与四路 h_* 组成 5 个 token
        self.extra_in = nn.Linear(LAYOUT_STATS_DIM + 1, d_model)
        self.extra_norm = nn.LayerNorm(d_model)
        self.fuse_role_emb = nn.Embedding(5, d_model)
        self.fuse_mixer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        n_res = int(getattr(cfg, "FUSE_RES_BLOCKS", 2))
        self.fuse_res = nn.Sequential(
            *[_ResidualMLPBlock(d_model) for _ in range(max(0, n_res))]
        )
        self.fuse_out = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, features_dim),
        )

    def forward(self, observations: dict[str, torch.Tensor]) -> torch.Tensor:
        """执行一次特征提取，返回 ``(batch, features_dim)``。"""
        spatial = observations["spatial"]
        batch_size = spatial.size(0)
        device = spatial.device

        # 空间 token: (B, H*W, spatial_dim)
        feat = self.cnn(spatial)
        _, _, height, width = feat.shape
        feat = feat.permute(0, 2, 3, 1).reshape(batch_size, height * width, -1)
        rows = torch.arange(height, device=device).unsqueeze(1).expand(height, width)
        cols = torch.arange(width, device=device).unsqueeze(0).expand(height, width)
        pos = self.row_emb(rows.reshape(-1)) + self.col_emb(cols.reshape(-1))
        space_tokens = self.space_norm(feat + pos.unsqueeze(0))
        page_mask = spatial[:, SPATIAL_PAGE].reshape(batch_size, height * width) > 0.5

        # Card tokens
        cards = observations["cards"]
        type_ids = cards[..., 0].long().clamp(0, TYPE_VOCAB - 1)
        # cols_n/rows_n 在 [0,1]，还原为整数格数再 embedding
        cols_ids = (
            (cards[..., CARD_IDX_COLS] * float(self.max_cols))
            .round()
            .long()
            .clamp(0, self.max_cols)
        )
        rows_ids = (
            (cards[..., CARD_IDX_ROWS] * float(self.max_rows))
            .round()
            .long()
            .clamp(0, self.max_rows)
        )
        min_w_ids = (
            (cards[..., CARD_IDX_MIN_W] * float(self.max_cols))
            .round()
            .long()
            .clamp(0, self.max_cols)
        )
        min_h_ids = (
            (cards[..., CARD_IDX_MIN_H] * float(self.max_rows))
            .round()
            .long()
            .clamp(0, self.max_rows)
        )
        tok = self.card_in(
            torch.cat(
                [
                    self.type_emb(type_ids),
                    self.cols_emb(cols_ids),
                    self.rows_emb(rows_ids),
                    self.min_w_emb(min_w_ids),
                    self.min_h_emb(min_h_ids),
                    cards[..., 1:],
                ],
                dim=-1,
            )
        )
        positions = torch.arange(cards.size(1), device=device).unsqueeze(0)
        positions = positions.expand(batch_size, -1)
        tok = tok + self.pos_emb(positions)

        pad = cards[..., CARD_IDX_VALID] <= 0
        if pad.all():
            encoded = tok
        else:
            safe_pad = pad.clone()
            empty = safe_pad.all(dim=1)
            if empty.any():
                safe_pad[empty, 0] = False
            encoded = self.card_encoder(tok, src_key_padding_mask=safe_pad)

        # 优先按 status=CURRENT 取当前卡；否则用归一化 cursor * N 回退
        status = cards[..., CARD_IDX_STATUS]
        valid = cards[..., CARD_IDX_VALID] > 0
        current_mask = valid & (torch.abs(status - STATUS_CURRENT) < 0.25)
        has_current = current_mask.any(dim=1)
        # argmax 在全 False 时返回 0，后面用 cursor 覆盖
        cur_idx = current_mask.float().argmax(dim=1)
        cursor = observations["cursor"].reshape(batch_size, -1)[:, 0]
        n_valid = valid.float().sum(dim=1).clamp(min=1.0)
        fallback_idx = (cursor * n_valid).round().long().clamp(0, cards.size(1) - 1)
        cur_idx = torch.where(has_current, cur_idx, fallback_idx)
        batch_idx = torch.arange(batch_size, device=device)
        h_cur = encoded[batch_idx, cur_idx]

        # Card → grid cross-attention
        q = self.cross_q(h_cur).unsqueeze(1)
        k = self.cross_k(space_tokens)
        v = self.cross_v(space_tokens)
        scores = torch.matmul(q, k.transpose(-1, -2)) / max(
            1.0, float(self.spatial_dim) ** 0.5
        )
        scores = scores.masked_fill(~page_mask.unsqueeze(1), -1e9)
        attn = torch.softmax(scores, dim=-1)
        # 全页 mask 为空时避免 NaN
        no_page = ~page_mask.any(dim=1)
        attn = torch.where(
            no_page.view(batch_size, 1, 1), torch.zeros_like(attn), attn
        )
        h_space = self.cross_out(torch.matmul(attn, v).squeeze(1))

        # 条件池化：剩余 / 已放
        keys = self.pool_k(encoded)
        values = self.pool_v(encoded)
        rest_mask = valid & (status < 0.5)
        done_mask = valid & (status > 1.5)
        h_rest = _attention_pool(h_cur, keys, values, rest_mask)
        h_done = _attention_pool(h_cur, keys, values, done_mask)

        extra = torch.cat(
            [
                observations["grid"].reshape(batch_size, -1),
                cursor.unsqueeze(-1).to(h_cur.dtype),
            ],
            dim=-1,
        )
        h_extra = self.extra_norm(self.extra_in(extra.to(h_cur.dtype)))
        tokens = torch.stack([h_cur, h_space, h_rest, h_done, h_extra], dim=1)
        tokens = tokens + self.fuse_role_emb.weight.unsqueeze(0)
        tokens = self.fuse_mixer(tokens)
        fuse_mask = torch.ones(batch_size, tokens.size(1), dtype=torch.bool, device=device)
        mixed = _attention_pool(h_cur, tokens, tokens, fuse_mask)
        fused = self.fuse_res(mixed + h_cur)
        return self.fuse_out(fused)
