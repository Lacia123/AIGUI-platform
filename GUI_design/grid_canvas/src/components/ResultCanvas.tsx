import { useMemo } from 'react'
import { cellOrigin, spanSize, type GridMetrics } from '../gridMetrics'
import type { GridItem } from '../types'

type Props = {
  metrics: GridMetrics
  items: GridItem[]
  /** 相对逻辑尺寸的显示缩放 */
  scale?: number
}

/**
 * 大空白结果画布：按坐标渲染，支持单位格 + gap 度量。
 * 块上的 #n 表示布局序列中的先后顺序。
 */
export function ResultCanvas({ metrics, items, scale = 1 }: Props) {
  const { pageW, pageH, cols, rows, cellW, cellH, gap } = metrics

  const gridStyle = useMemo(
    () =>
      ({
        width: pageW,
        height: pageH,
        gridTemplateColumns: `repeat(${cols}, ${cellW}px)`,
        gridTemplateRows: `repeat(${rows}, ${cellH}px)`,
        gap: `${gap}px`,
      }) as React.CSSProperties,
    [pageW, pageH, cols, rows, cellW, cellH, gap],
  )

  function itemBox(x: number, y: number, w: number, h: number) {
    const { left, top } = cellOrigin(x, y, cellW, cellH, gap)
    const { width, height } = spanSize(w, h, cellW, cellH, gap)
    return { left, top, width, height }
  }

  return (
    <div className="result-canvas-stage">
      <div
        className="result-canvas-scale"
        style={{ width: pageW * scale, height: pageH * scale }}
      >
        <div
          className="result-board"
          style={{
            ...gridStyle,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
        >
          {Array.from({ length: cols * rows }, (_, i) => (
            <div key={i} className="result-cell" />
          ))}

          {items.map((item, index) => (
            <div
              key={item.id}
              className="result-block"
              style={{
                ...itemBox(item.x, item.y, item.w, item.h),
                background: item.color,
              }}
              title={`#${index + 1} (w,h,x,y)=(${item.w},${item.h},${item.x},${item.y})`}
            >
              <span className="result-block-order">#{index + 1}</span>
              <span className="result-block-meta">
                ({item.x},{item.y}) {item.w}×{item.h}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
