import type { PaletteItem, ResolutionPreset } from './types'
import { CARD_TYPE_COLORS } from './cardTypes'

/** 默认预设单位格；gap 默认 16。cols/rows = floor((page+gap)/(cell+gap))。 */
export const DEFAULT_CELL_W0 = 228
export const DEFAULT_CELL_H0 = 216
export const DEFAULT_GAP = 16

/** 页面分辨率预设：固定设备像素，格子数随 228×216/16 重算。 */
export const RESOLUTION_PRESETS: ResolutionPreset[] = [
  {
    id: 'phone',
    label: '手机 390×844（1×3）',
    width: 390,
    height: 844,
  },
  {
    id: 'tablet',
    label: '平板 768×1024（3×4）',
    width: 768,
    height: 1024,
  },
  {
    id: 'desktop',
    label: '桌面 1280×800（5×3）',
    width: 1280,
    height: 800,
  },
  {
    id: 'dashboard',
    label: '仪表盘 1880×680（7×3）',
    width: 1880,
    height: 680,
  },
  {
    id: 'square',
    label: '方阵 800×800（3×3）',
    width: 800,
    height: 800,
  },
  {
    id: 'wide8x5',
    label: '宽屏 1936×1144（8×5）',
    width: 1936,
    height: 1144,
  },
  {
    id: 'tall3x6',
    label: '竖屏 716×1376（3×6）',
    width: 716,
    height: 1376,
  },
  {
    id: 'tall4x6',
    label: '竖屏 960×1376（4×6）',
    width: 960,
    height: 1376,
  },
]

/**
 * 拖入面板默认格数 = 样例文本在 8×5 上界下的最小可展示尺寸
 * （markdown-grid-growth-check / card_type_samples.json）。
 */
export const PALETTE_ITEMS: PaletteItem[] = [
  { type: 'textCard', label: 'textCard 2×1', w: 2, h: 1, color: CARD_TYPE_COLORS.textCard },
  { type: 'targetStatCard', label: 'targetStat 1×2', w: 1, h: 2, color: CARD_TYPE_COLORS.targetStatCard },
  { type: 'showcaseCard', label: 'showcase 3×3', w: 3, h: 3, color: CARD_TYPE_COLORS.showcaseCard },
  { type: 'summaryCard', label: 'summary 2×1', w: 2, h: 1, color: CARD_TYPE_COLORS.summaryCard },
  {
    type: 'contentSummaryCard',
    label: 'contentSummary 2×2',
    w: 2,
    h: 2,
    color: CARD_TYPE_COLORS.contentSummaryCard,
  },
  { type: 'mistakesCard', label: 'mistakes 1×2', w: 1, h: 2, color: CARD_TYPE_COLORS.mistakesCard },
  {
    type: 'commonStyleServiceListDesc',
    label: 'serviceList 2×1',
    w: 2,
    h: 1,
    color: CARD_TYPE_COLORS.commonStyleServiceListDesc,
  },
  { type: 'heroCard', label: 'heroCard 2×2', w: 2, h: 2, color: CARD_TYPE_COLORS.heroCard },
  {
    type: 'pairedImageTextCard',
    label: 'pairedMedia 3×3',
    w: 3,
    h: 3,
    color: CARD_TYPE_COLORS.pairedImageTextCard,
  },
  {
    type: '__rawMarkdown__',
    label: 'rawMarkdown 1×2',
    w: 1,
    h: 2,
    color: CARD_TYPE_COLORS.__rawMarkdown__,
  },
  { type: 'Topology', label: 'Topology 1×1', w: 1, h: 1, color: CARD_TYPE_COLORS.Topology },
  {
    type: '[table:commonStyle]',
    label: 'table 2×2',
    w: 2,
    h: 2,
    color: CARD_TYPE_COLORS['[table:commonStyle]'],
  },
]
