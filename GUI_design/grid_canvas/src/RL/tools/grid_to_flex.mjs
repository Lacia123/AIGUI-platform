/**
 * 把 sample_layouts.json 转成 layout2 row/column（与 grid_to_flex.py / flexTree.ts 同算法）。
 *   node RL/tools/grid_to_flex.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const dataDir = join(here, '..', 'data')

function bbox(items) {
  const x = Math.min(...items.map((i) => i.x))
  const y = Math.min(...items.map((i) => i.y))
  const r = Math.max(...items.map((i) => i.x + i.w))
  const b = Math.max(...items.map((i) => i.y + i.h))
  return { x, y, w: r - x, h: b - y }
}

function startOf(it, axis) {
  return axis === 'x' ? it.x : it.y
}

function sizeOf(it, axis) {
  return axis === 'x' ? it.w : it.h
}

function splitBands(items, axis) {
  if (items.length <= 1) return null
  const edges = [
    ...new Set(items.flatMap((it) => [startOf(it, axis), startOf(it, axis) + sizeOf(it, axis)])),
  ].sort((a, b) => a - b)
  const cuts = []
  for (const edge of edges) {
    if (edge === edges[0] || edge === edges[edges.length - 1]) continue
    if (!items.some((it) => startOf(it, axis) < edge && startOf(it, axis) + sizeOf(it, axis) > edge)) {
      cuts.push(edge)
    }
  }
  if (!cuts.length) return null
  const bounds = [edges[0], ...cuts, edges[edges.length - 1]]
  const bands = []
  for (let i = 0; i < bounds.length - 1; i++) {
    const a = bounds[i]
    const b = bounds[i + 1]
    const band = items.filter(
      (it) => startOf(it, axis) >= a && startOf(it, axis) + sizeOf(it, axis) <= b,
    )
    if (band.length) bands.push(band)
  }
  return bands.length >= 2 ? bands : null
}

function cardNode(card, index) {
  return {
    kind: 'card',
    cardIndex: index,
    card,
    flex: 1,
    bbox: { x: card.x, y: card.y, w: card.w, h: card.h },
  }
}

function fallback(items, indexOf) {
  const ordered = [...items].sort((a, b) => a.y - b.y || a.x - b.x)
  const rows = []
  for (const it of ordered) {
    const last = rows[rows.length - 1]
    if (last && last[0].y === it.y && last[0].h === it.h) last.push(it)
    else rows.push([it])
  }
  const box = bbox(items)
  if (rows.length === 1) {
    const row = rows[0]
    if (row.length === 1) return cardNode(row[0], indexOf.get(row[0]))
    return {
      kind: 'row',
      flex: 1,
      bbox: box,
      children: row.map((c) => ({ ...cardNode(c, indexOf.get(c)), flex: c.w })),
    }
  }
  return {
    kind: 'column',
    flex: 1,
    bbox: box,
    children: rows.map((row) => ({ ...fallback(row, indexOf), flex: bbox(row).h })),
  }
}

function build(items, indexOf) {
  if (items.length === 1) return cardNode(items[0], indexOf.get(items[0]))
  const hBands = splitBands(items, 'y')
  const vBands = splitBands(items, 'x')
  let bands = hBands
  let kind = 'column'
  if (hBands && vBands) {
    if (vBands.length > hBands.length) {
      bands = vBands
      kind = 'row'
    }
  } else if (vBands) {
    bands = vBands
    kind = 'row'
  } else if (!hBands) {
    return fallback(items, indexOf)
  }
  const box = bbox(items)
  const children = (bands ?? []).map((band) => {
    const child = build(band, indexOf)
    child.flex = kind === 'row' ? child.bbox.w : child.bbox.h
    return child
  })
  return { kind, children, flex: 1, bbox: box }
}

function cardsToFlexTree(cards) {
  if (!cards.length) {
    return { kind: 'column', children: [], flex: 1, bbox: { x: 0, y: 0, w: 0, h: 0 } }
  }
  const ordered = [...cards].sort((a, b) => a.y - b.y || a.x - b.x)
  const indexOf = new Map(ordered.map((c, i) => [c, i]))
  const inner = build(ordered, indexOf)
  if (inner.kind === 'card') {
    return { kind: 'column', children: [inner], flex: 1, bbox: inner.bbox }
  }
  return inner
}

function toAst(node) {
  if (node.kind === 'card') return { kind: 'card', cardIndex: node.cardIndex }
  return { kind: node.kind, children: node.children.map(toAst) }
}

function toActions(node) {
  const actions = []
  function walk(n, isRoot) {
    if (n.kind === 'card') {
      actions.push('PLACE_CARD')
      return
    }
    if (!isRoot) actions.push(n.kind === 'row' ? 'OPEN_ROW' : 'OPEN_COLUMN')
    for (const child of n.children) walk(child, false)
    if (!isRoot) actions.push('CLOSE')
  }
  walk(node, true)
  return actions
}

function escapeXml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function stringify(node, level) {
  const pad = '  '.repeat(level)
  if (node.kind === 'card') {
    const type = node.card.type || 'card'
    const label = node.card.label || type
    return `${pad}<${type}>\n${pad}  <label>${escapeXml(label)}</label>\n${pad}</${type}>`
  }
  const body = node.children.map((c) => stringify(c, level + 1)).join('\n')
  return `${pad}<layout:${node.kind} alignItems="stretch">\n${body}\n${pad}</layout:${node.kind}>`
}

function episodeToFlex(ep) {
  const queue = new Map((ep.card_queue || []).map((c) => [c.id, c]))
  const cards = (ep.expert_cards || []).map((box) => {
    const meta = queue.get(box.id) || {}
    return {
      id: box.id,
      type: meta.type || 'card',
      label: meta.label,
      color: meta.color,
      x: box.x,
      y: box.y,
      w: box.w,
      h: box.h,
    }
  })
  const tree = cardsToFlexTree(cards)
  const ordered = [...cards].sort((a, b) => a.y - b.y || a.x - b.x)
  return {
    id: ep.id,
    label: ep.label,
    description: ep.description,
    preset_id: ep.preset_id,
    grid: ep.grid,
    cards: ordered.map((c, i) => ({
      id: c.id || `c${i}`,
      type: c.type || 'card',
      label: c.label,
      color: c.color,
    })),
    actions: toActions(tree),
    layout: toAst(tree),
    psuip: `<layout:root>\n${stringify(tree, 1)}\n</layout:root>\n`,
  }
}

function loadJsonl(path) {
  return readFileSync(path, 'utf8')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line))
}

function presetFromGrid(grid = {}) {
  const key = `${Number(grid.cols)}x${Number(grid.rows)}`
  return (
    {
      '8x5': 'wide8x5',
      '3x6': 'tall3x6',
      '4x6': 'tall4x6',
    }[key] || grid.id || 'custom'
  )
}

function normalizeHand(ep) {
  const grid = ep.grid || {}
  const rawId = String(ep.id || 'hand')
  const id = rawId.startsWith('hand-') ? rawId : `hand-${rawId}`
  return {
    ...ep,
    id,
    preset_id: presetFromGrid(grid),
    label: ep.label?.includes('×') ? ep.label : `${grid.cols}×${grid.rows} · ${rawId}`,
  }
}

function pushUnique(episodes, seen, ep) {
  const converted = episodeToFlex(ep)
  if (seen.has(converted.id)) return
  seen.add(converted.id)
  episodes.push(converted)
}

const srcName = process.argv[2] || 'sample_layouts.json'
const srcPath = join(dataDir, srcName)
const layout2Dir = join(here, '..', '..', '..', '..', '..', 'GUI_design2', 'layout2data')
const psuipDir = join(layout2Dir, 'psuip')
const data = JSON.parse(readFileSync(srcPath, 'utf8'))
const episodes = []
const seen = new Set()
for (const ep of data.episodes || []) pushUnique(episodes, seen, ep)

const extraJsonl = [
  join(dataDir, 'handcrafted_layouts.jsonl'),
  join(dataDir, 'test_data', 'handcrafted_layouts (1).jsonl'),
]
for (const path of extraJsonl) {
  for (const ep of loadJsonl(path)) pushUnique(episodes, seen, normalizeHand(ep))
}

const payload = {
  schema_version: 1,
  task: 'flex_layout',
  source: 'sample_layouts.json + handcrafted + testdata',
  format: {
    input: 'cards: [{id,type,label?}]',
    target: 'layout AST (row/column/card) + OPEN/PLACE/CLOSE actions',
  },
  n_episodes: episodes.length,
  episodes,
}

mkdirSync(psuipDir, { recursive: true })
writeFileSync(join(layout2Dir, 'flex_layouts.json'), JSON.stringify(payload, null, 2) + '\n', 'utf8')
writeFileSync(
  join(layout2Dir, 'flex_layouts.jsonl'),
  episodes.map((ep) => JSON.stringify(ep)).join('\n') + '\n',
  'utf8',
)
writeFileSync(join(dataDir, 'flex_layouts.json'), JSON.stringify(payload, null, 2) + '\n', 'utf8')
for (const ep of episodes) {
  writeFileSync(join(psuipDir, `${ep.id}.psuip.md`), ep.psuip, 'utf8')
}

const byGrid = {}
for (const ep of episodes) {
  const g = ep.grid ? `${ep.grid.cols}x${ep.grid.rows}` : '?'
  byGrid[g] = (byGrid[g] || 0) + 1
}
console.log(`wrote ${join(layout2Dir, 'flex_layouts.json')} (${episodes.length})`)
console.log(`wrote ${join(layout2Dir, 'flex_layouts.jsonl')}`)
console.log(`grids ${JSON.stringify(byGrid)}`)
