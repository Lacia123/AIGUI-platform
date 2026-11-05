"""根据教育 App 设计稿抽象出的布局样例。

统一度量：单位格 228×216 + gap 16；格子数由页面分辨率推导。
每张卡均带 type / label / color。
"""

from __future__ import annotations

from .psuip_typed_samples import _c

DESIGN_MOCKUP_SAMPLES: list[dict] = [
    {
        "id": "design-phone-calculus",
        "preset_id": "phone",
        "label": "设计稿·手机复习",
        "description": "目标 + 日程 + CTA（1×3）",
        "cards": [
            _c(1, 1, 0, 0, "targetStatCard", "今日目标"),
            _c(1, 1, 0, 1, "__rawMarkdown__", "复习日程"),
            _c(1, 1, 0, 2, "textCard", "开始复习"),
        ],
    },
    {
        "id": "design-phone-calculus-tight",
        "preset_id": "phone",
        "label": "设计稿·手机复习(紧凑)",
        "description": "头图占两行 + 底栏（1×3）",
        "cards": [
            _c(1, 2, 0, 0, "heroCard", "复习概览"),
            _c(1, 1, 0, 2, "textCard", "开始复习"),
        ],
    },
    {
        "id": "design-desktop-class-over",
        "preset_id": "desktop",
        "label": "设计稿·课堂结束",
        "description": "顶栏 + 4 工具 + 双底卡（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "Well done header"),
            _c(1, 1, 0, 1, "targetStatCard", "Transcription"),
            _c(1, 1, 1, 1, "targetStatCard", "Related files"),
            _c(1, 1, 2, 1, "targetStatCard", "Smart Camera"),
            _c(2, 1, 3, 1, "targetStatCard", "Handwriting Space"),
            _c(2, 1, 0, 2, "showcaseCard", "知识图谱预览"),
            _c(3, 1, 2, 2, "__rawMarkdown__", "课堂笔记"),
        ],
    },
    {
        "id": "design-tablet-class-over",
        "preset_id": "tablet",
        "label": "设计稿·课堂结束(平板)",
        "description": "平板 3×4",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "Well done header"),
            _c(1, 1, 0, 1, "targetStatCard", "Transcription"),
            _c(1, 1, 1, 1, "targetStatCard", "Related files"),
            _c(1, 1, 2, 1, "targetStatCard", "Smart Camera"),
            _c(1, 1, 0, 2, "showcaseCard", "知识图谱"),
            _c(2, 1, 1, 2, "__rawMarkdown__", "课堂笔记"),
            _c(3, 1, 0, 3, "textCard", "Footer"),
        ],
    },
    {
        "id": "design-square-class-over",
        "preset_id": "square",
        "label": "设计稿·课堂结束(方阵)",
        "description": "3×3",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "Well done header"),
            _c(1, 1, 0, 1, "targetStatCard", "Tool A"),
            _c(1, 1, 1, 1, "targetStatCard", "Tool B"),
            _c(1, 1, 2, 1, "targetStatCard", "Tool C"),
            _c(1, 1, 0, 2, "showcaseCard", "图谱"),
            _c(2, 1, 1, 2, "__rawMarkdown__", "笔记"),
        ],
    },
    {
        "id": "design-desktop-exam-prep",
        "preset_id": "desktop",
        "label": "设计稿·备考仪表盘",
        "description": "顶栏 + 3 入口 + 三列底（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "Prepare for Math Final"),
            _c(2, 1, 0, 1, "targetStatCard", "Past Exam Papers"),
            _c(2, 1, 2, 1, "targetStatCard", "Error Collection"),
            _c(1, 1, 4, 1, "targetStatCard", "Mock Self-test"),
            _c(2, 1, 0, 2, "showcaseCard", "知识图谱预览"),
            _c(2, 1, 2, 2, "__rawMarkdown__", "Today's Review Note"),
            _c(1, 1, 4, 2, "mistakesCard", "Weak Spots"),
        ],
    },
    {
        "id": "design-tablet-exam-prep",
        "preset_id": "tablet",
        "label": "设计稿·备考(平板)",
        "description": "平板 3×4",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "Prepare for Math Final"),
            _c(1, 1, 0, 1, "targetStatCard", "Past Papers"),
            _c(1, 1, 1, 1, "targetStatCard", "Errors"),
            _c(1, 1, 2, 1, "targetStatCard", "Mock Test"),
            _c(1, 2, 0, 2, "showcaseCard", "图谱"),
            _c(1, 2, 1, 2, "__rawMarkdown__", "笔记"),
            _c(1, 2, 2, 2, "mistakesCard", "Weak Spots"),
        ],
    },
    {
        "id": "design-desktop-exam-prep-v2",
        "preset_id": "desktop",
        "label": "设计稿·备考(矮顶栏)",
        "description": "同备考骨架（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "Prepare for Math Final"),
            _c(2, 1, 0, 1, "targetStatCard", "Past Exam Papers"),
            _c(2, 1, 2, 1, "targetStatCard", "Error Collection"),
            _c(1, 1, 4, 1, "targetStatCard", "Mock Self-test"),
            _c(2, 1, 0, 2, "showcaseCard", "知识图谱预览"),
            _c(2, 1, 2, 2, "__rawMarkdown__", "Today's Review Note"),
            _c(1, 1, 4, 2, "mistakesCard", "Weak Spots"),
        ],
    },
    {
        "id": "design-desktop-domain",
        "preset_id": "desktop",
        "label": "设计稿·Domain 概念页",
        "description": "标题 + 双栏（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "The Domain"),
            _c(2, 2, 0, 1, "summaryCard", "Visualizing Domain"),
            _c(3, 2, 2, 1, "summaryCard", "Input-Output Rule"),
        ],
    },
    {
        "id": "design-tablet-domain",
        "preset_id": "tablet",
        "label": "设计稿·Domain(平板)",
        "description": "平板竖向（3×4）",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "The Domain"),
            _c(1, 2, 0, 1, "summaryCard", "Visualizing"),
            _c(2, 2, 1, 1, "summaryCard", "Input-Output"),
            _c(3, 1, 0, 3, "textCard", "CORE DEFINITION"),
        ],
    },
    {
        "id": "design-square-domain",
        "preset_id": "square",
        "label": "设计稿·Domain(方阵)",
        "description": "3×3",
        "cards": [
            _c(3, 1, 0, 0, "textCard", "The Domain"),
            _c(1, 1, 0, 1, "summaryCard", "Visualizing"),
            _c(2, 1, 1, 1, "summaryCard", "Input-Output"),
            _c(3, 1, 0, 2, "textCard", "CORE DEFINITION"),
        ],
    },
    {
        "id": "design-phone-domain-stack",
        "preset_id": "phone",
        "label": "设计稿·Domain(手机堆叠)",
        "description": "竖屏三行（1×3）",
        "cards": [
            _c(1, 1, 0, 0, "textCard", "The Domain"),
            _c(1, 1, 0, 1, "textCard", "CORE DEFINITION"),
            _c(1, 1, 0, 2, "summaryCard", "Visualizing Domain"),
        ],
    },
]
