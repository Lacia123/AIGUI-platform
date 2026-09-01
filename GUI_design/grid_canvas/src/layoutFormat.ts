import { canPlace, inBounds } from './gridUtils'
import type { GridItem } from './types'

/** 布局序列中单张卡片：(w, h, x, y) */
export type LayoutCard = {
  w: number
  h: number
  x: number
  y: number
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

/** 匹配 (w,h,x,y)，允许空白 */
const CARD_RE = /\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)/g

/**
 * 解析布局序列字符串。
 *
 * 单卡格式：`(w,h,x,y)`
 * 序列示例：
 * - `(2,1,0,0)(3,2,2,0)`
 * - `[(2,1,0,0), (3,2,2,0)]`
 * - 多行 / 逗号 / 空格分隔均可
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

  // 去掉包裹的 []，其余交给全局正则提取元组
  const body = text.replace(/^\s*\[/, '').replace(/\]\s*$/, '')

  // 检测无法识别的残留（去掉合法元组与分隔符后应为空）
  const residual = body
    .replace(CARD_RE, '')
    .replace(/[\s,;|]+/g, '')
  // 重置 lastIndex：上面 replace 用了带 g 的 CARD_RE
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

    const { cols, rows } = options
    if (cols !== undefined && rows !== undefined) {
      if (!inBounds(x, y, w, h, cols, rows)) {
        throw new LayoutFormatError(
          `card ${raw} out of bounds on ${cols}×${rows} grid`,
          index,
          raw,
        )
      }
    }

    cards.push({ w, h, x, y })
    index += 1
  }

  if (cards.length === 0) {
    throw new LayoutFormatError(
      'no cards found; expected tokens like (w,h,x,y)',
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

  return { cards, warnings }
}

function rectsOverlap(
  a: LayoutCard,
  b: LayoutCard,
): boolean {
  return !(
    a.x + a.w <= b.x ||
    b.x + b.w <= a.x ||
    a.y + a.h <= b.y ||
    b.y + b.h <= a.y
  )
}

/** 序列化为一行：`(w,h,x,y)(w,h,x,y)...` */
export function stringifyLayoutSequence(
  cards: Array<Pick<LayoutCard, 'w' | 'h' | 'x' | 'y'>>,
  style: 'compact' | 'list' = 'compact',
): string {
  const parts = cards.map((c) => `(${c.w},${c.h},${c.x},${c.y})`)
  if (style === 'list') return `[${parts.join(', ')}]`
  return parts.join('')
}

/**
 * 将解析结果转为画布 GridItem[]（自动补 id/label/color）。
 * 若提供 cols/rows，会用 canPlace 再校验一次放置合法性。
 */
export function layoutCardsToGridItems(
  cards: LayoutCard[],
  options: {
    cols?: number
    rows?: number
    colors?: string[]
    /** 为 false 时不校验重叠，便于渲染任意模型输出 */
    checkCollision?: boolean
  } = {},
): GridItem[] {
  const colors = options.colors ?? [
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
    items.push({
      id: `layout_${i}`,
      type: `card_${i}`,
      label: `#${i + 1} · ${c.w}×${c.h}`,
      x: c.x,
      y: c.y,
      w: c.w,
      h: c.h,
      color: colors[i % colors.length],
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
  const { cards } = parseLayoutSequence(input, options)
  return layoutCardsToGridItems(cards, {
    cols: options.cols,
    rows: options.rows,
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
