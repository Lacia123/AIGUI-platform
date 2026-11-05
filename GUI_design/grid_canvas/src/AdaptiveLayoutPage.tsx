/**
 * 自适应布局页：把 data 里的网格样例转成 layout2 的 row/column，用 flex 渲染。
 */
import { useMemo, useState } from 'react'
import { FlexCanvas } from './components/FlexCanvas'
import { ResultCanvas } from './components/ResultCanvas'
import { DEFAULT_CELL_H0, DEFAULT_CELL_W0, DEFAULT_GAP, RESOLUTION_PRESETS } from './data'
import { cardsToFlexTree, cardsToLayout2Episode, type FlexCard } from './flexTree'
import { computeGridMetrics } from './gridMetrics'
import { NavLinks } from './NavLinks'
import { SAMPLE_LAYOUTS, type SampleLayout } from './sampleLayouts'
import type { GridItem } from './types'
import './App.css'

function sampleCards(sample: SampleLayout): FlexCard[] {
  return sample.cards.map((c, i) => ({
    id: `c${i}`,
    type: c.type,
    label: c.label,
    color: c.color,
    x: c.x,
    y: c.y,
    w: c.w,
    h: c.h,
  }))
}

function sampleToGridItems(sample: SampleLayout): GridItem[] {
  return sample.cards.map((c, i) => ({
    id: `c${i}`,
    type: c.type || 'card',
    label: c.label || c.type || `card${i}`,
    x: c.x,
    y: c.y,
    w: c.w,
    h: c.h,
    color: c.color || '#3d8bfd',
  }))
}

export default function AdaptiveLayoutPage() {
  const [presetFilter, setPresetFilter] = useState('all')
  const [sampleId, setSampleId] = useState(SAMPLE_LAYOUTS[0]?.id ?? '')
  const [fill, setFill] = useState(false)
  const [compareGrid, setCompareGrid] = useState(false)
  const [codeTab, setCodeTab] = useState<'psuip' | 'ast' | 'actions'>('psuip')
  const [copyStatus, setCopyStatus] = useState<string | null>(null)

  const samples = useMemo(() => {
    if (presetFilter === 'all') return SAMPLE_LAYOUTS
    return SAMPLE_LAYOUTS.filter((s) => s.presetId === presetFilter)
  }, [presetFilter])

  const sample = useMemo(
    () => samples.find((s) => s.id === sampleId) ?? samples[0] ?? SAMPLE_LAYOUTS[0],
    [samples, sampleId],
  )

  const preset = useMemo(
    () => RESOLUTION_PRESETS.find((p) => p.id === sample.presetId) ?? RESOLUTION_PRESETS[0],
    [sample],
  )

  const cards = useMemo(() => sampleCards(sample), [sample])
  const tree = useMemo(() => cardsToFlexTree(cards), [cards])
  const episode = useMemo(
    () =>
      cardsToLayout2Episode(cards, {
        id: sample.id,
        label: sample.label,
        description: sample.description,
        presetId: sample.presetId,
      }),
    [cards, sample],
  )

  const metrics = useMemo(
    () => computeGridMetrics(preset.width, preset.height, DEFAULT_CELL_W0, DEFAULT_CELL_H0, DEFAULT_GAP),
    [preset],
  )

  const gridItems = useMemo(() => sampleToGridItems(sample), [sample])

  const scale = useMemo(() => {
    const maxW = compareGrid ? 520 : 880
    const maxH = 620
    return Math.min(1, maxW / metrics.pageW, maxH / metrics.pageH)
  }, [compareGrid, metrics])

  const codeText =
    codeTab === 'psuip'
      ? episode.psuip
      : codeTab === 'ast'
        ? JSON.stringify(episode.layout, null, 2)
        : episode.actions.join('\n')

  function copyCode() {
    void navigator.clipboard.writeText(codeText).then(
      () => setCopyStatus('已复制'),
      () => setCopyStatus('复制失败'),
    )
    window.setTimeout(() => setCopyStatus(null), 1600)
  }

  return (
    <div className="app flex-app">
      <header className="topbar">
        <div>
          <h1>自适应布局 · Layout2</h1>
          <p>
            网格样例转成 <code>layout:row</code> / <code>layout:column</code>
            ，flex 权重对齐原格数，含官方预设与 8×5 / 3×6 / 4×6 手工页
          </p>
        </div>
        <NavLinks active="layout2" />
      </header>

      <div className="flex-toolbar">
        <div className="presets">
          <button
            type="button"
            className={presetFilter === 'all' ? 'active' : ''}
            onClick={() => setPresetFilter('all')}
          >
            全部
          </button>
          {RESOLUTION_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={p.id === presetFilter ? 'active' : ''}
              onClick={() => {
                setPresetFilter(p.id)
                const first = SAMPLE_LAYOUTS.find((s) => s.presetId === p.id)
                if (first) setSampleId(first.id)
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
        <label className="scale-ctrl">
          <input type="checkbox" checked={fill} onChange={(e) => setFill(e.target.checked)} />
          铺满视口
        </label>
        <label className="scale-ctrl">
          <input
            type="checkbox"
            checked={compareGrid}
            onChange={(e) => setCompareGrid(e.target.checked)}
          />
          对照网格
        </label>
        <span className="stat">
          {sample.label} · {metrics.cols}×{metrics.rows} · {episode.cards.length} 卡 ·{' '}
          {episode.actions.length} 步
        </span>
      </div>

      <div className="flex-workspace">
        <aside className="flex-sample-list">
          {samples.map((s) => (
            <button
              key={s.id}
              type="button"
              className={s.id === sample.id ? 'active' : ''}
              onClick={() => setSampleId(s.id)}
              title={s.description}
            >
              <strong>{s.label}</strong>
              <span>{s.description}</span>
            </button>
          ))}
        </aside>

        <main className="flex-main">
          <div className={`flex-preview ${compareGrid ? 'flex-preview-split' : ''}`}>
            {compareGrid ? (
              <section className="flex-preview-pane">
                <h2>原网格</h2>
                <ResultCanvas metrics={metrics} items={gridItems} scale={scale} />
              </section>
            ) : null}
            <section className="flex-preview-pane">
              <h2>{fill ? '自适应 flex' : '等比 flex'}</h2>
              <FlexCanvas
                tree={tree}
                gap={metrics.gap}
                cellW={metrics.cellW}
                cellH={metrics.cellH}
                fill={fill}
                pageW={metrics.pageW}
                pageH={metrics.pageH}
                scale={scale}
              />
            </section>
          </div>
        </main>

        <aside className="flex-code">
          <div className="flex-code-tabs">
            <button
              type="button"
              className={codeTab === 'psuip' ? 'active' : ''}
              onClick={() => setCodeTab('psuip')}
            >
              PSUIP
            </button>
            <button
              type="button"
              className={codeTab === 'ast' ? 'active' : ''}
              onClick={() => setCodeTab('ast')}
            >
              AST
            </button>
            <button
              type="button"
              className={codeTab === 'actions' ? 'active' : ''}
              onClick={() => setCodeTab('actions')}
            >
              Actions
            </button>
            <button type="button" onClick={copyCode}>
              复制
            </button>
            {copyStatus ? <span className="result-input-ok">{copyStatus}</span> : null}
          </div>
          <pre>{codeText}</pre>
        </aside>
      </div>
    </div>
  )
}
