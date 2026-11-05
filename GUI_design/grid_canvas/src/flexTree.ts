/**
 * 把网格卡 (x,y,w,h) 切成 GUI_design2 的有序 row/column 树。
 * 用断头台分割：先找不穿过任何卡的水平/垂直切割，再递归。
 * flex 权重取子树包围盒的格数，渲染时比例与原网格一致。
 */

import { sortCardsReadingOrder } from './layoutFormat'

export type FlexCard = {
  id?: string
  type?: string
  label?: string
  color?: string
  x: number
  y: number
  w: number
  h: number
}

export type BBox = { x: number; y: number; w: number; h: number }

export type FlexCardNode = {
  kind: 'card'
  cardIndex: number
  card: FlexCard
  flex: number
  bbox: BBox
}

export type FlexContainerNode = {
  kind: 'row' | 'column'
  children: FlexNode[]
  flex: number
  bbox: BBox
}

export type FlexNode = FlexCardNode | FlexContainerNode

/** GUI_design2 训练 AST（不含几何）。 */
export type Layout2Node =
  | { kind: 'card'; cardIndex: number }
  | { kind: 'row' | 'column'; children: Layout2Node[] }

export type Layout2Episode = {
  id: string
  label?: string
  description?: string
  presetId?: string
  cards: Array<{
    id: string
    type: string
    label?: string
    color?: string
  }>
  actions: Array<'OPEN_ROW' | 'OPEN_COLUMN' | 'PLACE_CARD' | 'CLOSE'>
  layout: Layout2Node
  psuip: string
}

function bboxOf(items: FlexCard[]): BBox {
  const x = Math.min(...items.map((i) => i.x))
  const y = Math.min(...items.map((i) => i.y))
  const right = Math.max(...items.map((i) => i.x + i.w))
  const bottom = Math.max(...items.map((i) => i.y + i.h))
  return { x, y, w: right - x, h: bottom - y }
}

function startOf(it: FlexCard, axis: 'x' | 'y'): number {
  return axis === 'x' ? it.x : it.y
}

function sizeOf(it: FlexCard, axis: 'x' | 'y'): number {
  return axis === 'x' ? it.w : it.h
}

/** 沿 axis 找不穿过任何卡的切割，分成 2+ 条带。 */
function splitBands(items: FlexCard[], axis: 'x' | 'y'): FlexCard[][] | null {
  if (items.length <= 1) return null
  const edges = [
    ...new Set(items.flatMap((it) => [startOf(it, axis), startOf(it, axis) + sizeOf(it, axis)])),
  ].sort((a, b) => a - b)
  const cuts: number[] = []
  for (const edge of edges) {
    if (edge === edges[0] || edge === edges[edges.length - 1]) continue
    const crossed = items.some(
      (it) => startOf(it, axis) < edge && startOf(it, axis) + sizeOf(it, axis) > edge,
    )
    if (!crossed) cuts.push(edge)
  }
  if (cuts.length === 0) return null
  const bounds = [edges[0], ...cuts, edges[edges.length - 1]]
  const bands: FlexCard[][] = []
  for (let i = 0; i < bounds.length - 1; i++) {
    const a = bounds[i]
    const b = bounds[i + 1]
    const band = items.filter(
      (it) => startOf(it, axis) >= a && startOf(it, axis) + sizeOf(it, axis) <= b,
    )
    if (band.length) bands.push(band)
  }
  return bands.length >= 2 ? bands : null
}

function cardNode(card: FlexCard, index: number): FlexCardNode {
  return {
    kind: 'card',
    cardIndex: index,
    card,
    flex: 1,
    bbox: { x: card.x, y: card.y, w: card.w, h: card.h },
  }
}

/** 无法断头台分割时：同行成 row，再竖排成 column。 */
function fallback(items: FlexCard[], indexOf: Map<FlexCard, number>): FlexNode {
  const sorted = [...items].sort((a, b) => a.y - b.y || a.x - b.x)
  const rows: FlexCard[][] = []
  for (const it of sorted) {
    const last = rows[rows.length - 1]
    if (last && last[0].y === it.y && last[0].h === it.h) last.push(it)
    else rows.push([it])
  }
  const box = bboxOf(items)
  if (rows.length === 1) {
    const row = rows[0]
    if (row.length === 1) return cardNode(row[0], indexOf.get(row[0]) ?? 0)
    return {
      kind: 'row',
      flex: 1,
      bbox: box,
      children: row.map((c) => ({ ...cardNode(c, indexOf.get(c) ?? 0), flex: c.w })),
    }
  }
  return {
    kind: 'column',
    flex: 1,
    bbox: box,
    children: rows.map((row) => {
      const inner = fallback(row, indexOf)
      return { ...inner, flex: bboxOf(row).h }
    }),
  }
}

