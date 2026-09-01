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

/** 色值对齐 cardTypes.ts / CARD_REFERENCE.md */
const C = {
  text: '#5eb887',
  stat: '#e6a23c',
  showcase: '#3d8bfd',
  mistakes: '#d9776f',
  summary: '#9b6bdf',
  hero: '#2aa8a0',
  service: '#6b8cae',
  raw: '#7a8b9a',
  topology: '#5c6bc0',
  table: '#8a7a5c',
  paired: '#4a90a4',
} as const

/**
 * 全部样例统一按「预设单位格 80 × gap/pad 16」推导网格后铺格：
 *   phone 390×844 → 4×8
 *   tablet 768×1024 → 8×10
 *   desktop 1280×800 → 13×8
 *   dashboard 1880×680 → 19×7
 *   square 800×800 → 8×8
 * 元组：(w,h,x,y) 或 (w,h,x,y,type,label,color)
 */
export const SAMPLE_LAYOUTS: SampleLayout[] = [
  // —— 手机 4×8 ——
  {
    id: 'phone-feed',
    presetId: 'phone',
    label: '信息流',
    description: '顶栏 + 列表行 + 底栏（4×8）',
    cards: cards(
      [4, 1, 0, 0],
      [4, 1, 0, 1],
      [4, 1, 0, 2],
      [4, 1, 0, 3],
      [4, 1, 0, 4],
      [4, 1, 0, 5],
      [4, 1, 0, 6],
      [4, 1, 0, 7],
    ),
  },
  {
    id: 'phone-landing',
    presetId: 'phone',
    label: '落地页',
    description: '顶栏 + Hero + 2×2 功能卡 + CTA',
    cards: cards(
      [4, 1, 0, 0],
      [4, 2, 0, 1],
      [2, 2, 0, 3],
      [2, 2, 2, 3],
      [2, 2, 0, 5],
      [2, 2, 2, 5],
      [4, 1, 0, 7],
    ),
  },
  {
    id: 'phone-profile',
    presetId: 'phone',
    label: '个人主页',
    description: '头图 + KPI + 内容块',
    cards: cards(
      [4, 1, 0, 0],
      [4, 2, 0, 1],
      [2, 1, 0, 3],
      [2, 1, 2, 3],
      [4, 2, 0, 4],
      [4, 2, 0, 6],
    ),
  },

  // —— 平板 8×10 ——
  {
    id: 'tablet-blog',
    presetId: 'tablet',
    label: '双栏博客',
    description: '顶栏 + 主栏/侧栏 + 底栏',
    cards: cards(
      [8, 1, 0, 0],
      [5, 8, 0, 1],
      [3, 8, 5, 1],
      [8, 1, 0, 9],
    ),
  },
  {
    id: 'tablet-gallery',
    presetId: 'tablet',
    label: '卡片画廊',
    description: '顶栏 + 2×4 栅格 + 底栏',
    cards: cards(
      [8, 1, 0, 0],
      [2, 2, 0, 1],
      [2, 2, 2, 1],
      [2, 2, 4, 1],
      [2, 2, 6, 1],
      [2, 2, 0, 3],
      [2, 2, 2, 3],
      [2, 2, 4, 3],
      [2, 2, 6, 3],
      [2, 2, 0, 5],
      [2, 2, 2, 5],
      [2, 2, 4, 5],
      [2, 2, 6, 5],
      [2, 2, 0, 7],
      [2, 2, 2, 7],
      [2, 2, 4, 7],
      [2, 2, 6, 7],
      [8, 1, 0, 9],
    ),
  },
  {
    id: 'tablet-dashboard',
    presetId: 'tablet',
    label: '仪表盘',
    description: '侧栏 + KPI + 图表/明细',
    cards: cards(
      [2, 10, 0, 0],
      [6, 1, 2, 0],
      [2, 1, 2, 1],
      [2, 1, 4, 1],
      [2, 1, 6, 1],
      [4, 6, 2, 2],
      [2, 6, 6, 2],
      [6, 2, 2, 8],
    ),
  },

  // —— 桌面 13×8 ——
  {
    id: 'desktop-dashboard',
    presetId: 'desktop',
    label: '仪表盘壳',
    description: '侧栏 + KPI + 主图/侧栏 + 底表',
    cards: cards(
      [2, 8, 0, 0],
      [11, 1, 2, 0],
      [3, 1, 2, 1],
      [3, 1, 5, 1],
      [2, 1, 8, 1],
      [3, 1, 10, 1],
      [7, 5, 2, 2],
      [4, 5, 9, 2],
      [11, 1, 2, 7],
    ),
  },
  {
    id: 'desktop-holy-grail',
    presetId: 'desktop',
    label: '圣杯布局',
    description: '顶栏 + 侧栏/主内容 + 底栏',
    cards: cards(
      [13, 1, 0, 0],
      [3, 6, 0, 1],
      [10, 6, 3, 1],
      [13, 1, 0, 7],
    ),
  },
  {
    id: 'desktop-three-col',
    presetId: 'desktop',
    label: '三栏后台',
    description: '顶栏 + 左导航/主区/右 aside + 底栏',
    cards: cards(
      [13, 1, 0, 0],
      [2, 6, 0, 1],
      [8, 6, 2, 1],
      [3, 6, 10, 1],
      [13, 1, 0, 7],
    ),
  },
  {
    id: 'desktop-magazine',
    presetId: 'desktop',
    label: '杂志分栏',
    description: '顶栏 + 大主卡 + 右侧堆叠 + 底栏',
    cards: cards(
      [13, 1, 0, 0],
      [8, 6, 0, 1],
      [5, 3, 8, 1],
      [5, 3, 8, 4],
      [13, 1, 0, 7],
    ),
  },

  // —— 方阵 8×8 ——
  {
    id: 'square-holy-grail',
    presetId: 'square',
    label: '圣杯布局',
    description: '顶栏 + 侧栏/主区 + 底栏',
    cards: cards(
      [8, 1, 0, 0],
      [2, 6, 0, 1],
      [6, 6, 2, 1],
      [8, 1, 0, 7],
    ),
  },
  {
    id: 'square-dashboard',
    presetId: 'square',
    label: '仪表盘',
    description: '侧栏 + KPI + 图表/明细',
    cards: cards(
      [2, 8, 0, 0],
      [6, 1, 2, 0],
      [2, 1, 2, 1],
      [2, 1, 4, 1],
      [2, 1, 6, 1],
      [4, 5, 2, 2],
      [2, 5, 6, 2],
      [6, 1, 2, 7],
    ),
  },
  {
    id: 'square-gallery',
    presetId: 'square',
    label: '卡片画廊',
    description: '顶栏 + 2×3 栅格 + 底栏',
    cards: cards(
      [8, 1, 0, 0],
      [2, 2, 0, 1],
      [2, 2, 2, 1],
      [2, 2, 4, 1],
      [2, 2, 6, 1],
      [2, 2, 0, 3],
      [2, 2, 2, 3],
      [2, 2, 4, 3],
      [2, 2, 6, 3],
      [2, 2, 0, 5],
      [2, 2, 2, 5],
      [2, 2, 4, 5],
      [2, 2, 6, 5],
      [8, 1, 0, 7],
    ),
  },
  {
    id: 'square-landing',
    presetId: 'square',
    label: '落地页',
    description: '顶栏 + Hero + 双栏 + 底栏',
    cards: cards(
      [8, 1, 0, 0],
      [8, 2, 0, 1],
      [4, 4, 0, 3],
      [4, 4, 4, 3],
      [8, 1, 0, 7],
    ),
  },

  // —— 设计稿（80/16）——
  {
    id: 'design-phone-calculus',
    presetId: 'phone',
    label: '设计稿·手机复习',
    description: '目标卡 + 日程 + 提醒 + CTA（4×8）',
    cards: cards(
      [4, 2, 0, 0],
      [4, 3, 0, 2],
      [4, 1, 0, 5],
      [4, 2, 0, 6],
    ),
  },
  {
    id: 'design-desktop-class-over',
    presetId: 'desktop',
    label: '设计稿·课堂结束',
    description: '顶栏 + 4 工具 + 左图谱/右笔记（13×8）',
    cards: cards(
      [13, 1, 0, 0],
      [3, 2, 0, 1],
      [3, 2, 3, 1],
      [3, 2, 6, 1],
      [4, 2, 9, 1],
      [5, 5, 0, 3],
      [8, 5, 5, 3],
    ),
  },
  {
    id: 'design-desktop-exam-prep',
    presetId: 'desktop',
    label: '设计稿·备考仪表盘',
    description: '顶栏 + 入口行 + 三列大卡',
    cards: cards(
      [13, 1, 0, 0],
      [3, 2, 0, 1],
      [3, 2, 3, 1],
      [3, 2, 6, 1],
      [4, 2, 9, 1],
      [4, 5, 0, 3],
      [5, 5, 4, 3],
      [4, 5, 9, 3],
    ),
  },
  {
    id: 'design-desktop-domain',
    presetId: 'desktop',
    label: '设计稿·Domain',
    description: '标题 + 双栏 + 底栏',
    cards: cards(
      [13, 2, 0, 0],
      [6, 4, 0, 2],
      [7, 4, 6, 2],
      [13, 2, 0, 6],
    ),
  },

  // —— PSUIP（desktop 13×8 / phone 4×8 / dashboard 19×7）——
  {
    id: 'psuip-class-is-over',
    presetId: 'desktop',
    label: 'PSUIP·课堂结束',
    description: 'textCard + 4 targetStat + showcaseCard / __rawMarkdown__',
    cards: cards(
      [13, 1, 0, 0, 'textCard', 'Well done header', C.text],
      [3, 2, 0, 1, 'targetStatCard', 'Transcription', C.stat],
      [3, 2, 3, 1, 'targetStatCard', 'Related files', C.stat],
      [3, 2, 6, 1, 'targetStatCard', 'Smart Camera', C.stat],
      [4, 2, 9, 1, 'targetStatCard', 'Handwriting Space', C.stat],
      [5, 5, 0, 3, 'showcaseCard', '知识图谱预览', C.showcase],
      [8, 5, 5, 3, '__rawMarkdown__', '课堂笔记', C.raw],
    ),
  },
  {
    id: 'psuip-contents-legend',
    presetId: 'desktop',
    label: 'PSUIP·目录与图例',
    description: 'textCard + 4× commonStyleServiceListDesc + heroCard',
    cards: cards(
      [13, 1, 0, 0, 'textCard', 'CONTENTS', C.text],
      [13, 1, 0, 1, 'commonStyleServiceListDesc', '1 Definition', C.service],
      [13, 1, 0, 2, 'commonStyleServiceListDesc', '2 Properties', C.service],
      [13, 1, 0, 3, 'commonStyleServiceListDesc', '3 Applications', C.service],
      [13, 1, 0, 4, 'commonStyleServiceListDesc', '4 Visual Data', C.service],
      [13, 3, 0, 5, 'heroCard', 'SOURCE LEGEND', C.hero],
    ),
  },
  {
    id: 'psuip-functions-notes',
    presetId: 'desktop',
    label: 'PSUIP·函数笔记',
    description: 'textCard + __rawMarkdown__ 通栏',
    cards: cards(
      [13, 2, 0, 0, 'textCard', 'Functions & Applications', C.text],
      [13, 6, 0, 2, '__rawMarkdown__', '笔记正文', C.raw],
    ),
  },
  {
    id: 'psuip-math-final',
    presetId: 'desktop',
    label: 'PSUIP·期末备考',
    description: '顶栏 + 3 入口 + showcase / raw / mistakes',
    cards: cards(
      [13, 1, 0, 0, 'textCard', 'Prepare for Math Final', C.text],
      [4, 2, 0, 1, 'targetStatCard', 'Past Exam Papers', C.stat],
      [5, 2, 4, 1, 'targetStatCard', 'Error Collection', C.stat],
      [4, 2, 9, 1, 'targetStatCard', 'Mock Self-test', C.stat],
      [4, 5, 0, 3, 'showcaseCard', '知识图谱预览', C.showcase],
      [5, 5, 4, 3, '__rawMarkdown__', "Today's Review Note", C.raw],
      [4, 5, 9, 3, 'mistakesCard', 'Weak Spots', C.mistakes],
    ),
  },
  {
    id: 'psuip-tager',
    presetId: 'desktop',
    label: 'PSUIP·单目标卡',
    description: '单张 targetStatCard',
    cards: cards([9, 3, 2, 2, 'targetStatCard', 'Master Calculus', C.stat]),
  },
  {
    id: 'psuip-the-domain',
    presetId: 'desktop',
    label: 'PSUIP·Domain 概念',
    description: '双 textCard + 双 summaryCard',
    cards: cards(
      [13, 2, 0, 0, 'textCard', 'The Domain', C.text],
      [13, 2, 0, 2, 'textCard', 'CORE DEFINITION', C.text],
      [6, 4, 0, 4, 'summaryCard', 'Visualizing Domain', C.summary],
      [7, 4, 6, 4, 'summaryCard', 'Input-Output Rule', C.summary],
    ),
  },
  {
    id: 'psuip-phone-contents-legend',
    presetId: 'phone',
    label: 'PSUIP·目录图例',
    description: '竖屏目录 + 图例（4×8）',
    cards: cards(
      [4, 1, 0, 0, 'textCard', 'CONTENTS', C.text],
      [4, 1, 0, 1, 'commonStyleServiceListDesc', '1 Definition', C.service],
      [4, 1, 0, 2, 'commonStyleServiceListDesc', '2 Properties', C.service],
      [4, 1, 0, 3, 'commonStyleServiceListDesc', '3 Applications', C.service],
      [4, 1, 0, 4, 'commonStyleServiceListDesc', '4 Visual Data', C.service],
      [4, 3, 0, 5, 'heroCard', 'SOURCE LEGEND', C.hero],
    ),
  },
  {
    id: 'psuip-phone-tager',
    presetId: 'phone',
    label: 'PSUIP·单目标卡',
    description: '竖屏通栏目标卡',
    cards: cards([4, 3, 0, 2, 'targetStatCard', 'Master Calculus', C.stat]),
  },
  {
    id: 'psuip-phone-the-domain',
    presetId: 'phone',
    label: 'PSUIP·Domain',
    description: '竖屏 Domain 堆叠',
    cards: cards(
      [4, 1, 0, 0, 'textCard', 'The Domain', C.text],
      [4, 1, 0, 1, 'textCard', 'CORE DEFINITION', C.text],
      [4, 3, 0, 2, 'summaryCard', 'Visualizing Domain', C.summary],
      [4, 3, 0, 5, 'summaryCard', 'Input-Output Rule', C.summary],
    ),
  },

  // —— 仪表盘 19×7（宽屏）——
  {
    id: 'psuip-dashboard-class-over',
    presetId: 'dashboard',
    label: 'PSUIP·课堂结束(宽)',
    description: '1880×680 @80/16 → 19×7',
    cards: cards(
      [19, 1, 0, 0, 'textCard', 'Well done header', C.text],
      [5, 2, 0, 1, 'targetStatCard', 'Transcription', C.stat],
      [5, 2, 5, 1, 'targetStatCard', 'Related files', C.stat],
      [5, 2, 10, 1, 'targetStatCard', 'Smart Camera', C.stat],
      [4, 2, 15, 1, 'targetStatCard', 'Handwriting Space', C.stat],
      [8, 4, 0, 3, 'showcaseCard', '知识图谱预览', C.showcase],
      [11, 4, 8, 3, '__rawMarkdown__', '课堂笔记', C.raw],
    ),
  },
  {
    id: 'psuip-dashboard-math-final',
    presetId: 'dashboard',
    label: 'PSUIP·期末备考(宽)',
    description: '宽屏三入口 + 三列内容',
    cards: cards(
      [19, 1, 0, 0, 'textCard', 'Prepare for Math Final', C.text],
      [6, 2, 0, 1, 'targetStatCard', 'Past Exam Papers', C.stat],
      [7, 2, 6, 1, 'targetStatCard', 'Error Collection', C.stat],
      [6, 2, 13, 1, 'targetStatCard', 'Mock Self-test', C.stat],
      [6, 4, 0, 3, 'showcaseCard', '知识图谱预览', C.showcase],
      [7, 4, 6, 3, '__rawMarkdown__', "Today's Review Note", C.raw],
      [6, 4, 13, 3, 'mistakesCard', 'Weak Spots', C.mistakes],
    ),
  },
]

export function sampleLayoutsForPreset(presetId: string): SampleLayout[] {
  return SAMPLE_LAYOUTS.filter((s) => s.presetId === presetId)
}

export function sampleLayoutSequence(sample: SampleLayout): string {
  return stringifyLayoutSequence(sample.cards)
}
