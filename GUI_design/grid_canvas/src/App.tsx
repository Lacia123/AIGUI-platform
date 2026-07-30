import { useCallback, useEffect, useMemo, useState } from 'react'
import { GridCanvas } from './components/GridCanvas'
import { Palette } from './components/Palette'
import { PALETTE_ITEMS, RESOLUTION_PRESETS } from './data'
import { canPlace, occupiedCells } from './gridUtils'
import type { GridItem, ResolutionPreset } from './types'
import './App.css'

function uid() {
  return `item_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`
}

export default function App() {
  const [presetId, setPresetId] = useState(RESOLUTION_PRESETS[3].id)
  const [itemsByPreset, setItemsByPreset] = useState<Record<string, GridItem[]>>({})
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [fitScale, setFitScale] = useState(true)
  const [manualScale, setManualScale] = useState(0.75)
  const [viewport, setViewport] = useState({
    w: typeof window !== 'undefined' ? window.innerWidth : 1280,
    h: typeof window !== 'undefined' ? window.innerHeight : 800,
  })

  useEffect(() => {
    const onResize = () => setViewport({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const preset = useMemo(
    () => RESOLUTION_PRESETS.find((p) => p.id === presetId) ?? RESOLUTION_PRESETS[0],
    [presetId],
  )

  const items = itemsByPreset[presetId] ?? []

  const scale = useMemo(() => {
    if (!fitScale) return manualScale
    const pad = 48
    const maxW = Math.max(320, viewport.w - 320 - pad)
    const maxH = Math.max(320, viewport.h - 120)
    return Math.min(1, maxW / preset.width, maxH / preset.height)
  }, [fitScale, manualScale, preset, viewport])

  const setItems = useCallback(
    (next: GridItem[] | ((prev: GridItem[]) => GridItem[])) => {
      setItemsByPreset((all) => {
        const prev = all[presetId] ?? []
        const value = typeof next === 'function' ? next(prev) : next
        return { ...all, [presetId]: value }
      })
    },
    [presetId],
  )

  function handlePlace(partial: Omit<GridItem, 'id'>): boolean {
    if (!canPlace(items, partial.x, partial.y, partial.w, partial.h, preset.cols, preset.rows)) {
      return false
    }
    const next: GridItem = { ...partial, id: uid() }
    setItems((prev) => [...prev, next])
    setSelectedId(next.id)
    return true
  }

  function handleMove(id: string, x: number, y: number): boolean {
    const target = items.find((i) => i.id === id)
    if (!target) return false
    if (!canPlace(items, x, y, target.w, target.h, preset.cols, preset.rows, id)) {
      return false
    }
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, x, y } : i)))
    return true
  }

  function handleRemove(id: string) {
    setItems((prev) => prev.filter((i) => i.id !== id))
    if (selectedId === id) setSelectedId(null)
  }

  function clearBoard() {
    setItems([])
    setSelectedId(null)
  }

  const selected = items.find((i) => i.id === selectedId) ?? null
  const occupied = selected
    ? occupiedCells(selected.x, selected.y, selected.w, selected.h)
        .map(([r, c]) => `(${c},${r})`)
        .join(' ')
    : ''

  function switchPreset(next: ResolutionPreset) {
    setPresetId(next.id)
    setSelectedId(null)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>固定网格画布</h1>
          <p>离散矩阵占用 · 拖入吸附 · 碰撞检测</p>
        </div>
        <div className="presets">
          {RESOLUTION_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={p.id === presetId ? 'active' : ''}
              onClick={() => switchPreset(p)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </header>

      <div className="workspace">
        <Palette items={PALETTE_ITEMS} />

        <main className="main">
          <div className="toolbar">
            <span className="stat">
              画布 {preset.width}×{preset.height}px · 网格 {preset.cols}×{preset.rows} · 格{' '}
              {(preset.width / preset.cols).toFixed(1)}×{(preset.height / preset.rows).toFixed(1)}px
            </span>
            <label className="scale-ctrl">
              <input
                type="checkbox"
                checked={fitScale}
                onChange={(e) => setFitScale(e.target.checked)}
              />
              自适应缩放
            </label>
            {!fitScale && (
              <label className="scale-ctrl">
                缩放
                <input
                  type="range"
                  min={0.3}
                  max={1.2}
                  step={0.05}
                  value={manualScale}
                  onChange={(e) => setManualScale(Number(e.target.value))}
                />
                {Math.round(manualScale * 100)}%
              </label>
            )}
            <button type="button" onClick={clearBoard}>
              清空
            </button>
          </div>

          <GridCanvas
            preset={preset}
            items={items}
            onPlace={handlePlace}
            onMove={handleMove}
            onSelect={setSelectedId}
            selectedId={selectedId}
            onRemove={handleRemove}
            scale={scale}
          />

          <footer className="inspector">
            {selected ? (
              <p>
                选中 <strong>{selected.label}</strong> 锚点 ({selected.x},{selected.y}) 尺寸{' '}
                {selected.w}×{selected.h} · 占用 {occupied}
                <em> · 双击组件可删除</em>
              </p>
            ) : (
              <p>从左侧拖入组件。切换分辨率会保留各画布上的独立布局。</p>
            )}
          </footer>
        </main>
      </div>
    </div>
  )
}
