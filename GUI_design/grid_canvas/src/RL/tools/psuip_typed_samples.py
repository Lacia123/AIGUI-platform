"""将 data/gird_with_cardtype/*.psuip.md 映射为离散网格。

统一度量：单位格 228×216 + gap 16；格子由页面分辨率推导：
  phone 390×844 → 1×3
  desktop 1280×800 → 5×3
  dashboard 1880×680 → 7×3

card 类型名对齐 docx/CARD_REFERENCE.md §0（Slab ×9 + 透传）。
"""

from __future__ import annotations

TYPE_COLORS: dict[str, str] = {
    "targetStatCard": "#e6a23c",
    "mistakesCard": "#d9776f",
    "showcaseCard": "#3d8bfd",
    "summaryCard": "#9b6bdf",
    "textCard": "#5eb887",
    "commonStyleServiceListDesc": "#6b8cae",
    "pairedImageTextCard": "#4a90a4",
    "heroCard": "#2aa8a0",
    "contentSummaryCard": "#c4785a",
    "[table:commonStyle]": "#8a7a5c",
    "__rawMarkdown__": "#7a8b9a",
    "Topology": "#5c6bc0",
}


def _c(
    w: int,
    h: int,
    x: int,
    y: int,
    type_: str,
    label: str,
) -> dict:
    return {
        "w": w,
        "h": h,
        "x": x,
        "y": y,
        "type": type_,
        "label": label,
        "color": TYPE_COLORS.get(type_, "#3d8bfd"),
    }


PSUIP_TYPED_SAMPLES: list[dict] = [
    {
        "id": "psuip-class-is-over",
        "preset_id": "desktop",
        "source_file": "class_is_over_dashboard.psuip.md",
        "label": "PSUIP·课堂结束",
        "description": "textCard + 4 targetStat + showcase / raw（5×3 @228×216/16）",
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
        "id": "psuip-contents-legend",
        "preset_id": "desktop",
        "source_file": "contents_source_legend.psuip.md",
        "label": "PSUIP·目录与图例",
        "description": "标题 + 目录行 + hero（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "CONTENTS"),
            _c(5, 1, 0, 1, "commonStyleServiceListDesc", "1–4 Sections"),
            _c(5, 1, 0, 2, "heroCard", "SOURCE LEGEND"),
        ],
    },
    {
        "id": "psuip-functions-notes",
        "preset_id": "desktop",
        "source_file": "functions_applications_notes.psuip.md",
        "label": "PSUIP·函数笔记",
        "description": "标题 + 笔记（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "Functions & Applications"),
            _c(5, 2, 0, 1, "__rawMarkdown__", "笔记正文"),
        ],
    },
    {
        "id": "psuip-math-final",
        "preset_id": "desktop",
        "source_file": "math_final_dashboard.psuip.md",
        "label": "PSUIP·期末备考",
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
        "id": "psuip-tager",
        "preset_id": "desktop",
        "source_file": "tager.psuip.md",
        "label": "PSUIP·单目标卡",
        "description": "单张 targetStatCard 填满画布（5×3）",
        "cards": [
            _c(5, 3, 0, 0, "targetStatCard", "Master Calculus"),
        ],
    },
    {
        "id": "psuip-the-domain",
        "preset_id": "desktop",
        "source_file": "the_domain.psuip.md",
        "label": "PSUIP·Domain 概念",
        "description": "双标题 + 双 summary（5×3）",
        "cards": [
            _c(5, 1, 0, 0, "textCard", "The Domain"),
            _c(5, 1, 0, 1, "textCard", "CORE DEFINITION"),
            _c(2, 1, 0, 2, "summaryCard", "Visualizing Domain"),
            _c(3, 1, 2, 2, "summaryCard", "Input-Output Rule"),
        ],
    },
    {
        "id": "psuip-phone-contents-legend",
        "preset_id": "phone",
        "source_file": "contents_source_legend.psuip.md",
        "label": "PSUIP·目录图例(手机)",
        "description": "竖屏 1×3",
        "cards": [
            _c(1, 1, 0, 0, "textCard", "CONTENTS"),
            _c(1, 1, 0, 1, "commonStyleServiceListDesc", "Sections"),
            _c(1, 1, 0, 2, "heroCard", "SOURCE LEGEND"),
        ],
    },
    {
        "id": "psuip-phone-tager",
        "preset_id": "phone",
        "source_file": "tager.psuip.md",
        "label": "PSUIP·单目标卡(手机)",
        "description": "竖屏目标卡填满画布 1×3",
        "cards": [
            _c(1, 3, 0, 0, "targetStatCard", "Master Calculus"),
        ],
    },
    {
        "id": "psuip-phone-the-domain",
        "preset_id": "phone",
        "source_file": "the_domain.psuip.md",
        "label": "PSUIP·Domain(手机)",
        "description": "竖屏三行 1×3",
        "cards": [
            _c(1, 1, 0, 0, "textCard", "The Domain"),
            _c(1, 1, 0, 1, "textCard", "CORE DEFINITION"),
            _c(1, 1, 0, 2, "summaryCard", "Visualizing Domain"),
        ],
    },
    {
        "id": "psuip-dashboard-class-over",
        "preset_id": "dashboard",
        "source_file": "class_is_over_dashboard.psuip.md",
        "label": "PSUIP·课堂结束(宽)",
        "description": "1880×680 @228×216/16 → 7×3",
        "cards": [
            _c(7, 1, 0, 0, "textCard", "Well done header"),
            _c(2, 1, 0, 1, "targetStatCard", "Transcription"),
            _c(2, 1, 2, 1, "targetStatCard", "Related files"),
            _c(2, 1, 4, 1, "targetStatCard", "Smart Camera"),
            _c(1, 1, 6, 1, "targetStatCard", "Handwriting Space"),
            _c(3, 1, 0, 2, "showcaseCard", "知识图谱预览"),
            _c(4, 1, 3, 2, "__rawMarkdown__", "课堂笔记"),
        ],
    },
    {
        "id": "psuip-dashboard-math-final",
        "preset_id": "dashboard",
        "source_file": "math_final_dashboard.psuip.md",
        "label": "PSUIP·期末备考(宽)",
        "description": "宽屏 7×3",
        "cards": [
            _c(7, 1, 0, 0, "textCard", "Prepare for Math Final"),
            _c(2, 1, 0, 1, "targetStatCard", "Past Exam Papers"),
            _c(3, 1, 2, 1, "targetStatCard", "Error Collection"),
            _c(2, 1, 5, 1, "targetStatCard", "Mock Self-test"),
            _c(2, 1, 0, 2, "showcaseCard", "知识图谱预览"),
            _c(3, 1, 2, 2, "__rawMarkdown__", "Today's Review Note"),
            _c(2, 1, 5, 2, "mistakesCard", "Weak Spots"),
        ],
    },
]
