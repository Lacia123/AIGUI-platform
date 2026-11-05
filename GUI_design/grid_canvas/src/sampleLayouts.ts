import { stringifyLayoutSequence } from './layoutFormat'
import type { LayoutCard } from './layoutFormat'

export type SampleLayoutCard = LayoutCard & {
  type?: string
  label?: string
  color?: string
}

export type SampleLayout = {
  id: string
  label: string
  description: string
  /** 对应 RESOLUTION_PRESETS.id */
  presetId: string
  cards: SampleLayoutCard[]
}

function cards(
  ...tuples: Array<
    [number, number, number, number] | [number, number, number, number, string, string, string?]
  >
): SampleLayoutCard[] {
  return tuples.map((t) => {
    const [w, h, x, y] = t
    const item: SampleLayoutCard = { w, h, x, y }
    if (t.length >= 6) {
      item.type = t[4]
      item.label = t[5]
      if (t.length >= 7 && t[6]) item.color = t[6]
    }
    return item
  })
}

/**
 * 单格 228×216 / gap 16；全部样例均带 card type。
 *   phone 390×844 → 1×3
 *   tablet 768×1024 → 3×4
 *   desktop 1280×800 → 5×3
 *   dashboard 1880×680 → 7×3
 *   square 800×800 → 3×3
 */
