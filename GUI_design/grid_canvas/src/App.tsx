import { useCallback, useEffect, useMemo, useState } from 'react'
import { GridCanvas } from './components/GridCanvas'
import { Palette } from './components/Palette'
import { ResultCanvas } from './components/ResultCanvas'
import {
  DEFAULT_CELL_H0,
  DEFAULT_CELL_W0,
  DEFAULT_GAP,
  PALETTE_ITEMS,
  RESOLUTION_PRESETS,
} from './data'
import { canPlace, occupiedCells } from './gridUtils'
import { computeGridMetrics, pageSizeForGrid } from './gridMetrics'
import {
  LayoutFormatError,
  inferGridSize,
  layoutCardsToGridItems,
  parseLayoutSequence,
  parseLayoutToGridItems,
  stringifyLayoutSequence,
} from './layoutFormat'
import { sampleLayoutsForPreset, type SampleLayout } from './sampleLayouts'
import type { GridItem, ResolutionPreset } from './types'
import { NavLinks } from './NavLinks'
import './App.css'

function uid() {
  return `item_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`
}

const LAYOUT_PLACEHOLDER =
  '示例：(2,1,0,0)(3,2,2,0) 或 [(2,1,0,0), (3,2,2,0)]\n格式：每张卡 (w,h,x,y)'

const RESULT_PLACEHOLDER =
  '粘贴模型输出，例如：\ngrid:5x3;(5,1,0,0,textCard)(1,1,0,1,targetStatCard)\n含画布尺寸 + (w,h,x,y,type)；渲染到下方大画布'

const DEFAULT_RESULT_PAGE = RESOLUTION_PRESETS.find((p) => p.id === 'dashboard') ?? {
  width: 1880,
  height: 680,
}

function parsePositiveNumber(raw: string, fallback: number): number {
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0) return fallback
  return n
}

function parseNonNegativeNumber(raw: string, fallback: number): number {
  const n = Number(raw)
  if (!Number.isFinite(n) || n < 0) return fallback
  return n
}