function build(items: FlexCard[], indexOf: Map<FlexCard, number>): FlexNode {
  if (items.length === 1) return cardNode(items[0], indexOf.get(items[0]) ?? 0)

  const hBands = splitBands(items, 'y')
  const vBands = splitBands(items, 'x')

  let bands = hBands
  let kind: 'row' | 'column' = 'column'
  if (hBands && vBands) {
    if (vBands.length > hBands.length) {
      bands = vBands
      kind = 'row'
    }
  } else if (vBands) {
    bands = vBands
    kind = 'row'
  } else if (!hBands) {
    return fallback(items, indexOf)
  }

  const box = bboxOf(items)
  const children = (bands ?? []).map((band) => {
    const child = build(band, indexOf)
    const flex = kind === 'row' ? child.bbox.w : child.bbox.h
    return { ...child, flex }
  })
  return { kind, children, flex: 1, bbox: box }
}

/** 网格卡 → 有序 row/column 树。根始终是容器。 */
export function cardsToFlexTree(cards: FlexCard[]): FlexContainerNode {
  if (cards.length === 0) {
    return { kind: 'column', children: [], flex: 1, bbox: { x: 0, y: 0, w: 0, h: 0 } }
  }
  const ordered = sortCardsReadingOrder(cards)
  const indexOf = new Map<FlexCard, number>()
  ordered.forEach((c, i) => indexOf.set(c, i))
  const inner = build(ordered, indexOf)
  if (inner.kind === 'card') {
    return {
      kind: 'column',
      children: [inner],
      flex: 1,
      bbox: inner.bbox,
    }
  }
  return inner
}

export function toLayout2Ast(node: FlexNode): Layout2Node {
  if (node.kind === 'card') return { kind: 'card', cardIndex: node.cardIndex }
  return { kind: node.kind, children: node.children.map(toLayout2Ast) }
}

export function toLayout2Actions(
  node: FlexContainerNode,
): Array<'OPEN_ROW' | 'OPEN_COLUMN' | 'PLACE_CARD' | 'CLOSE'> {
  const actions: Array<'OPEN_ROW' | 'OPEN_COLUMN' | 'PLACE_CARD' | 'CLOSE'> = []
  function walk(n: FlexNode, isRoot: boolean) {
    if (n.kind === 'card') {
      actions.push('PLACE_CARD')
      return
    }
    if (!isRoot) actions.push(n.kind === 'row' ? 'OPEN_ROW' : 'OPEN_COLUMN')
    for (const child of n.children) walk(child, false)
    if (!isRoot) actions.push('CLOSE')
  }
  walk(node, true)
  return actions
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function indent(level: number): string {
  return '  '.repeat(level)
}

function stringifyNode(node: FlexNode, level: number): string {
  if (node.kind === 'card') {
    const type = node.card.type || 'card'
    const label = node.card.label || type
    return `${indent(level)}<${type}>\n${indent(level + 1)}<label>${escapeXml(label)}</label>\n${indent(level)}</${type}>`
  }
  const open = `${indent(level)}<layout:${node.kind} alignItems="stretch">`
  const close = `${indent(level)}</layout:${node.kind}>`
  const body = node.children.map((c) => stringifyNode(c, level + 1)).join('\n')
  return `${open}\n${body}\n${close}`
}

/** 写成 GUI_design2 的 layout:row / layout:column PSUIP。 */
export function toLayout2Psuip(node: FlexContainerNode): string {
  return `<layout:root>\n${stringifyNode(node, 1)}\n</layout:root>\n`
}

export function cardsToLayout2Episode(
  cards: FlexCard[],
  meta: { id: string; label?: string; description?: string; presetId?: string },
): Layout2Episode {
  const tree = cardsToFlexTree(cards)
  const ordered = sortCardsReadingOrder(cards)
  return {
    id: meta.id,
    label: meta.label,
    description: meta.description,
    presetId: meta.presetId,
    cards: ordered.map((c, i) => ({
      id: c.id || `c${i}`,
      type: c.type || 'card',
      label: c.label,
      color: c.color,
    })),
    actions: toLayout2Actions(tree),
    layout: toLayout2Ast(tree),
    psuip: toLayout2Psuip(tree),
  }
}
