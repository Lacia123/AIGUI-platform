import type { PaletteItem, ResolutionPreset } from './types'
import { CARD_TYPE_COLORS } from './cardTypes'

/** 页面分辨率预设：列/行由单位格 + gap 公式推导，不再写死。 */
export const RESOLUTION_PRESETS: ResolutionPreset[] = [
  {
    id: 'phone',
    label: '手机 390×844',
    width: 390,
    height: 844,
  },
  {
    id: 'tablet',
    label: '平板 768×1024',
    width: 768,
    height: 1024,
  },
  {
    id: 'desktop',
    label: '桌面 1280×800',
    width: 1280,
    height: 800,
  },
  {
    id: 'dashboard',
    label: '仪表盘 1880×680',
    width: 1880,
    height: 680,
  },
  {
    id: 'square',
    label: '方阵 800×800',
    width: 800,
    height: 800,
  },
]

/** 默认预设单位格（可在页面修改）；gap 默认 16 */
export const DEFAULT_CELL_W0 = 80
export const DEFAULT_CELL_H0 = 80
export const DEFAULT_GAP = 16

/** 拖入面板：类型名对齐 CARD_REFERENCE.md */
export const PALETTE_ITEMS: PaletteItem[] = [
  { type: 'textCard', label: 'textCard 4×1', w: 4, h: 1, color: CARD_TYPE_COLORS.textCard },
  { type: 'targetStatCard', label: 'targetStat 3×2', w: 3, h: 2, color: CARD_TYPE_COLORS.targetStatCard },
  { type: 'showcaseCard', label: 'showcase 4×3', w: 4, h: 3, color: CARD_TYPE_COLORS.showcaseCard },
  { type: 'summaryCard', label: 'summary 4×3', w: 4, h: 3, color: CARD_TYPE_COLORS.summaryCard },
  { type: 'mistakesCard', label: 'mistakes 3×3', w: 3, h: 3, color: CARD_TYPE_COLORS.mistakesCard },
  {
    type: 'commonStyleServiceListDesc',
    label: 'serviceList 4×1',
    w: 4,
    h: 1,
    color: CARD_TYPE_COLORS.commonStyleServiceListDesc,
  },
  { type: 'heroCard', label: 'heroCard 6×2', w: 6, h: 2, color: CARD_TYPE_COLORS.heroCard },
  {
    type: 'pairedImageTextCard',
    label: 'pairedMedia 6×3',
    w: 6,
    h: 3,
    color: CARD_TYPE_COLORS.pairedImageTextCard,
  },
  {
    type: '__rawMarkdown__',
    label: 'rawMarkdown 4×4',
    w: 4,
    h: 4,
    color: CARD_TYPE_COLORS.__rawMarkdown__,
  },
  { type: 'Topology', label: 'Topology 4×4', w: 4, h: 4, color: CARD_TYPE_COLORS.Topology },
  {
    type: '[table:commonStyle]',
    label: 'table 6×3',
    w: 6,
    h: 3,
    color: CARD_TYPE_COLORS['[table:commonStyle]'],
  },
]
