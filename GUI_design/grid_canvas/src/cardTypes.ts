/**
 * 与 docx/CARD_REFERENCE.md §0 对齐的 card 类型名与默认色。
 * Slab ×9 + 透传伪卡（table / rawMarkdown / Topology）。
 */
export const SLAB_CARD_TYPES = [
  'targetStatCard',
  'mistakesCard',
  'showcaseCard',
  'summaryCard',
  'textCard',
  'commonStyleServiceListDesc',
  'pairedImageTextCard',
  'heroCard',
  'contentSummaryCard',
] as const

export const PASSTHROUGH_CARD_TYPES = [
  '[table:commonStyle]',
  '__rawMarkdown__',
  'Topology',
] as const

export type SlabCardType = (typeof SLAB_CARD_TYPES)[number]
export type PassthroughCardType = (typeof PASSTHROUGH_CARD_TYPES)[number]
export type SupportedCardType = SlabCardType | PassthroughCardType

export const CARD_TYPE_COLORS: Record<SupportedCardType, string> = {
  targetStatCard: '#e6a23c',
  mistakesCard: '#d9776f',
  showcaseCard: '#3d8bfd',
  summaryCard: '#9b6bdf',
  textCard: '#5eb887',
  commonStyleServiceListDesc: '#6b8cae',
  pairedImageTextCard: '#4a90a4',
  heroCard: '#2aa8a0',
  contentSummaryCard: '#c4785a',
  '[table:commonStyle]': '#8a7a5c',
  __rawMarkdown__: '#7a8b9a',
  Topology: '#5c6bc0',
}

export function cardTypeColor(type: string): string {
  return CARD_TYPE_COLORS[type as SupportedCardType] ?? '#3d8bfd'
}