export const SAMPLE_LAYOUTS: SampleLayout[] = [
  // —— 经典 ——
  {
    id: 'phone-feed',
    presetId: 'phone',
    label: "信息流",
    description: "顶 / 中 / 底三行通栏（1×3）",
    cards: cards(
      [1, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [1, 1, 0, 1, 'commonStyleServiceListDesc', '列表', '#6b8cae'],
      [1, 1, 0, 2, 'textCard', '底栏', '#5eb887'],
    ),
  },
  {
    id: 'phone-landing',
    presetId: 'phone',
    label: "落地页",
    description: "顶栏 + Hero + CTA（1×3）",
    cards: cards(
      [1, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [1, 1, 0, 1, 'heroCard', 'Hero', '#2aa8a0'],
      [1, 1, 0, 2, 'textCard', 'CTA', '#5eb887'],
    ),
  },
  {
    id: 'phone-profile',
    presetId: 'phone',
    label: "个人主页",
    description: "头图 + 内容 + 底栏（1×3）",
    cards: cards(
      [1, 1, 0, 0, 'heroCard', '头图', '#2aa8a0'],
      [1, 1, 0, 1, 'summaryCard', '内容', '#9b6bdf'],
      [1, 1, 0, 2, 'textCard', '底栏', '#5eb887'],
    ),
  },
  {
    id: 'tablet-blog',
    presetId: 'tablet',
    label: "双栏博客",
    description: "顶栏 + 主/侧 + 底（3×4）",
    cards: cards(
      [3, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [2, 2, 0, 1, '__rawMarkdown__', '主栏', '#7a8b9a'],
      [1, 2, 2, 1, 'summaryCard', '侧栏', '#9b6bdf'],
      [3, 1, 0, 3, 'textCard', '底栏', '#5eb887'],
    ),
  },
  {
    id: 'tablet-gallery',
    presetId: 'tablet',
    label: "卡片画廊",
    description: "顶栏 + 2×3 栅格 + 底（3×4）",
    cards: cards(
      [3, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [1, 1, 0, 1, 'showcaseCard', '卡1', '#3d8bfd'],
      [1, 1, 1, 1, 'showcaseCard', '卡2', '#3d8bfd'],
      [1, 1, 2, 1, 'showcaseCard', '卡3', '#3d8bfd'],
      [1, 1, 0, 2, 'showcaseCard', '卡4', '#3d8bfd'],
      [1, 1, 1, 2, 'showcaseCard', '卡5', '#3d8bfd'],
      [1, 1, 2, 2, 'showcaseCard', '卡6', '#3d8bfd'],
      [3, 1, 0, 3, 'textCard', '底栏', '#5eb887'],
    ),
  },
  {
    id: 'tablet-dashboard',
    presetId: 'tablet',
    label: "仪表盘",
    description: "侧栏 + KPI + 主区（3×4）",
    cards: cards(
      [1, 4, 0, 0, 'textCard', '侧栏', '#5eb887'],
      [2, 1, 1, 0, 'textCard', '标题', '#5eb887'],
      [1, 1, 1, 1, 'targetStatCard', 'KPI A', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'KPI B', '#e6a23c'],
      [2, 2, 1, 2, 'showcaseCard', '主图', '#3d8bfd'],
    ),
  },
  {
    id: 'desktop-dashboard',
    presetId: 'desktop',
    label: "仪表盘壳",
    description: "侧栏 + KPI + 主图（5×3）",
    cards: cards(
      [1, 3, 0, 0, 'textCard', '侧栏', '#5eb887'],
      [4, 1, 1, 0, 'textCard', '顶栏', '#5eb887'],
      [1, 1, 1, 1, 'targetStatCard', 'KPI A', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'KPI B', '#e6a23c'],
      [1, 1, 3, 1, 'targetStatCard', 'KPI C', '#e6a23c'],
      [1, 1, 4, 1, 'targetStatCard', 'KPI D', '#e6a23c'],
      [2, 1, 1, 2, 'showcaseCard', '主图', '#3d8bfd'],
      [2, 1, 3, 2, '__rawMarkdown__', '明细', '#7a8b9a'],
    ),
  },
  {
    id: 'desktop-holy-grail',
    presetId: 'desktop',
    label: "圣杯布局",
    description: "顶栏 + 侧/主 + 底（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [1, 1, 0, 1, 'summaryCard', '侧栏', '#9b6bdf'],
      [4, 1, 1, 1, '__rawMarkdown__', '主内容', '#7a8b9a'],
      [5, 1, 0, 2, 'textCard', '底栏', '#5eb887'],
    ),
  },
  {
    id: 'desktop-three-col',
    presetId: 'desktop',
    label: "三栏后台",
    description: "顶栏 + 左/中/右 + 底（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [1, 1, 0, 1, 'textCard', '左导航', '#5eb887'],
      [3, 1, 1, 1, '__rawMarkdown__', '主区', '#7a8b9a'],
      [1, 1, 4, 1, 'summaryCard', '右侧栏', '#9b6bdf'],
      [5, 1, 0, 2, 'textCard', '底栏', '#5eb887'],
    ),
  },
  {
    id: 'desktop-magazine',
    presetId: 'desktop',
    label: "杂志分栏",
    description: "顶栏 + 主卡 + 右侧堆叠（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [3, 2, 0, 1, 'heroCard', '大主卡', '#2aa8a0'],
      [2, 1, 3, 1, 'summaryCard', '侧卡上', '#9b6bdf'],
      [2, 1, 3, 2, 'summaryCard', '侧卡下', '#9b6bdf'],
    ),
  },
  {
    id: 'square-holy-grail',
    presetId: 'square',
    label: "圣杯布局",
    description: "顶 + 侧/主 + 底（3×3）",
    cards: cards(
      [3, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [1, 1, 0, 1, 'summaryCard', '侧栏', '#9b6bdf'],
      [2, 1, 1, 1, '__rawMarkdown__', '主区', '#7a8b9a'],
      [3, 1, 0, 2, 'textCard', '底栏', '#5eb887'],
    ),
  },
  {
    id: 'square-dashboard',
    presetId: 'square',
    label: "仪表盘",
    description: "侧栏 + KPI + 主区（3×3）",
    cards: cards(
      [1, 3, 0, 0, 'textCard', '侧栏', '#5eb887'],
      [2, 1, 1, 0, 'textCard', '标题', '#5eb887'],
      [1, 1, 1, 1, 'targetStatCard', 'KPI A', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'KPI B', '#e6a23c'],
      [2, 1, 1, 2, 'showcaseCard', '主图', '#3d8bfd'],
    ),
  },
  {
    id: 'square-gallery',
    presetId: 'square',
    label: "卡片画廊",
    description: "九宫格（3×3）",
    cards: cards(
      [1, 1, 0, 0, 'showcaseCard', '卡1', '#3d8bfd'],
      [1, 1, 1, 0, 'showcaseCard', '卡2', '#3d8bfd'],
      [1, 1, 2, 0, 'showcaseCard', '卡3', '#3d8bfd'],
      [1, 1, 0, 1, 'showcaseCard', '卡4', '#3d8bfd'],
      [1, 1, 1, 1, 'showcaseCard', '卡5', '#3d8bfd'],
      [1, 1, 2, 1, 'showcaseCard', '卡6', '#3d8bfd'],
      [1, 1, 0, 2, 'showcaseCard', '卡7', '#3d8bfd'],
      [1, 1, 1, 2, 'showcaseCard', '卡8', '#3d8bfd'],
      [1, 1, 2, 2, 'showcaseCard', '卡9', '#3d8bfd'],
    ),
  },
  {
    id: 'square-landing',
    presetId: 'square',
    label: "落地页",
    description: "顶栏 + Hero + 双栏（3×3）",
    cards: cards(
      [3, 1, 0, 0, 'textCard', '顶栏', '#5eb887'],
      [3, 1, 0, 1, 'heroCard', 'Hero', '#2aa8a0'],
      [1, 1, 0, 2, 'summaryCard', '左栏', '#9b6bdf'],
      [2, 1, 1, 2, 'summaryCard', '右栏', '#9b6bdf'],
    ),
  },
  // —— 设计稿 ——
  {
    id: 'design-phone-calculus',
    presetId: 'phone',
    label: "设计稿·手机复习",
    description: "目标 + 日程 + CTA（1×3）",
    cards: cards(
      [1, 1, 0, 0, 'targetStatCard', '今日目标', '#e6a23c'],
      [1, 1, 0, 1, '__rawMarkdown__', '复习日程', '#7a8b9a'],
      [1, 1, 0, 2, 'textCard', '开始复习', '#5eb887'],
    ),
  },
  {
    id: 'design-phone-calculus-tight',
    presetId: 'phone',
    label: "设计稿·手机复习(紧凑)",
    description: "头图占两行 + 底栏（1×3）",
    cards: cards(
      [1, 2, 0, 0, 'heroCard', '复习概览', '#2aa8a0'],
      [1, 1, 0, 2, 'textCard', '开始复习', '#5eb887'],
    ),
  },
  {
    id: 'design-desktop-class-over',
    presetId: 'desktop',
    label: "设计稿·课堂结束",
    description: "顶栏 + 4 工具 + 双底卡（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'Well done header', '#5eb887'],
      [1, 1, 0, 1, 'targetStatCard', 'Transcription', '#e6a23c'],
      [1, 1, 1, 1, 'targetStatCard', 'Related files', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'Smart Camera', '#e6a23c'],
      [2, 1, 3, 1, 'targetStatCard', 'Handwriting Space', '#e6a23c'],
      [2, 1, 0, 2, 'showcaseCard', '知识图谱预览', '#3d8bfd'],
      [3, 1, 2, 2, '__rawMarkdown__', '课堂笔记', '#7a8b9a'],
    ),
  },
  {
    id: 'design-tablet-class-over',
    presetId: 'tablet',
    label: "设计稿·课堂结束(平板)",
    description: "平板 3×4",
    cards: cards(
      [3, 1, 0, 0, 'textCard', 'Well done header', '#5eb887'],
      [1, 1, 0, 1, 'targetStatCard', 'Transcription', '#e6a23c'],
      [1, 1, 1, 1, 'targetStatCard', 'Related files', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'Smart Camera', '#e6a23c'],
      [1, 1, 0, 2, 'showcaseCard', '知识图谱', '#3d8bfd'],
      [2, 1, 1, 2, '__rawMarkdown__', '课堂笔记', '#7a8b9a'],
      [3, 1, 0, 3, 'textCard', 'Footer', '#5eb887'],
    ),
  },
  {
    id: 'design-square-class-over',
    presetId: 'square',
    label: "设计稿·课堂结束(方阵)",
    description: "3×3",
    cards: cards(
      [3, 1, 0, 0, 'textCard', 'Well done header', '#5eb887'],
      [1, 1, 0, 1, 'targetStatCard', 'Tool A', '#e6a23c'],
      [1, 1, 1, 1, 'targetStatCard', 'Tool B', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'Tool C', '#e6a23c'],
      [1, 1, 0, 2, 'showcaseCard', '图谱', '#3d8bfd'],
      [2, 1, 1, 2, '__rawMarkdown__', '笔记', '#7a8b9a'],
    ),
  },
  {
    id: 'design-desktop-exam-prep',
    presetId: 'desktop',
    label: "设计稿·备考仪表盘",
    description: "顶栏 + 3 入口 + 三列底（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'Prepare for Math Final', '#5eb887'],
      [2, 1, 0, 1, 'targetStatCard', 'Past Exam Papers', '#e6a23c'],
      [2, 1, 2, 1, 'targetStatCard', 'Error Collection', '#e6a23c'],
      [1, 1, 4, 1, 'targetStatCard', 'Mock Self-test', '#e6a23c'],
      [2, 1, 0, 2, 'showcaseCard', '知识图谱预览', '#3d8bfd'],
      [2, 1, 2, 2, '__rawMarkdown__', "Today's Review Note", '#7a8b9a'],
      [1, 1, 4, 2, 'mistakesCard', 'Weak Spots', '#d9776f'],
    ),
  },
  {
    id: 'design-tablet-exam-prep',
    presetId: 'tablet',
    label: "设计稿·备考(平板)",
    description: "平板 3×4",
    cards: cards(
      [3, 1, 0, 0, 'textCard', 'Prepare for Math Final', '#5eb887'],
      [1, 1, 0, 1, 'targetStatCard', 'Past Papers', '#e6a23c'],
      [1, 1, 1, 1, 'targetStatCard', 'Errors', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'Mock Test', '#e6a23c'],
      [1, 2, 0, 2, 'showcaseCard', '图谱', '#3d8bfd'],
      [1, 2, 1, 2, '__rawMarkdown__', '笔记', '#7a8b9a'],
      [1, 2, 2, 2, 'mistakesCard', 'Weak Spots', '#d9776f'],
    ),
  },
  {
    id: 'design-desktop-exam-prep-v2',
    presetId: 'desktop',
    label: "设计稿·备考(矮顶栏)",
    description: "同备考骨架（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'Prepare for Math Final', '#5eb887'],
      [2, 1, 0, 1, 'targetStatCard', 'Past Exam Papers', '#e6a23c'],
      [2, 1, 2, 1, 'targetStatCard', 'Error Collection', '#e6a23c'],
      [1, 1, 4, 1, 'targetStatCard', 'Mock Self-test', '#e6a23c'],
      [2, 1, 0, 2, 'showcaseCard', '知识图谱预览', '#3d8bfd'],
      [2, 1, 2, 2, '__rawMarkdown__', "Today's Review Note", '#7a8b9a'],
      [1, 1, 4, 2, 'mistakesCard', 'Weak Spots', '#d9776f'],
    ),
  },
  {
    id: 'design-desktop-domain',
    presetId: 'desktop',
    label: "设计稿·Domain 概念页",
    description: "标题 + 双栏（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'The Domain', '#5eb887'],
      [2, 2, 0, 1, 'summaryCard', 'Visualizing Domain', '#9b6bdf'],
      [3, 2, 2, 1, 'summaryCard', 'Input-Output Rule', '#9b6bdf'],
    ),
  },
  {
    id: 'design-tablet-domain',
    presetId: 'tablet',
    label: "设计稿·Domain(平板)",
    description: "平板竖向（3×4）",
    cards: cards(
      [3, 1, 0, 0, 'textCard', 'The Domain', '#5eb887'],
      [1, 2, 0, 1, 'summaryCard', 'Visualizing', '#9b6bdf'],
      [2, 2, 1, 1, 'summaryCard', 'Input-Output', '#9b6bdf'],
      [3, 1, 0, 3, 'textCard', 'CORE DEFINITION', '#5eb887'],
    ),
  },
  {
    id: 'design-square-domain',
    presetId: 'square',
    label: "设计稿·Domain(方阵)",
    description: "3×3",
    cards: cards(
      [3, 1, 0, 0, 'textCard', 'The Domain', '#5eb887'],
      [1, 1, 0, 1, 'summaryCard', 'Visualizing', '#9b6bdf'],
      [2, 1, 1, 1, 'summaryCard', 'Input-Output', '#9b6bdf'],
      [3, 1, 0, 2, 'textCard', 'CORE DEFINITION', '#5eb887'],
    ),
  },
  {
    id: 'design-phone-domain-stack',
    presetId: 'phone',
    label: "设计稿·Domain(手机堆叠)",
    description: "竖屏三行（1×3）",
    cards: cards(
      [1, 1, 0, 0, 'textCard', 'The Domain', '#5eb887'],
      [1, 1, 0, 1, 'textCard', 'CORE DEFINITION', '#5eb887'],
      [1, 1, 0, 2, 'summaryCard', 'Visualizing Domain', '#9b6bdf'],
    ),
  },
  // —— PSUIP ——
  {
    id: 'psuip-class-is-over',
    presetId: 'desktop',
    label: "PSUIP·课堂结束",
    description: "textCard + 4 targetStat + showcase / raw（5×3 @228×216/16）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'Well done header', '#5eb887'],
      [1, 1, 0, 1, 'targetStatCard', 'Transcription', '#e6a23c'],
      [1, 1, 1, 1, 'targetStatCard', 'Related files', '#e6a23c'],
      [1, 1, 2, 1, 'targetStatCard', 'Smart Camera', '#e6a23c'],
      [2, 1, 3, 1, 'targetStatCard', 'Handwriting Space', '#e6a23c'],
      [2, 1, 0, 2, 'showcaseCard', '知识图谱预览', '#3d8bfd'],
      [3, 1, 2, 2, '__rawMarkdown__', '课堂笔记', '#7a8b9a'],
    ),
  },
  {
    id: 'psuip-contents-legend',
    presetId: 'desktop',
    label: "PSUIP·目录与图例",
    description: "标题 + 目录行 + hero（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'CONTENTS', '#5eb887'],
      [5, 1, 0, 1, 'commonStyleServiceListDesc', '1–4 Sections', '#6b8cae'],
      [5, 1, 0, 2, 'heroCard', 'SOURCE LEGEND', '#2aa8a0'],
    ),
  },
  {
    id: 'psuip-functions-notes',
    presetId: 'desktop',
    label: "PSUIP·函数笔记",
    description: "标题 + 笔记（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'Functions & Applications', '#5eb887'],
      [5, 2, 0, 1, '__rawMarkdown__', '笔记正文', '#7a8b9a'],
    ),
  },
  {
    id: 'psuip-math-final',
    presetId: 'desktop',
    label: "PSUIP·期末备考",
    description: "顶栏 + 3 入口 + 三列底（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'Prepare for Math Final', '#5eb887'],
      [2, 1, 0, 1, 'targetStatCard', 'Past Exam Papers', '#e6a23c'],
      [2, 1, 2, 1, 'targetStatCard', 'Error Collection', '#e6a23c'],
      [1, 1, 4, 1, 'targetStatCard', 'Mock Self-test', '#e6a23c'],
      [2, 1, 0, 2, 'showcaseCard', '知识图谱预览', '#3d8bfd'],
      [2, 1, 2, 2, '__rawMarkdown__', "Today's Review Note", '#7a8b9a'],
      [1, 1, 4, 2, 'mistakesCard', 'Weak Spots', '#d9776f'],
    ),
  },
  {
    id: 'psuip-tager',
    presetId: 'desktop',
    label: "PSUIP·单目标卡",
    description: "单张 targetStatCard（5×3）",
    cards: cards(
      [3, 2, 0, 0, 'targetStatCard', 'Master Calculus', '#e6a23c'],
    ),
  },
  {
    id: 'psuip-the-domain',
    presetId: 'desktop',
    label: "PSUIP·Domain 概念",
    description: "双标题 + 双 summary（5×3）",
    cards: cards(
      [5, 1, 0, 0, 'textCard', 'The Domain', '#5eb887'],
      [5, 1, 0, 1, 'textCard', 'CORE DEFINITION', '#5eb887'],
      [2, 1, 0, 2, 'summaryCard', 'Visualizing Domain', '#9b6bdf'],
      [3, 1, 2, 2, 'summaryCard', 'Input-Output Rule', '#9b6bdf'],
    ),
  },
  {
    id: 'psuip-phone-contents-legend',
    presetId: 'phone',
    label: "PSUIP·目录图例(手机)",
    description: "竖屏 1×3",
    cards: cards(
      [1, 1, 0, 0, 'textCard', 'CONTENTS', '#5eb887'],
      [1, 1, 0, 1, 'commonStyleServiceListDesc', 'Sections', '#6b8cae'],
      [1, 1, 0, 2, 'heroCard', 'SOURCE LEGEND', '#2aa8a0'],
    ),
  },
  {
    id: 'psuip-phone-tager',
    presetId: 'phone',
    label: "PSUIP·单目标卡(手机)",
    description: "竖屏目标卡 1×3",
    cards: cards(
      [1, 2, 0, 0, 'targetStatCard', 'Master Calculus', '#e6a23c'],
    ),
  },
  {
    id: 'psuip-phone-the-domain',
    presetId: 'phone',
    label: "PSUIP·Domain(手机)",
    description: "竖屏三行 1×3",
    cards: cards(
      [1, 1, 0, 0, 'textCard', 'The Domain', '#5eb887'],
      [1, 1, 0, 1, 'textCard', 'CORE DEFINITION', '#5eb887'],
      [1, 1, 0, 2, 'summaryCard', 'Visualizing Domain', '#9b6bdf'],
    ),
  },
  {
    id: 'psuip-dashboard-class-over',
    presetId: 'dashboard',
    label: "PSUIP·课堂结束(宽)",
    description: "1880×680 @228×216/16 → 7×3",
    cards: cards(
      [7, 1, 0, 0, 'textCard', 'Well done header', '#5eb887'],
      [2, 1, 0, 1, 'targetStatCard', 'Transcription', '#e6a23c'],
      [2, 1, 2, 1, 'targetStatCard', 'Related files', '#e6a23c'],
      [2, 1, 4, 1, 'targetStatCard', 'Smart Camera', '#e6a23c'],
      [1, 1, 6, 1, 'targetStatCard', 'Handwriting Space', '#e6a23c'],
      [3, 1, 0, 2, 'showcaseCard', '知识图谱预览', '#3d8bfd'],
      [4, 1, 3, 2, '__rawMarkdown__', '课堂笔记', '#7a8b9a'],
    ),
  },
  {
    id: 'psuip-dashboard-math-final',
    presetId: 'dashboard',
    label: "PSUIP·期末备考(宽)",
    description: "宽屏 7×3",
    cards: cards(
      [7, 1, 0, 0, 'textCard', 'Prepare for Math Final', '#5eb887'],
      [2, 1, 0, 1, 'targetStatCard', 'Past Exam Papers', '#e6a23c'],
      [3, 1, 2, 1, 'targetStatCard', 'Error Collection', '#e6a23c'],
      [2, 1, 5, 1, 'targetStatCard', 'Mock Self-test', '#e6a23c'],
      [2, 1, 0, 2, 'showcaseCard', '知识图谱预览', '#3d8bfd'],
      [3, 1, 2, 2, '__rawMarkdown__', "Today's Review Note", '#7a8b9a'],
      [2, 1, 5, 2, 'mistakesCard', 'Weak Spots', '#d9776f'],
    ),
  },
  // —— 8×5 手工标注（handcrafted_layouts.jsonl / min_size_seqs）——
  {
    id: 'hand-1',
    presetId: 'wide8x5',
    label: '8×5 · 1',
    description: '顶栏 + 4 KPI + 左图/中卡/右大卡（1936×1144）',
    cards: cards(
      [8, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [2, 1, 0, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 2, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 4, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 6, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 3, 0, 2, 'showcaseCard', 'showcase', '#3d8bfd'],
      [2, 1, 2, 2, 'showcaseCard', 'showcase', '#3d8bfd'],
      [4, 3, 4, 2, 'contentSummaryCard', 'contentSummary', '#c4785a'],
      [2, 2, 2, 3, 'contentSummaryCard', 'contentSummary', '#c4785a'],
    ),
  },
  {
    id: 'hand-2',
    presetId: 'wide8x5',
    label: '8×5 · 2',
    description: '顶栏 + 左侧栏 + 3 KPI + Topology / 摘要（1936×1144）',
    cards: cards(
      [8, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [2, 4, 0, 1, 'showcaseCard', 'showcase', '#3d8bfd'],
      [2, 1, 2, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 4, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 6, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [3, 3, 2, 2, 'Topology', 'Topology', '#5c6bc0'],
      [3, 3, 5, 2, 'contentSummaryCard', 'contentSummary', '#c4785a'],
    ),
  },
  {
    id: 'hand-3',
    presetId: 'wide8x5',
    label: '8×5 · 3',
    description: '顶栏 + 左侧栏 + 3 KPI + 笔记 / 错题堆叠（1936×1144）',
    cards: cards(
      [8, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [2, 4, 0, 1, 'showcaseCard', 'showcase', '#3d8bfd'],
      [2, 1, 2, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 4, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 6, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [3, 3, 2, 2, '__rawMarkdown__', 'rawMarkdown', '#7a8b9a'],
      [3, 1, 5, 2, 'mistakesCard', 'mistakes', '#d9776f'],
      [3, 1, 5, 3, 'mistakesCard', 'mistakes', '#d9776f'],
      [3, 1, 5, 4, 'mistakesCard', 'mistakes', '#d9776f'],
    ),
  },
  {
    id: 'hand-5',
    presetId: 'wide8x5',
    label: '8×5 · 5',
    description: '顶栏 + 左图 + Topology + 右列 KPI/错题（1936×1144）',
    cards: cards(
      [8, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [2, 4, 0, 1, 'showcaseCard', 'showcase', '#3d8bfd'],
      [3, 4, 2, 1, 'Topology', 'Topology', '#5c6bc0'],
      [3, 1, 5, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [3, 1, 5, 2, 'mistakesCard', 'mistakes', '#d9776f'],
      [3, 1, 5, 3, 'mistakesCard', 'mistakes', '#d9776f'],
      [3, 1, 5, 4, 'mistakesCard', 'mistakes', '#d9776f'],
    ),
  },
  {
    id: 'hand-7',
    presetId: 'wide8x5',
    label: '8×5 · 7',
    description: '顶栏 + 左侧栏 + 双 KPI + 摘要 / 错题（1936×1144）',
    cards: cards(
      [8, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [2, 4, 0, 1, 'showcaseCard', 'showcase', '#3d8bfd'],
      [3, 1, 2, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [3, 1, 5, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [3, 3, 2, 2, 'contentSummaryCard', 'contentSummary', '#c4785a'],
      [3, 1, 5, 2, 'mistakesCard', 'mistakes', '#d9776f'],
      [3, 1, 5, 3, 'mistakesCard', 'mistakes', '#d9776f'],
      [3, 1, 5, 4, 'mistakesCard', 'mistakes', '#d9776f'],
    ),
  },
  {
    id: 'hand-1-1',
    presetId: 'wide8x5',
    label: '8×5 · 1-1',
    description: '顶栏 + 左图 + 笔记 + 右侧 KPI 列（1936×1144）',
    cards: cards(
      [8, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [3, 4, 0, 1, 'showcaseCard', 'showcase', '#3d8bfd'],
      [3, 4, 3, 1, '__rawMarkdown__', 'rawMarkdown', '#7a8b9a'],
      [2, 1, 6, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 6, 2, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 6, 3, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 1, 6, 4, 'targetStatCard', 'targetStat', '#e6a23c'],
    ),
  },
  {
    id: 'hand-22-1',
    presetId: 'tall3x6',
    label: '3×6 · 22-1',
    description: '表格 + 笔记通栏（716×1376）',
    cards: cards(
      [3, 2, 0, 0, '[table:commonStyle]', 'table', '#8a7a5c'],
      [3, 4, 0, 2, '__rawMarkdown__', 'rawMarkdown', '#7a8b9a'],
    ),
  },
  {
    id: 'hand-mu4xh59w-1',
    presetId: 'tall4x6',
    label: '4×6 · 1',
    description: '顶栏 + KPI + 双栏（960×1376）',
    cards: cards(
      [4, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [4, 1, 0, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [2, 4, 0, 2, 'summaryCard', 'summary', '#9b6bdf'],
      [2, 4, 2, 2, 'showcaseCard', 'showcase', '#3d8bfd'],
    ),
  },
  {
    id: 'hand-mu4xh59w-2',
    presetId: 'tall4x6',
    label: '4×6 · 2',
    description: '顶栏 + KPI + Hero（960×1376）',
    cards: cards(
      [4, 1, 0, 0, 'textCard', 'textCard', '#5eb887'],
      [4, 1, 0, 1, 'targetStatCard', 'targetStat', '#e6a23c'],
      [4, 4, 0, 2, 'heroCard', 'heroCard', '#2aa8a0'],
    ),
  },
  {
    id: 'hand-mu4xh59w-3',
    presetId: 'tall4x6',
    label: '4×6 · 3',
    description: '三张 mistakes 通栏（960×1376）',
    cards: cards(
      [4, 2, 0, 0, 'mistakesCard', 'mistakes', '#d9776f'],
      [4, 2, 0, 2, 'mistakesCard', 'mistakes', '#d9776f'],
      [4, 2, 0, 4, 'mistakesCard', 'mistakes', '#d9776f'],
    ),
  },
  {
    id: 'hand-mu4xh59w-4',
    presetId: 'tall4x6',
    label: '4×6 · 4',
    description: '图谱 + 表格（960×1376）',
    cards: cards(
      [4, 4, 0, 0, 'Topology', 'Topology', '#5c6bc0'],
      [4, 2, 0, 4, '[table:commonStyle]', 'table', '#8a7a5c'],
    ),
  },
]

export function sampleLayoutsForPreset(presetId: string): SampleLayout[] {
  return SAMPLE_LAYOUTS.filter((s) => s.presetId === presetId)
}

export function sampleToSequence(sample: SampleLayout): string {
  return stringifyLayoutSequence(sample.cards)
}
