import type { PaletteItem } from '../types'
import { setActiveDrag } from '../dragState'
import { DRAG_MIME, type DragPayload } from './dragTypes'

type Props = {
  items: PaletteItem[]
}

export function Palette({ items }: Props) {
  function onDragStart(item: PaletteItem, e: React.DragEvent) {
    const payload: DragPayload = { kind: 'palette', item }
    setActiveDrag(payload)
    e.dataTransfer.setData(DRAG_MIME, JSON.stringify(payload))
    e.dataTransfer.setData('text/plain', JSON.stringify(payload))
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <aside className="palette">
      <h2>组件库</h2>
      <p className="hint">拖到右侧画布；吸附网格并检测碰撞。已放组件可再拖动，双击删除。</p>
      <ul>
        {items.map((item) => (
          <li key={item.type}>
            <button
              type="button"
              className="palette-item"
              draggable
              onDragStart={(e) => onDragStart(item, e)}
              onDragEnd={() => setActiveDrag(null)}
              style={{ ['--swatch' as string]: item.color }}
            >
              <span className="swatch" />
              <span className="meta">
                <strong>{item.label}</strong>
                <small>
                  {item.w}×{item.h} 格
                </small>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
