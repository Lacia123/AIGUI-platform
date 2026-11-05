/**
 * 手工标注页：拖拽摆卡、改尺寸；只调行列/gap/单格，整页分辨率由它们算出。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { GridCanvas } from './components/GridCanvas'
import { Palette } from './components/Palette'
import {
  DEFAULT_CELL_H0,
  DEFAULT_CELL_W0,
  DEFAULT_GAP,
  PALETTE_ITEMS,
  RESOLUTION_PRESETS,
} from './data'
import {
  buildEpisodeFromBoard,
  downloadText,
  episodeToJsonlLine,
  loadHandcraftedEpisodes,
  nextHandcraftedId,
  removeHandcraftedEpisode,
  upsertHandcraftedEpisode,
  type DatasetEpisode,
} from './datasetFormat'
import { canPlace } from './gridUtils'
import { computeGridMetrics, pageSizeForGrid } from './gridMetrics'
import { stringifyLayoutSequence } from './layoutFormat'
import { NavLinks } from './NavLinks'
import type { GridItem } from './types'
import './App.css'

function uid() {
  return `item_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`
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

function parsePositiveInt(raw: string, fallback: number): number {
  return Math.max(1, Math.floor(parsePositiveNumber(raw, fallback)))
}

function itemsFitInGrid(items: GridItem[], cols: number, rows: number): GridItem[] {
  return items.filter((i) => i.x + i.w <= cols && i.y + i.h <= rows)
}

function matchPresetId(cols: number, rows: number, cellW0: number, cellH0: number, gap: number) {
  for (const p of RESOLUTION_PRESETS) {
    const m = computeGridMetrics(p.width, p.height, cellW0, cellH0, gap)
    if (m.cols === cols && m.rows === rows) return p.id
  }
  return 'custom'
}

const DEFAULT_PAGE =
  RESOLUTION_PRESETS.find((p) => p.id === 'desktop') ?? RESOLUTION_PRESETS[0]
const DEFAULT_GRID = computeGridMetrics(
  DEFAULT_PAGE.width,
  DEFAULT_PAGE.height,
  DEFAULT_CELL_W0,
  DEFAULT_CELL_H0,
  DEFAULT_GAP,
)
const RL_LIMITS = { cols: 8, rows: 6, cardW: 8, cardH: 6, cards: 32 } as const

export default function AnnotatePage() {
  const [cols, setCols] = useState(DEFAULT_GRID.cols)
  const [rows, setRows] = useState(DEFAULT_GRID.rows)
  const [cellW0, setCellW0] = useState(DEFAULT_CELL_W0)
  const [cellH0, setCellH0] = useState(DEFAULT_CELL_H0)
  const [gap, setGap] = useState(DEFAULT_GAP)
  const [items, setItems] = useState<GridItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [canvasScale, setCanvasScale] = useState(0.5)
  const canvasPaneRef = useRef<HTMLDivElement>(null)
  const [fitNonce, setFitNonce] = useState(0)
  const [epId, setEpId] = useState(`hand-${Date.now().toString(36)}`)
  const [epLabel, setEpLabel] = useState('手工标注')
  const [epDesc, setEpDesc] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [savedList, setSavedList] = useState<DatasetEpisode[]>(() => loadHandcraftedEpisodes())

  const pageSize = useMemo(
    () => pageSizeForGrid(cols, rows, cellW0, cellH0, gap),
    [cols, rows, cellW0, cellH0, gap],
  )

  const metrics = useMemo(
    () => computeGridMetrics(pageSize.width, pageSize.height, cellW0, cellH0, gap),
    [pageSize, cellW0, cellH0, gap],
  )

  const presetId = useMemo(
    () => matchPresetId(cols, rows, cellW0, cellH0, gap),
    [cols, rows, cellW0, cellH0, gap],
  )

  const selected = items.find((i) => i.id === selectedId) ?? null

  const clampCanvasScale = (s: number) =>
    Math.min(2, Math.max(0.15, Number(s.toFixed(2))))

  const fitCanvas = useCallback(() => {
    const el = canvasPaneRef.current
    if (!el) return
    const maxW = Math.max(160, el.clientWidth - 40)
    const maxH = Math.max(160, el.clientHeight - 48)
    const s = Math.min(maxW / metrics.pageW, maxH / metrics.pageH)
    setCanvasScale(clampCanvasScale(s))
  }, [metrics.pageW, metrics.pageH])

  const fitCanvasRef = useRef(fitCanvas)
  fitCanvasRef.current = fitCanvas

  useEffect(() => {
    const id = requestAnimationFrame(() => fitCanvasRef.current())
    return () => cancelAnimationFrame(id)
  }, [fitNonce])

  useEffect(() => {
    const el = canvasPaneRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return
      e.preventDefault()
      const step = e.deltaY > 0 ? -0.05 : 0.05
      setCanvasScale((s) => clampCanvasScale(s + step))
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])

  const bumpCanvasScale = (delta: number) => {
    setCanvasScale((s) => clampCanvasScale(s + delta))
  }

  const requestFitCanvas = () => setFitNonce((n) => n + 1)

  const applyGridSize = (nextCols: number, nextRows: number, clear = false) => {
    setCols(nextCols)
    setRows(nextRows)
    if (clear) {
      setItems([])
      setSelectedId(null)
      return
    }
    setItems((prev) => itemsFitInGrid(prev, nextCols, nextRows))
    setSelectedId((cur) => {
      if (!cur) return null
      const stillThere = items.some(
        (i) => i.id === cur && i.x + i.w <= nextCols && i.y + i.h <= nextRows,
      )
      return stillThere ? cur : null
    })
  }

  const applyPreset = (id: string) => {
    const p = RESOLUTION_PRESETS.find((x) => x.id === id)
    if (!p) return
    const m = computeGridMetrics(p.width, p.height, DEFAULT_CELL_W0, DEFAULT_CELL_H0, DEFAULT_GAP)
    setCellW0(DEFAULT_CELL_W0)
    setCellH0(DEFAULT_CELL_H0)
    setGap(DEFAULT_GAP)
    applyGridSize(m.cols, m.rows, true)
    requestFitCanvas()
    setStatus(`已切换预设 ${p.label}（${m.cols}×${m.rows}），画布已清空`)
  }

  const handlePlace = useCallback(
    (partial: Omit<GridItem, 'id'>): boolean => {
      if (!canPlace(items, partial.x, partial.y, partial.w, partial.h, metrics.cols, metrics.rows)) {
        return false
      }
      const next: GridItem = { ...partial, id: uid() }
      setItems((prev) => [...prev, next])
      setSelectedId(next.id)
      return true
    },
    [items, metrics.cols, metrics.rows],
  )

  const handleMove = useCallback(
    (id: string, x: number, y: number): boolean => {
      const target = items.find((i) => i.id === id)
      if (!target) return false
      if (!canPlace(items, x, y, target.w, target.h, metrics.cols, metrics.rows, id)) {
        return false
      }
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, x, y } : i)))
      return true
    },
    [items, metrics.cols, metrics.rows],
  )

  const handleResize = useCallback(
    (id: string, w: number, h: number): boolean => {
      const target = items.find((i) => i.id === id)
      if (!target) return false
      if (!canPlace(items, target.x, target.y, w, h, metrics.cols, metrics.rows, id)) {
        return false
      }
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, w, h } : i)))
      return true
    },
    [items, metrics.cols, metrics.rows],
  )

  function updateSelected(patch: Partial<GridItem>) {
    if (!selected) return
    const next = { ...selected, ...patch }
    if (
      !canPlace(items, next.x, next.y, next.w, next.h, metrics.cols, metrics.rows, selected.id)
    ) {
      setStatus('尺寸/位置与其它卡冲突或越界')
      return
    }
    setItems((prev) => prev.map((i) => (i.id === selected.id ? next : i)))
    setStatus(null)
  }

  function buildCurrentEpisode(id = epId): DatasetEpisode | null {
    if (items.length === 0) {
      setStatus('请先放置至少一张卡')
      return null
    }
    if (metrics.cols > RL_LIMITS.cols || metrics.rows > RL_LIMITS.rows) {
      setStatus(`当前网格 ${metrics.cols}×${metrics.rows} 超过训练环境上限 8×6`)
      return null
    }
    if (items.length > RL_LIMITS.cards) {
      setStatus(`当前有 ${items.length} 张卡，超过训练环境上限 ${RL_LIMITS.cards}`)
      return null
    }
    const oversized = items.find((item) => item.w > RL_LIMITS.cardW || item.h > RL_LIMITS.cardH)
    if (oversized) {
      setStatus(`卡片 ${oversized.id} 的尺寸超过训练环境上限 8×6`)
      return null
    }
    return buildEpisodeFromBoard({
      id,
      label: epLabel,
      description: epDesc,
      presetId,
      pageW: metrics.pageW,
      pageH: metrics.pageH,
      cols: metrics.cols,
      rows: metrics.rows,
      cellW: cellW0,
      cellH: cellH0,
      gap,
      items,
      sourceFile: 'handcrafted',
    })
  }

  function saveEpisode() {
    const ep = buildCurrentEpisode()
    if (!ep) return
    const list = upsertHandcraftedEpisode(ep)
    setSavedList(list)
    setStatus(`已写入浏览器缓存：${ep.id}（共 ${list.length} 条）`)
  }

  function saveAsNextEpisode() {
    const nextId = nextHandcraftedId(
      epId,
      savedList.map((e) => e.id),
    )
    const ep = buildCurrentEpisode(nextId)
    if (!ep) return
    setEpId(nextId)
    const list = upsertHandcraftedEpisode(ep)
    setSavedList(list)
    setStatus(`已另存为下一条：${ep.id}（共 ${list.length} 条）`)
  }

  function downloadEpisodeJson() {
    const ep = buildCurrentEpisode()
    if (!ep) return
    downloadText(`${ep.id}.json`, JSON.stringify(ep, null, 2) + '\n')
    setStatus(`已下载 ${ep.id}.json`)
  }

  function downloadEpisodeJsonl() {
    const ep = buildCurrentEpisode()
    if (!ep) return
    downloadText(`${ep.id}.jsonl`, episodeToJsonlLine(ep) + '\n', 'application/x-ndjson')
    setStatus(`已下载 ${ep.id}.jsonl（可追加到 RL/data/*.jsonl）`)
  }

  function downloadAllJsonl() {
    const list = loadHandcraftedEpisodes()
    if (list.length === 0) {
      setStatus('缓存中还没有条目，请先「保存到本机缓存」')
      return
    }
    const body = list.map(episodeToJsonlLine).join('\n') + '\n'
    downloadText('handcrafted_layouts.jsonl', body, 'application/x-ndjson')
    setStatus(`已导出全部 ${list.length} 条 JSONL`)
  }

  function copySequence() {
    if (items.length === 0) {
      setStatus('画布为空')
      return
    }
    const seq = stringifyLayoutSequence(items, 'compact', {
      cols: metrics.cols,
      rows: metrics.rows,
    })
    void navigator.clipboard.writeText(seq).then(
      () => setStatus('已复制布局序列'),
      () => setStatus(seq),
    )
  }

  function loadSaved(ep: DatasetEpisode) {
    const nextCols = Math.max(1, ep.grid.cols)
    const nextRows = Math.max(1, ep.grid.rows)
    const nextCellW = ep.grid.cell_w || DEFAULT_CELL_W0
    const nextCellH = ep.grid.cell_h || DEFAULT_CELL_H0
    const nextGap = ep.grid.gap ?? DEFAULT_GAP
    setEpId(ep.id)
    setEpLabel(ep.label)
    setEpDesc(ep.description)
    setCellW0(nextCellW)
    setCellH0(nextCellH)
    setGap(nextGap)
    setCols(nextCols)
    setRows(nextRows)
    const queueById = new Map(ep.card_queue.map((c) => [c.id, c]))
    setItems(
      ep.expert_cards.map((box, i) => {
        const card = queueById.get(box.id)
        return {
          id: box.id || `c${i}`,
          type: card?.type || 'textCard',
          label: card?.label || card?.type || `card${i}`,
          x: box.x,
          y: box.y,
          w: box.w,
          h: box.h,
          color: card?.color || '#3d8bfd',
        }
      }),
    )
    setSelectedId(null)
    const page = pageSizeForGrid(nextCols, nextRows, nextCellW, nextCellH, nextGap)
    setStatus(`已加载 ${ep.id}（${nextCols}×${nextRows} → ${page.width}×${page.height}）`)
  }

  function deleteSaved(id: string) {
    const list = removeHandcraftedEpisode(id)
    setSavedList(list)
    setStatus(`已从缓存删除：${id}（剩余 ${list.length} 条）`)
  }

  return (
    <div className="app annotate-app">
      <header className="topbar">
        <div>
          <h1>手工标注 · 训练数据</h1>
          <p>
            拖拽摆卡 · 改尺寸 · 只调行列 / 单格 / gap，整页分辨率自动算出 · 导出 RL episode
          </p>
        </div>
        <NavLinks active="annotate" />
      </header>

      <div className="workspace annotate-workspace">
        <Palette items={PALETTE_ITEMS} />

        <main className="main">
          <div className="toolbar annotate-toolbar">
            <div className="presets">
              {RESOLUTION_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={p.id === presetId ? 'active' : ''}
                  onClick={() => applyPreset(p.id)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="toolbar">
            <div className="grid-params">
              <label className="param-ctrl">
                列数
                <input
                  type="number"
                  min={1}
                  value={cols}
                  onChange={(e) =>
                    applyGridSize(parsePositiveInt(e.target.value, cols), rows)
                  }
                />
              </label>
              <label className="param-ctrl">
                行数
                <input
                  type="number"
                  min={1}
                  value={rows}
                  onChange={(e) =>
                    applyGridSize(cols, parsePositiveInt(e.target.value, rows))
                  }
                />
              </label>
              <label className="param-ctrl">
                格宽
                <input
                  type="number"
                  min={1}
                  value={cellW0}
                  onChange={(e) => setCellW0(parsePositiveNumber(e.target.value, DEFAULT_CELL_W0))}
                />
              </label>
              <label className="param-ctrl">
                格高
                <input
                  type="number"
                  min={1}
                  value={cellH0}
                  onChange={(e) => setCellH0(parsePositiveNumber(e.target.value, DEFAULT_CELL_H0))}
                />
              </label>
              <label className="param-ctrl">
                gap
                <input
                  type="number"
                  min={0}
                  value={gap}
                  onChange={(e) => setGap(parseNonNegativeNumber(e.target.value, DEFAULT_GAP))}
                />
              </label>
            </div>
            <span className="stat">
              网格 {cols}×{rows} · 单格 {cellW0}×{cellH0} · gap {gap} → 页面 {metrics.pageW}×
              {metrics.pageH} · 卡 {items.length}
              {presetId !== 'custom' ? ` · ${presetId}` : ''}
            </span>
            <button
              type="button"
              onClick={() => {
                setItems([])
                setSelectedId(null)
              }}
            >
              清空
            </button>
          </div>

          <div className="annotate-body">
            <div className="annotate-canvas-pane">
              <div className="annotate-zoom-bar">
                <span className="annotate-zoom-label">画布缩放</span>
                <button type="button" onClick={() => bumpCanvasScale(-0.1)} title="缩小">
                  −
                </button>
                <input
                  type="range"
                  min={0.15}
                  max={2}
                  step={0.05}
                  value={canvasScale}
                  onChange={(e) => setCanvasScale(clampCanvasScale(Number(e.target.value)))}
                  aria-label="画布缩放"
                />
                <button type="button" onClick={() => bumpCanvasScale(0.1)} title="放大">
                  +
                </button>
                <span className="annotate-zoom-pct">{Math.round(canvasScale * 100)}%</span>
                <button type="button" onClick={fitCanvas}>
                  适应窗口
                </button>
                <span className="hint">Ctrl + 滚轮也可缩放</span>
              </div>
              <div ref={canvasPaneRef} className="annotate-canvas-host">
                <GridCanvas
                  metrics={metrics}
                  items={items}
                  onPlace={handlePlace}
                  onMove={handleMove}
                  onResize={handleResize}
                  onSelect={setSelectedId}
                  selectedId={selectedId}
                  onRemove={(id) => {
                    setItems((prev) => prev.filter((i) => i.id !== id))
                    if (selectedId === id) setSelectedId(null)
                  }}
                  scale={canvasScale}
                />
              </div>
            </div>

            <aside className="annotate-side">
              <section className="annotate-panel">
                <h2>条目元数据</h2>
                <label>
                  id
                  <input value={epId} onChange={(e) => setEpId(e.target.value)} />
                </label>
                <label>
                  label
                  <input value={epLabel} onChange={(e) => setEpLabel(e.target.value)} />
                </label>
                <label>
                  description
                  <textarea
                    rows={2}
                    value={epDesc}
                    onChange={(e) => setEpDesc(e.target.value)}
                    placeholder="可选说明"
                  />
                </label>
                <p className="hint">preset_id = {presetId}</p>
              </section>

              <section className="annotate-panel">
                <h2>选中卡片</h2>
                {selected ? (
                  <>
                    <p className="hint">
                      {selected.type} · ({selected.x},{selected.y})
                    </p>
                    <label>
                      label
                      <input
                        value={selected.label}
                        onChange={(e) => updateSelected({ label: e.target.value })}
                      />
                    </label>
                    <div className="annotate-wh">
                      <label>
                        w
                        <input
                          type="number"
                          min={1}
                          max={metrics.cols - selected.x}
                          value={selected.w}
                          onChange={(e) =>
                            updateSelected({
                              w: parsePositiveNumber(e.target.value, selected.w),
                            })
                          }
                        />
                      </label>
                      <label>
                        h
                        <input
                          type="number"
                          min={1}
                          max={metrics.rows - selected.y}
                          value={selected.h}
                          onChange={(e) =>
                            updateSelected({
                              h: parsePositiveNumber(e.target.value, selected.h),
                            })
                          }
                        />
                      </label>
                      <label>
                        x
                        <input
                          type="number"
                          min={0}
                          max={metrics.cols - selected.w}
                          value={selected.x}
                          onChange={(e) =>
                            updateSelected({
                              x: Math.max(0, Number(e.target.value) || 0),
                            })
                          }
                        />
                      </label>
                      <label>
                        y
                        <input
                          type="number"
                          min={0}
                          max={metrics.rows - selected.h}
                          value={selected.y}
                          onChange={(e) =>
                            updateSelected({
                              y: Math.max(0, Number(e.target.value) || 0),
                            })
                          }
                        />
                      </label>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setItems((prev) => prev.filter((i) => i.id !== selected.id))
                        setSelectedId(null)
                      }}
                    >
                      删除此卡
                    </button>
                  </>
                ) : (
                  <p className="hint">点击画布上的卡进行编辑；右下角拖柄改大小</p>
                )}
              </section>

              <section className="annotate-panel">
                <h2>保存 / 导出</h2>
                <div className="annotate-actions">
                  <button type="button" className="primary" onClick={saveEpisode}>
                    保存到本机缓存
                  </button>
                  <button type="button" onClick={saveAsNextEpisode}>
                    保存为下一个
                  </button>
                  <button type="button" onClick={downloadEpisodeJson}>
                    下载本条 JSON
                  </button>
                  <button type="button" onClick={downloadEpisodeJsonl}>
                    下载本条 JSONL
                  </button>
                  <button type="button" onClick={downloadAllJsonl}>
                    导出全部缓存 JSONL
                  </button>
                  <button type="button" onClick={copySequence}>
                    复制序列
                  </button>
                </div>
                {status ? <p className="annotate-status">{status}</p> : null}
                <p className="hint">
                  将 JSONL 行追加到{' '}
                  <code>GUI_design/grid_canvas/src/RL/data/psuip_typed_layouts.jsonl</code>{' '}
                  或新建手工作集；字段与 <code>export_sample_dataset</code> 一致：
                  <code>card_queue</code> 是无几何输入，<code>expert_cards</code> 仅作训练答案。
                </p>
              </section>

              <section className="annotate-panel">
                <h2>缓存列表（{savedList.length}）</h2>
                <ul className="annotate-saved">
                  {savedList.length === 0 ? (
                    <li className="hint">暂无</li>
                  ) : (
                    savedList.map((ep) => (
                      <li key={ep.id}>
                        <button type="button" onClick={() => loadSaved(ep)}>
                          {ep.id}
                        </button>
                        <span>
                          {ep.grid.cols}×{ep.grid.rows} · {ep.n_cards}卡
                        </span>
                        <button
                          type="button"
                          className="annotate-saved-delete"
                          title={`删除 ${ep.id}`}
                          onClick={() => deleteSaved(ep.id)}
                        >
                          删除
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              </section>
            </aside>
          </div>
        </main>
      </div>
    </div>
  )
}
