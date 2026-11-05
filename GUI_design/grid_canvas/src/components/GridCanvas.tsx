import { useMemo, useRef, useState } from 'react'
import { getActiveDrag, setActiveDrag } from '../dragState'
import { canPlace, snapToCell } from '../gridUtils'
import { cellOrigin, spanSize, type GridMetrics } from '../gridMetrics'
import type { GridItem } from '../types'
import type { DragPayload } from './dragTypes'
import { DRAG_MIME } from './dragTypes'

type Props = {
  metrics: GridMetrics
  items: GridItem[]
  onPlace: (item: Omit<GridItem, 'id'>) => boolean
  onMove: (id: string, x: number, y: number) => boolean
  /** 可选：改尺寸（格数）；提供时选中卡右下角可拖拽缩放 */
  onResize?: (id: string, w: number, h: number) => boolean
  onSelect: (id: string | null) => void
  selectedId: string | null
  onRemove: (id: string) => void
  scale: number
}

export function GridCanvas({
  metrics,
  items,
  onPlace,
  onMove,
  onResize,
  onSelect,
  selectedId,
  onRemove,
  scale,
}: Props) {
  const boardRef = useRef<HTMLDivElement>(null)
  const [ghost, setGhost] = useState<{
    x: number
    y: number
    w: number
    h: number
    ok: boolean
  } | null>(null)
  const resizingRef = useRef<{
    id: string
    startX: number
    startY: number
    origW: number
    origH: number
    cellX: number
    cellY: number
  } | null>(null)
  const [isResizing, setIsResizing] = useState(false)

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

  function readPayload(e: React.DragEvent): DragPayload | null {
    const live = getActiveDrag()
    if (live) return live
    const raw = e.dataTransfer.getData(DRAG_MIME) || e.dataTransfer.getData('text/plain')
    if (!raw) return null
    try {
      return JSON.parse(raw) as DragPayload
    } catch {
      return null
    }
  }

  function localPoint(e: React.DragEvent) {
    const el = boardRef.current
    if (!el) return { x: 0, y: 0 }
    const rect = el.getBoundingClientRect()
    return {
      x: (e.clientX - rect.left) / scale,
      y: (e.clientY - rect.top) / scale,
    }
  }

  function updateGhost(e: React.DragEvent, w: number, h: number, excludeId?: string) {
    const { x: lx, y: ly } = localPoint(e)
    const { x, y } = snapToCell(lx, ly, cellW, cellH, cols, rows, w, h, gap)
    const ok = canPlace(items, x, y, w, h, cols, rows, excludeId)
    setGhost({ x, y, w, h, ok })
    return { x, y, ok }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
    const payload = getActiveDrag() ?? readPayload(e)
    if (!payload) return
    if (payload.kind === 'palette') {
      updateGhost(e, payload.item.w, payload.item.h)
    } else {
      updateGhost(e, payload.w, payload.h, payload.id)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const payload = readPayload(e)
    setGhost(null)
    setActiveDrag(null)
    if (!payload) return

    if (payload.kind === 'palette') {
      const { item } = payload
      const { x: lx, y: ly } = localPoint(e)
      const { x, y } = snapToCell(lx, ly, cellW, cellH, cols, rows, item.w, item.h, gap)
      onPlace({
        type: item.type,
        label: item.label,
        x,
        y,
        w: item.w,
        h: item.h,
        color: item.color,
      })
      return
    }

    const { x: lx, y: ly } = localPoint(e)
    const { x, y } = snapToCell(lx, ly, cellW, cellH, cols, rows, payload.w, payload.h, gap)
    onMove(payload.id, x, y)
  }

  function startMove(item: GridItem, e: React.DragEvent) {
    e.stopPropagation()
    const payload: DragPayload = {
      kind: 'move',
      id: item.id,
      w: item.w,
      h: item.h,
    }
    setActiveDrag(payload)
    e.dataTransfer.setData(DRAG_MIME, JSON.stringify(payload))
    e.dataTransfer.setData('text/plain', JSON.stringify(payload))
    e.dataTransfer.effectAllowed = 'move'
    onSelect(item.id)
  }

  function startResize(item: GridItem, e: React.PointerEvent) {
    if (!onResize) return
    e.stopPropagation()
    e.preventDefault()
    onSelect(item.id)
    resizingRef.current = {
      id: item.id,
      startX: e.clientX,
      startY: e.clientY,
      origW: item.w,
      origH: item.h,
      cellX: item.x,
      cellY: item.y,
    }
    setIsResizing(true)
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }

  function onResizeMove(e: React.PointerEvent) {
    const r = resizingRef.current
    if (!r || !onResize) return
    const stepW = cellW + gap
    const stepH = cellH + gap
    const dw = Math.round((e.clientX - r.startX) / scale / stepW)
    const dh = Math.round((e.clientY - r.startY) / scale / stepH)
    const maxW = cols - r.cellX
    const maxH = rows - r.cellY
    const nextW = Math.max(1, Math.min(maxW, r.origW + dw))
    const nextH = Math.max(1, Math.min(maxH, r.origH + dh))
    onResize(r.id, nextW, nextH)
  }

  function endResize(e: React.PointerEvent) {
    if (!resizingRef.current) return
    resizingRef.current = null
    setIsResizing(false)
    try {
      ;(e.target as HTMLElement).releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="canvas-stage">
      <div
        className="canvas-scale"
        style={{
          width: pageW * scale,
          height: pageH * scale,
        }}
      >
        <div
          ref={boardRef}
          className="grid-board"
          style={{
            ...gridStyle,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
          onDragOver={handleDragOver}
          onDragLeave={() => setGhost(null)}
          onDrop={handleDrop}
          onClick={() => onSelect(null)}
        >
          {Array.from({ length: cols * rows }, (_, i) => (
            <div key={i} className="grid-cell" />
          ))}

          {ghost && (
            <div
              className={`ghost ${ghost.ok ? 'ok' : 'bad'}`}
              style={itemBox(ghost.x, ghost.y, ghost.w, ghost.h)}
            />
          )}

          {items.map((item) => (
            <div
              key={item.id}
              className={`placed ${selectedId === item.id ? 'selected' : ''}`}
              draggable={!isResizing}
              onDragStart={(e) => startMove(item, e)}
              onDragEnd={() => {
                setGhost(null)
                setActiveDrag(null)
              }}
              onClick={(e) => {
                e.stopPropagation()
                onSelect(item.id)
              }}
              onDoubleClick={(e) => {
                e.stopPropagation()
                onRemove(item.id)
              }}
              style={{
                ...itemBox(item.x, item.y, item.w, item.h),
                background: item.color,
              }}
              title={`${item.label} @ (${item.x},${item.y}) 双击删除`}
            >
              <span>{item.label}</span>
              <small>
                ({item.x},{item.y}) {item.w}×{item.h}
                {item.type ? ` · ${item.type}` : ''}
              </small>
              {onResize && selectedId === item.id ? (
                <button
                  type="button"
                  className="resize-handle"
                  aria-label="拖拽改尺寸"
                  onPointerDown={(e) => startResize(item, e)}
                  onPointerMove={onResizeMove}
                  onPointerUp={endResize}
                  onPointerCancel={endResize}
                  onDragStart={(e) => e.preventDefault()}
                />
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
