import { canPlace, inBounds } from './gridUtils'
import { cardTypeColor } from './cardTypes'
import type { GridItem } from './types'

/** 布局序列中单张卡片：(w, h, x, y[, type]) */
export type LayoutCard = {
  w: number
  h: number
  x: number
  y: number
  type?: string
}

export type ParseLayoutOptions = {
  /** 网格列数；提供后校验不越界 */
  cols?: number
  /** 网格行数；提供后校验不越界 */
  rows?: number
  /** 是否检测卡片两两重叠，默认 true（在提供 cols/rows 或可推断时） */
  checkOverlap?: boolean
}

export type ParseLayoutResult = {
  cards: LayoutCard[]
  /** 序列头 `grid:CxR` 解析出的画布格数 */
  grid?: { cols: number; rows: number }
  /** 非致命问题（如空序列） */
  warnings: string[]
}

export class LayoutFormatError extends Error {
  constructor(
    message: string,
    readonly index?: number,
    readonly raw?: string,
  ) {
    super(message)
    this.name = 'LayoutFormatError'
  }
}

/** 可选头：grid:13x8; */
const GRID_HEADER_RE = /^\s*grid\s*:\s*(\d+)\s*[x×X]\s*(\d+)\s*;?\s*/

/**
 * 匹配 (w,h,x,y) 或 (w,h,x,y,"type") / (w,h,x,y,'type') / (w,h,x,y,typeId)
 */
const CARD_RE =
  /\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)(?:\s*,\s*(?:"([^"]*)"|'([^']*)'|([^\s,)]+)))?\s*\)/g

function splitGridHeader(text: string): {
  grid?: { cols: number; rows: number }
  body: string
} {
  const m = text.match(GRID_HEADER_RE)
  if (!m) return { body: text }
  return {
    grid: { cols: Number(m[1]), rows: Number(m[2]) },
    body: text.slice(m[0].length),
  }
}

/**
 * 解析布局序列字符串。
 *
 * 可选头：`grid:13x8;`
 * 单卡：`(w,h,x,y)` 或 `(w,h,x,y,"type")`
 */
export function parseLayoutSequence(
  input: string,
  options: ParseLayoutOptions = {},
): ParseLayoutResult {
  const text = input.trim()
  const warnings: string[] = []

  if (!text) {
    return { cards: [], warnings: ['empty layout sequence'] }
  }

  const { grid, body: rawBody } = splitGridHeader(text)
  const body = rawBody.replace(/^\s*\[/, '').replace(/\]\s*$/, '')
  const checkCols = options.cols ?? grid?.cols
  const checkRows = options.rows ?? grid?.rows

  const residual = body
    .replace(CARD_RE, '')
    .replace(/[\s,;|]+/g, '')
  CARD_RE.lastIndex = 0

  if (residual.length > 0) {
    throw new LayoutFormatError(
      `invalid layout sequence: unexpected token near "${residual.slice(0, 24)}"`,
      undefined,
      input,
    )
  }

  const cards: LayoutCard[] = []
  let match: RegExpExecArray | null
  let index = 0
  while ((match = CARD_RE.exec(body)) !== null) {
    const w = Number(match[1])
    const h = Number(match[2])
    const x = Number(match[3])
    const y = Number(match[4])
    const type = match[5] ?? match[6] ?? match[7] ?? undefined
    const raw = match[0]

    if (![w, h, x, y].every(Number.isInteger)) {
      throw new LayoutFormatError(`non-integer values in ${raw}`, index, raw)
    }
    if (w <= 0 || h <= 0) {
      throw new LayoutFormatError(`w and h must be positive in ${raw}`, index, raw)
    }
    if (x < 0 || y < 0) {
      throw new LayoutFormatError(`x and y must be >= 0 in ${raw}`, index, raw)
    }

    if (checkCols !== undefined && checkRows !== undefined) {
      if (!inBounds(x, y, w, h, checkCols, checkRows)) {
        throw new LayoutFormatError(
          `card ${raw} out of bounds on ${checkCols}×${checkRows} grid`,
          index,
          raw,
        )
      }
    }

    cards.push(type ? { w, h, x, y, type } : { w, h, x, y })
    index += 1
  }

  if (cards.length === 0) {
    throw new LayoutFormatError(
      'no cards found; expected grid:CxR; and/or tokens like (w,h,x,y,"type")',
      undefined,
      input,
    )
  }

  const checkOverlap = options.checkOverlap !== false
  if (checkOverlap) {
    for (let i = 0; i < cards.length; i++) {
      const a = cards[i]
      for (let j = i + 1; j < cards.length; j++) {
        const b = cards[j]
        if (rectsOverlap(a, b)) {
          throw new LayoutFormatError(
            `overlap between card#${i} (${a.w},${a.h},${a.x},${a.y}) and card#${j} (${b.w},${b.h},${b.x},${b.y})`,
            i,
          )
        }
      }
    }
  }

  return { cards, grid, warnings }
}