export default function App() {
  const [presetId, setPresetId] = useState('dashboard')
  const [itemsByPreset, setItemsByPreset] = useState<Record<string, GridItem[]>>({})
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [fitScale, setFitScale] = useState(true)
  const [manualScale, setManualScale] = useState(0.75)
  const [cellW0, setCellW0] = useState(DEFAULT_CELL_W0)
  const [cellH0, setCellH0] = useState(DEFAULT_CELL_H0)
  const [gap, setGap] = useState(DEFAULT_GAP)
  const [layoutInput, setLayoutInput] = useState('')
  const [layoutError, setLayoutError] = useState<string | null>(null)
  const [resultInput, setResultInput] = useState('')
  const [resultItems, setResultItems] = useState<GridItem[]>([])
  const [resultError, setResultError] = useState<string | null>(null)
  const [resultPageW, setResultPageW] = useState(DEFAULT_RESULT_PAGE.width)
  const [resultPageH, setResultPageH] = useState(DEFAULT_RESULT_PAGE.height)
  const [resultCellW0, setResultCellW0] = useState(DEFAULT_CELL_W0)
  const [resultCellH0, setResultCellH0] = useState(DEFAULT_CELL_H0)
  const [resultGap, setResultGap] = useState(DEFAULT_GAP)
  const [resultFitScale, setResultFitScale] = useState(true)
  const [resultManualScale, setResultManualScale] = useState(0.5)
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

  const metrics = useMemo(
    () => computeGridMetrics(preset.width, preset.height, cellW0, cellH0, gap),
    [preset, cellW0, cellH0, gap],
  )

  const resultMetrics = useMemo(
    () =>
      computeGridMetrics(resultPageW, resultPageH, resultCellW0, resultCellH0, resultGap),
    [resultPageW, resultPageH, resultCellW0, resultCellH0, resultGap],
  )

  const items = itemsByPreset[presetId] ?? []
  const sampleLayouts = useMemo(() => sampleLayoutsForPreset(presetId), [presetId])

  const scale = useMemo(() => {
    if (!fitScale) return manualScale
    const pad = 48
    const maxW = Math.max(320, viewport.w - 320 - pad)
    const maxH = Math.max(320, viewport.h - 180)
    return Math.min(1, maxW / metrics.pageW, maxH / metrics.pageH)
  }, [fitScale, manualScale, metrics, viewport])

  const resultScale = useMemo(() => {
    if (!resultFitScale) return resultManualScale
    const maxW = Math.max(480, viewport.w - 48)
    const maxH = Math.max(420, Math.min(720, viewport.h * 0.7))
    return Math.min(1, maxW / resultMetrics.pageW, maxH / resultMetrics.pageH)
  }, [resultFitScale, resultManualScale, resultMetrics, viewport])

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
    if (!canPlace(items, partial.x, partial.y, partial.w, partial.h, metrics.cols, metrics.rows)) {
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
    if (!canPlace(items, x, y, target.w, target.h, metrics.cols, metrics.rows, id)) {
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
    setLayoutError(null)
  }

  function renderLayoutInput() {
    try {
      const next = parseLayoutToGridItems(layoutInput, {
        cols: metrics.cols,
        rows: metrics.rows,
      })
      setItems(next)
      setSelectedId(null)
      setLayoutError(null)
      setLayoutInput(stringifyLayoutSequence(next))
    } catch (err) {
      const message =
        err instanceof LayoutFormatError
          ? err.message
          : err instanceof Error
            ? err.message
            : '解析失败'
      setLayoutError(message)
    }
  }

  function exportCurrentLayout() {
    if (items.length === 0) {
      setLayoutInput('')
      setLayoutError(null)
      return
    }
    setLayoutInput(stringifyLayoutSequence(items))
    setLayoutError(null)
  }

  function applySampleLayout(sample: SampleLayout) {
    try {
      const next: GridItem[] = sample.cards.map((c, i) => {
        if (c.x + c.w > metrics.cols || c.y + c.h > metrics.rows) {
          throw new LayoutFormatError(
            `卡 (${c.w},${c.h},${c.x},${c.y}) 超出当前网格 ${metrics.cols}×${metrics.rows}；请换「桌面/手机」预设或调大页面/调小单位格`,
            i,
          )
        }
        return {
          id: uid(),
          type: c.type ?? 'card',
          label: c.label ?? `${c.type ?? 'card'} ${c.w}×${c.h}`,
          x: c.x,
          y: c.y,
          w: c.w,
          h: c.h,
          color: c.color ?? '#3d8bfd',
        }
      })
      // 重叠校验
      for (let i = 0; i < next.length; i++) {
        const a = next[i]
        if (!canPlace(next, a.x, a.y, a.w, a.h, metrics.cols, metrics.rows, a.id)) {
          throw new LayoutFormatError(`卡 ${a.label} 与其它卡重叠或越界`, i)
        }
      }
      setLayoutInput(stringifyLayoutSequence(next))
      setItems(next)
      setSelectedId(null)
      setLayoutError(null)
    } catch (err) {
      const message =
        err instanceof LayoutFormatError
          ? err.message
          : err instanceof Error
            ? err.message
            : '典型布局应用失败'
      setLayoutError(message)
    }
  }

  function renderModelResult() {
    try {
      const parsed = parseLayoutSequence(resultInput, {
        checkOverlap: false,
      })
      const { cards, grid } = parsed
      const needed = inferGridSize(cards, 1, 1)
      const targetCols = grid?.cols ?? Math.max(needed.cols, 1)
      const targetRows = grid?.rows ?? Math.max(needed.rows, 1)

      const expanded = pageSizeForGrid(
        targetCols,
        targetRows,
        resultCellW0,
        resultCellH0,
        resultGap,
      )
      const pageW = expanded.width
      const pageH = expanded.height
      setResultPageW(pageW)
      setResultPageH(pageH)

      const metricsNow = computeGridMetrics(
        pageW,
        pageH,
        resultCellW0,
        resultCellH0,
        resultGap,
      )

      const next = layoutCardsToGridItems(cards, {
        cols: metricsNow.cols,
        rows: metricsNow.rows,
        checkCollision: false,
      })
      setResultItems(next)
      setResultError(null)
    } catch (err) {
      const message =
        err instanceof LayoutFormatError
          ? err.message
          : err instanceof Error
            ? err.message
            : '解析失败'
      setResultError(message)
    }
  }

  function clearModelResult() {
    setResultItems([])
    setResultError(null)
  }

  function sendEditorToResult() {
    const seq = items.length > 0 ? stringifyLayoutSequence(items) : layoutInput
    setResultInput(seq)
    setResultError(null)
  }

  function applyResultPreset(p: ResolutionPreset) {
    setResultPageW(p.width)
    setResultPageH(p.height)
  }

  function syncResultFromEditor() {
    setResultPageW(preset.width)
    setResultPageH(preset.height)
    setResultCellW0(cellW0)
    setResultCellH0(cellH0)
    setResultGap(gap)
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
    setLayoutError(null)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>固定网格画布</h1>
          <p>样例统一 228×216 单位格 / 16 gap · 余数摊平 · 拖入吸附 · 碰撞检测</p>
        </div>
        <div className="topbar-right">
          <NavLinks active="home" />
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
        </div>
      </header>

      <div className="workspace">
        <Palette items={PALETTE_ITEMS} />

        <main className="main">
          <div className="toolbar">
            <div className="grid-params">
              <label className="param-ctrl">
                预设格宽
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={cellW0}
                  onChange={(e) => setCellW0(parsePositiveNumber(e.target.value, DEFAULT_CELL_W0))}
                />
              </label>
              <label className="param-ctrl">
                预设格高
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={cellH0}
                  onChange={(e) => setCellH0(parsePositiveNumber(e.target.value, DEFAULT_CELL_H0))}
                />
              </label>
              <label className="param-ctrl">
                gap
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={gap}
                  onChange={(e) => setGap(parseNonNegativeNumber(e.target.value, DEFAULT_GAP))}
                />
              </label>
            </div>
            <span className="stat">
              画布 {metrics.pageW}×{metrics.pageH}px · 网格 {metrics.cols}×{metrics.rows} · 实际格{' '}
              {metrics.cellW.toFixed(1)}×{metrics.cellH.toFixed(1)}px · gap {metrics.gap}px
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

          <section className="layout-input">
            <div className="layout-input-head">
              <label htmlFor="layout-seq">布局序列</label>
              <span className="layout-input-hint">格式 (w,h,x,y)，渲染后覆盖当前画布</span>
            </div>
            {sampleLayouts.length > 0 ? (
              <div className="sample-layouts">
                <span className="sample-layouts-label">典型布局</span>
                <div className="sample-layouts-list">
                  {sampleLayouts.map((sample) => (
                    <button
                      key={sample.id}
                      type="button"
                      title={sample.description}
                      onClick={() => applySampleLayout(sample)}
                    >
                      {sample.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            <textarea
              id="layout-seq"
              value={layoutInput}
              onChange={(e) => {
                setLayoutInput(e.target.value)
                if (layoutError) setLayoutError(null)
              }}
              placeholder={LAYOUT_PLACEHOLDER}
              rows={3}
              spellCheck={false}
            />
            <div className="layout-input-actions">
              <button type="button" className="primary" onClick={renderLayoutInput}>
                渲染
              </button>
              <button type="button" onClick={exportCurrentLayout}>
                导出当前
              </button>
              <button type="button" onClick={sendEditorToResult}>
                送到结果画布
              </button>
              {layoutError ? <p className="layout-input-error">{layoutError}</p> : null}
            </div>
          </section>

          <GridCanvas
            metrics={metrics}
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
              <p>
                从左侧拖入组件。切换分辨率会保留各画布上的独立布局。修改预设格 / gap
                会重算列行与实际格宽高。
              </p>
            )}
          </footer>
        </main>
      </div>

      <section className="result-section">
        <div className="result-section-head">
          <div>
            <h2>模型结果画布</h2>
            <p>
              可手动改分辨率与单位格；与编辑区相同公式（含 gap）。块上显示 #顺序 与 card 类型。
            </p>
          </div>
          <span className="stat">
            画布 {resultMetrics.pageW}×{resultMetrics.pageH}px · 网格 {resultMetrics.cols}×
            {resultMetrics.rows} · 实际格 {resultMetrics.cellW.toFixed(1)}×
            {resultMetrics.cellH.toFixed(1)}px · 显示 {Math.round(resultScale * 100)}%
          </span>
        </div>

        <div className="toolbar result-toolbar">
          <div className="grid-params">
            <label className="param-ctrl">
              页面宽
              <input
                type="number"
                min={1}
                step={1}
                value={resultPageW}
                onChange={(e) =>
                  setResultPageW(parsePositiveNumber(e.target.value, DEFAULT_RESULT_PAGE.width))
                }
              />
            </label>
            <label className="param-ctrl">
              页面高
              <input
                type="number"
                min={1}
                step={1}
                value={resultPageH}
                onChange={(e) =>
                  setResultPageH(parsePositiveNumber(e.target.value, DEFAULT_RESULT_PAGE.height))
                }
              />
            </label>
            <label className="param-ctrl">
              预设格宽
              <input
                type="number"
                min={1}
                step={1}
                value={resultCellW0}
                onChange={(e) =>
                  setResultCellW0(parsePositiveNumber(e.target.value, DEFAULT_CELL_W0))
                }
              />
            </label>
            <label className="param-ctrl">
              预设格高
              <input
                type="number"
                min={1}
                step={1}
                value={resultCellH0}
                onChange={(e) =>
                  setResultCellH0(parsePositiveNumber(e.target.value, DEFAULT_CELL_H0))
                }
              />
            </label>
            <label className="param-ctrl">
              gap
              <input
                type="number"
                min={0}
                step={1}
                value={resultGap}
                onChange={(e) => setResultGap(parseNonNegativeNumber(e.target.value, DEFAULT_GAP))}
              />
            </label>
          </div>
          <div className="presets result-presets">
            {RESOLUTION_PRESETS.map((p) => (
              <button
                key={`result-${p.id}`}
                type="button"
                className={
                  resultPageW === p.width && resultPageH === p.height ? 'active' : ''
                }
                onClick={() => applyResultPreset(p)}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button type="button" onClick={syncResultFromEditor}>
            同步编辑区参数
          </button>
          <label className="scale-ctrl">
            <input
              type="checkbox"
              checked={resultFitScale}
              onChange={(e) => setResultFitScale(e.target.checked)}
            />
            自适应缩放
          </label>
          {!resultFitScale && (
            <label className="scale-ctrl">
              缩放
              <input
                type="range"
                min={0.2}
                max={1.2}
                step={0.05}
                value={resultManualScale}
                onChange={(e) => setResultManualScale(Number(e.target.value))}
              />
              {Math.round(resultManualScale * 100)}%
            </label>
          )}
        </div>

        <div className="layout-input result-input">
          <div className="layout-input-head">
            <label htmlFor="result-seq">模型输出序列</label>
            <span className="layout-input-hint">
              支持 <code>grid:13x8;(w,h,x,y,type)…</code>
              ；有 grid 头时会按该尺寸设定大画布
            </span>
          </div>
          <textarea
            id="result-seq"
            value={resultInput}
            onChange={(e) => {
              setResultInput(e.target.value)
              if (resultError) setResultError(null)
            }}
            placeholder={RESULT_PLACEHOLDER}
            rows={4}
            spellCheck={false}
          />
          <div className="layout-input-actions">
            <button type="button" className="primary" onClick={renderModelResult}>
              渲染到大画布
            </button>
            <button type="button" onClick={clearModelResult}>
              清空结果
            </button>
            {resultError ? <p className="layout-input-error">{resultError}</p> : null}
            {!resultError && resultItems.length > 0 ? (
              <p className="result-input-ok">已渲染 {resultItems.length} 块</p>
            ) : null}
          </div>
        </div>

        <ResultCanvas metrics={resultMetrics} items={resultItems} scale={resultScale} />
      </section>
    </div>
  )
}
