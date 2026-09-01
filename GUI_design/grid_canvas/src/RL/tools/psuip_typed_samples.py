"""将 data/gird_with_cardtype/*.psuip.md 映射为离散网格。

统一度量：预设单位格 80 × gap/pad 16，与页面默认一致。
  phone 390×844 → 4×8
  desktop 1280×800 → 13×8
  dashboard 1880×680 → 19×7

card 类型名对齐 docx/CARD_REFERENCE.md §0（Slab ×8 + 透传）。
"""

from __future__ import annotations

# 与 CARD_REFERENCE.md / src/cardTypes.ts 一致
TYPE_COLORS: dict[str, str] = {
    "targetStatCard": "#e6a23c",
    "mistakesCard": "#d9776f",
    "showcaseCard": "#3d8bfd",
    "summaryCard": "#9b6bdf",
    "textCard": "#5eb887",
    "commonStyleServiceListDesc": "#6b8cae",
    "pairedImageTextCard": "#4a90a4",
    "heroCard": "#2aa8a0",
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
        "description": "textCard + 4 targetStat + showcaseCard / __rawMarkdown__（13×8 @80/16）",
        "cards": [
            _c(13, 1, 0, 0, "textCard", "Well done header"),
            _c(3, 2, 0, 1, "targetStatCard", "Transcription"),
            _c(3, 2, 3, 1, "targetStatCard", "Related files"),
            _c(3, 2, 6, 1, "targetStatCard", "Smart Camera"),
            _c(4, 2, 9, 1, "targetStatCard", "Handwriting Space"),
            _c(5, 5, 0, 3, "showcaseCard", "知识图谱预览"),
            _c(8, 5, 5, 3, "__rawMarkdown__", "课堂笔记"),
        ],
    },
    {
        "id": "psuip-contents-legend",
        "preset_id": "desktop",
        "source_file": "contents_source_legend.psuip.md",
        "label": "PSUIP·目录与图例",
        "description": "textCard + 4× commonStyleServiceListDesc + heroCard（13×8）",
        "cards": [
            _c(13, 1, 0, 0, "textCard", "CONTENTS"),
            _c(13, 1, 0, 1, "commonStyleServiceListDesc", "1 Definition"),
            _c(13, 1, 0, 2, "commonStyleServiceListDesc", "2 Properties"),
            _c(13, 1, 0, 3, "commonStyleServiceListDesc", "3 Applications"),
            _c(13, 1, 0, 4, "commonStyleServiceListDesc", "4 Visual Data"),
            _c(13, 3, 0, 5, "heroCard", "SOURCE LEGEND"),
        ],
    },
    {
        "id": "psuip-functions-notes",
        "preset_id": "desktop",
        "source_file": "functions_applications_notes.psuip.md",
        "label": "PSUIP·函数笔记",
        "description": "textCard + __rawMarkdown__ 通栏笔记（13×8）",
        "cards": [
            _c(13, 2, 0, 0, "textCard", "Functions & Applications"),
            _c(13, 6, 0, 2, "__rawMarkdown__", "笔记正文"),
        ],
    },
    {
        "id": "psuip-math-final",
        "preset_id": "desktop",
        "source_file": "math_final_dashboard.psuip.md",
        "label": "PSUIP·期末备考",
        "description": "顶栏 + 3 入口 + showcase / raw / mistakes（13×8）",
        "cards": [
            _c(13, 1, 0, 0, "textCard", "Prepare for Math Final"),
            _c(4, 2, 0, 1, "targetStatCard", "Past Exam Papers"),
            _c(5, 2, 4, 1, "targetStatCard", "Error Collection"),
            _c(4, 2, 9, 1, "targetStatCard", "Mock Self-test"),
            _c(4, 5, 0, 3, "showcaseCard", "知识图谱预览"),
            _c(5, 5, 4, 3, "__rawMarkdown__", "Today's Review Note"),
            _c(4, 5, 9, 3, "mistakesCard", "Weak Spots"),
        ],
    },
    {
        "id": "psuip-tager",
        "preset_id": "desktop",
        "source_file": "tager.psuip.md",
        "label": "PSUIP·单目标卡",
        "description": "单张 targetStatCard（13×8）",
        "cards": [
            _c(9, 3, 2, 2, "targetStatCard", "Master Calculus"),
        ],
    },
    {
        "id": "psuip-the-domain",
        "preset_id": "desktop",
        "source_file": "the_domain.psuip.md",
        "label": "PSUIP·Domain 概念",
        "description": "双 textCard + 双 summaryCard（13×8）",
        "cards": [
            _c(13, 2, 0, 0, "textCard", "The Domain"),
            _c(13, 2, 0, 2, "textCard", "CORE DEFINITION"),
            _c(6, 4, 0, 4, "summaryCard", "Visualizing Domain"),
            _c(7, 4, 6, 4, "summaryCard", "Input-Output Rule"),
        ],
    },
    {
        "id": "psuip-phone-contents-legend",
        "preset_id": "phone",
        "source_file": "contents_source_legend.psuip.md",
        "label": "PSUIP·目录图例(手机)",
        "description": "竖屏 4×8",
        "cards": [
            _c(4, 1, 0, 0, "textCard", "CONTENTS"),
            _c(4, 1, 0, 1, "commonStyleServiceListDesc", "1 Definition"),
            _c(4, 1, 0, 2, "commonStyleServiceListDesc", "2 Properties"),
            _c(4, 1, 0, 3, "commonStyleServiceListDesc", "3 Applications"),
            _c(4, 1, 0, 4, "commonStyleServiceListDesc", "4 Visual Data"),
            _c(4, 3, 0, 5, "heroCard", "SOURCE LEGEND"),
        ],
    },
    {
        "id": "psuip-phone-tager",
        "preset_id": "phone",
        "source_file": "tager.psuip.md",
        "label": "PSUIP·单目标卡(手机)",
        "description": "竖屏通栏目标卡 4×8",
        "cards": [
            _c(4, 3, 0, 2, "targetStatCard", "Master Calculus"),
        ],
    },
    {
        "id": "psuip-phone-the-domain",
        "preset_id": "phone",
        "source_file": "the_domain.psuip.md",
        "label": "PSUIP·Domain(手机)",
        "description": "竖屏 Domain 堆叠 4×8",
        "cards": [
            _c(4, 1, 0, 0, "textCard", "The Domain"),
            _c(4, 1, 0, 1, "textCard", "CORE DEFINITION"),
            _c(4, 3, 0, 2, "summaryCard", "Visualizing Domain"),
            _c(4, 3, 0, 5, "summaryCard", "Input-Output Rule"),
        ],
    },
    {
        "id": "psuip-dashboard-class-over",
        "preset_id": "dashboard",
        "source_file": "class_is_over_dashboard.psuip.md",
        "label": "PSUIP·课堂结束(宽)",
        "description": "1880×680 @80/16 → 19×7",
        "cards": [
            _c(19, 1, 0, 0, "textCard", "Well done header"),
            _c(5, 2, 0, 1, "targetStatCard", "Transcription"),
            _c(5, 2, 5, 1, "targetStatCard", "Related files"),
            _c(5, 2, 10, 1, "targetStatCard", "Smart Camera"),
            _c(4, 2, 15, 1, "targetStatCard", "Handwriting Space"),
            _c(8, 4, 0, 3, "showcaseCard", "知识图谱预览"),
            _c(11, 4, 8, 3, "__rawMarkdown__", "课堂笔记"),
        ],
    },
    {
        "id": "psuip-dashboard-math-final",
        "preset_id": "dashboard",
        "source_file": "math_final_dashboard.psuip.md",
        "label": "PSUIP·期末备考(宽)",
        "description": "宽屏 19×7",
        "cards": [
            _c(19, 1, 0, 0, "textCard", "Prepare for Math Final"),
            _c(6, 2, 0, 1, "targetStatCard", "Past Exam Papers"),
            _c(7, 2, 6, 1, "targetStatCard", "Error Collection"),
            _c(6, 2, 13, 1, "targetStatCard", "Mock Self-test"),
            _c(6, 4, 0, 3, "showcaseCard", "知识图谱预览"),
            _c(7, 4, 6, 3, "__rawMarkdown__", "Today's Review Note"),
            _c(6, 4, 13, 3, "mistakesCard", "Weak Spots"),
        ],
    },
]