function rectsOverlap(a: LayoutCard, b: LayoutCard): boolean {
  return !(
    a.x + a.w <= b.x ||
    b.x + b.w <= a.x ||
    a.y + a.h <= b.y ||
    b.y + b.h <= a.y
  )
}

/** 阅读序：自上而下逐行，同行自左而右（与放置先后无关）。 */
export function sortCardsReadingOrder<T extends { x: number; y: number }>(cards: T[]): T[] {
  return [...cards].sort((a, b) => a.y - b.y || a.x - b.x)
}

/** 序列化；可带 `grid:CxR;` 头与 type。卡片顺序固定为阅读序。 */
export function stringifyLayoutSequence(
  cards: Array<Pick<LayoutCard, 'w' | 'h' | 'x' | 'y'> & { type?: string }>,
  style: 'compact' | 'list' = 'compact',
  grid?: { cols: number; rows: number },
): string {
  const ordered = sortCardsReadingOrder(cards)
  const parts = ordered.map((c) => {
    if (!c.type) return `(${c.w},${c.h},${c.x},${c.y})`
    const t = String(c.type)
    // 无空格/逗号/括号/引号时不加引号，便于从 JSON 原样复制
    if (/^[^\s,()"']+$/.test(t)) {
      return `(${c.w},${c.h},${c.x},${c.y},${t})`
    }
    const esc = t.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
    return `(${c.w},${c.h},${c.x},${c.y},"${esc}")`
  })
  const body = style === 'list' ? `[${parts.join(', ')}]` : parts.join('')
  if (grid && grid.cols > 0 && grid.rows > 0) {
    return `grid:${grid.cols}x${grid.rows};${body}`
  }
  return body
}

/**
 * 将解析结果转为画布 GridItem[]（自动补 id/label/color）。
 */
export function layoutCardsToGridItems(
  cards: LayoutCard[],
  options: {
    cols?: number
    rows?: number
    colors?: string[]
    checkCollision?: boolean
  } = {},
): GridItem[] {
  const fallbackColors = options.colors ?? [
    '#3d8bfd',
    '#5eb887',
    '#e6a23c',
    '#9b6bdf',
    '#d9776f',
    '#2aa8a0',
    '#c45c9a',
    '#6b8cae',
  ]
  const checkCollision = options.checkCollision !== false

  const items: GridItem[] = []
  for (let i = 0; i < cards.length; i++) {
    const c = cards[i]
    if (
      checkCollision &&
      options.cols !== undefined &&
      options.rows !== undefined
    ) {
      if (!canPlace(items, c.x, c.y, c.w, c.h, options.cols, options.rows)) {
        throw new LayoutFormatError(
          `cannot place card#${i} (${c.w},${c.h},${c.x},${c.y}) on grid`,
          i,
        )
      }
    }
    const type = c.type || `card_${i}`
    items.push({
      id: `layout_${i}`,
      type,
      label: c.type ? `${c.type} ${c.w}×${c.h}` : `#${i + 1} · ${c.w}×${c.h}`,
      x: c.x,
      y: c.y,
      w: c.w,
      h: c.h,
      color: c.type ? cardTypeColor(c.type) : fallbackColors[i % fallbackColors.length],
    })
  }
  return items
}

/** 一步：解析字符串并转为 GridItem[] */
export function parseLayoutToGridItems(
  input: string,
  options: ParseLayoutOptions & {
    colors?: string[]
    checkCollision?: boolean
  } = {},
): GridItem[] {
  const parsed = parseLayoutSequence(input, options)
  return layoutCardsToGridItems(parsed.cards, {
    cols: options.cols ?? parsed.grid?.cols,
    rows: options.rows ?? parsed.grid?.rows,
    colors: options.colors,
    checkCollision: options.checkCollision,
  })
}

/** 根据卡片坐标推算需要的网格尺寸（至少 minCols×minRows） */
export function inferGridSize(
  cards: LayoutCard[],
  minCols = 32,
  minRows = 24,
): { cols: number; rows: number } {
  let cols = minCols
  let rows = minRows
  for (const c of cards) {
    cols = Math.max(cols, c.x + c.w)
    rows = Math.max(rows, c.y + c.h)
  }
  return { cols, rows }
}
