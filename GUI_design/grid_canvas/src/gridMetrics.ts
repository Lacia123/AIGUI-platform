/** 由预设单位格 + 页面尺寸 + gap 推导实际网格度量。 */

export type GridMetrics = {
  /** 页面宽 */
  pageW: number
  /** 页面高 */
  pageH: number
  /** 预设单位格宽 */
  cellW0: number
  /** 预设单位格高 */
  cellH0: number
  /** 水平/垂直统一间距 */
  gap: number
  /** 列数 */
  cols: number
  /** 行数 */
  rows: number
  /** 实际单位格宽（余数均摊后） */
  cellW: number
  /** 实际单位格高 */
  cellH: number
}

/**
 * 实际格宽 = 预设 + 余数/列数，余数 = 页面宽 - 列*预设 - (列-1)*gap。
 * 列数 = floor((pageW + gap) / (cellW0 + gap))；不足一列时退化为 1 列铺满。
 */
export function computeGridMetrics(
  pageW: number,
  pageH: number,
  cellW0: number,
  cellH0: number,
  gap: number,
): GridMetrics {
  const g = Math.max(0, gap)
  const cw0 = Math.max(1, cellW0)
  const ch0 = Math.max(1, cellH0)
  const pw = Math.max(1, pageW)
  const ph = Math.max(1, pageH)

  let cols = Math.floor((pw + g) / (cw0 + g))
  let rows = Math.floor((ph + g) / (ch0 + g))

  let cellW: number
  let cellH: number

  if (cols < 1) {
    cols = 1
    cellW = pw
  } else {
    const remW = pw - cols * cw0 - (cols - 1) * g
    cellW = cw0 + remW / cols
  }

  if (rows < 1) {
    rows = 1
    cellH = ph
  } else {
    const remH = ph - rows * ch0 - (rows - 1) * g
    cellH = ch0 + remH / rows
  }

  return {
    pageW: pw,
    pageH: ph,
    cellW0: cw0,
    cellH0: ch0,
    gap: g,
    cols,
    rows,
    cellW,
    cellH,
  }
}

/**
 * 给定目标列/行数与单位格参数，反推刚好容纳的页面宽高。
 * page = n * cell0 + (n - 1) * gap
 */
export function pageSizeForGrid(
  cols: number,
  rows: number,
  cellW0: number,
  cellH0: number,
  gap: number,
): { width: number; height: number } {
  const g = Math.max(0, gap)
  const cw0 = Math.max(1, cellW0)
  const ch0 = Math.max(1, cellH0)
  const c = Math.max(1, cols)
  const r = Math.max(1, rows)
  return {
    width: c * cw0 + (c - 1) * g,
    height: r * ch0 + (r - 1) * g,
  }
}

/** 格点 (x,y) 左上角像素 */
export function cellOrigin(
  x: number,
  y: number,
  cellW: number,
  cellH: number,
  gap: number,
): { left: number; top: number } {
  return {
    left: x * (cellW + gap),
    top: y * (cellH + gap),
  }
}

/** 跨 w×h 格的像素尺寸（格间含 gap） */
export function spanSize(
  w: number,
  h: number,
  cellW: number,
  cellH: number,
  gap: number,
): { width: number; height: number } {
  return {
    width: w * cellW + Math.max(0, w - 1) * gap,
    height: h * cellH + Math.max(0, h - 1) * gap,
  }
}
