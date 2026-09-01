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
              draggable
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
              </small>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
