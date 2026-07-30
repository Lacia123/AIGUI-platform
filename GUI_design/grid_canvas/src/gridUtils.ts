import type { GridItem } from './types'

/** 检测两个轴对齐矩形在网格上是否重叠 */
export function rectsOverlap(
  a: { x: number; y: number; w: number; h: number },
  b: { x: number; y: number; w: number; h: number },
): boolean {
  return !(
    a.x + a.w <= b.x ||
    b.x + b.w <= a.x ||
    a.y + a.h <= b.y ||
    b.y + b.h <= a.y
  )
}

export function inBounds(
  x: number,
  y: number,
  w: number,
  h: number,
  cols: number,
  rows: number,
): boolean {
  return x >= 0 && y >= 0 && x + w <= cols && y + h <= rows
}

/** 能否把矩形放到 (x,y)；excludeId 用于移动自身 */
export function canPlace(
  items: GridItem[],
  x: number,
  y: number,
  w: number,
  h: number,
  cols: number,
  rows: number,
  excludeId?: string,
): boolean {
  if (!inBounds(x, y, w, h, cols, rows)) return false
  const candidate = { x, y, w, h }
  return items.every(
    (item) => item.id === excludeId || !rectsOverlap(candidate, item),
  )
}

/** 把指针像素坐标吸附为网格格点 */
export function snapToCell(
  localX: number,
  localY: number,
  cellW: number,
  cellH: number,
  cols: number,
  rows: number,
  w: number,
  h: number,
): { x: number; y: number } {
  let x = Math.floor(localX / cellW)
  let y = Math.floor(localY / cellH)
  x = Math.max(0, Math.min(x, cols - w))
  y = Math.max(0, Math.min(y, rows - h))
  return { x, y }
}

export function occupiedCells(
  x: number,
  y: number,
  w: number,
  h: number,
): Array<[number, number]> {
  const cells: Array<[number, number]> = []
  for (let r = y; r < y + h; r++) {
    for (let c = x; c < x + w; c++) {
      cells.push([r, c])
    }
  }
  return cells
}
