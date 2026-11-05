/** 与 RL tools/export_sample_dataset.build_episode 对齐的 clean schema v3。 */

import { sortCardsReadingOrder, stringifyLayoutSequence } from './layoutFormat'
import type { GridItem } from './types'

export type DatasetEpisode = {
  schema_version: 3
  id: string
  label: string
  description: string
  preset_id: string
  grid: {
    cols: number
    rows: number
    width: number
    height: number
    label: string
    cell_w: number
    cell_h: number
    gap: number
  }
  card_queue: Array<{
    id: string
    type?: string
    label?: string
    color?: string
  }>
  expert_cards: Array<{
    id: string
    w: number
    h: number
    x: number
    y: number
  }>
  sequence: string
  n_cards: number
  area: number
  source_file?: string
}

export type BuildEpisodeInput = {
  id: string
  label: string
  description?: string
  presetId: string
  pageW: number
  pageH: number
  cols: number
  rows: number
  cellW: number
  cellH: number
  gap: number
  items: GridItem[]
  sourceFile?: string
}

export function buildEpisodeFromBoard(input: BuildEpisodeInput): DatasetEpisode {
  const ordered = sortCardsReadingOrder(input.items)
  const card_queue = ordered.map((it, i) => {
    const id = `c${i}`
    const card: DatasetEpisode['card_queue'][number] = {
      id,
    }
    if (it.type) card.type = it.type
    if (it.label) card.label = it.label
    if (it.color) card.color = it.color
    return card
  })

  const expert_cards = ordered.map((it, i) => ({
    id: `c${i}`,
    w: it.w,
    h: it.h,
    x: it.x,
    y: it.y,
  }))
  const sequence = stringifyLayoutSequence(
    ordered.map((it) => ({
      w: it.w,
      h: it.h,
      x: it.x,
      y: it.y,
      type: it.type,
    })),
  )

  const ep: DatasetEpisode = {
    schema_version: 3,
    id: input.id.trim() || `hand-${Date.now()}`,
    label: input.label.trim() || input.id,
    description: (input.description || '').trim() || `${input.cols}×${input.rows} 手工标注`,
    preset_id: input.presetId,
    grid: {
      cols: input.cols,
      rows: input.rows,
      width: input.pageW,
      height: input.pageH,
      label: `${input.pageW}×${input.pageH}（${input.cols}×${input.rows} @${input.cellW}×${input.cellH}/${input.gap}）`,
      cell_w: input.cellW,
      cell_h: input.cellH,
      gap: input.gap,
    },
    card_queue,
    expert_cards,
    sequence,
    n_cards: expert_cards.length,
    area: expert_cards.reduce((s, c) => s + c.w * c.h, 0),
  }
  if (input.sourceFile?.trim()) {
    ep.source_file = input.sourceFile.trim()
  }
  return ep
}

export function episodeToJsonlLine(ep: DatasetEpisode): string {
  return JSON.stringify(ep)
}

export function downloadText(filename: string, text: string, mime = 'application/json') {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const STORAGE_KEY = 'grid_canvas_handcrafted_episodes_v2'
const LEGACY_STORAGE_KEY = 'grid_canvas_handcrafted_episodes_v1'

type LegacyEpisode = Omit<DatasetEpisode, 'schema_version' | 'card_queue' | 'expert_cards'> & {
  cards?: Array<{
    id: string
    w: number
    h: number
    x: number
    y: number
    type?: string
    label?: string
    color?: string
  }>
  cards_wh?: Array<{ id: string; type?: string; label?: string; color?: string }>
}

function migrateLegacyEpisode(raw: LegacyEpisode): DatasetEpisode | null {
  if (!Array.isArray(raw.cards)) return null
  const queueById = new Map((raw.cards_wh ?? []).map((c) => [String(c.id), c]))
  const card_queue = raw.cards.map((c) => {
    const old = queueById.get(String(c.id))
    return {
      id: String(c.id),
      type: c.type ?? old?.type,
      label: c.label ?? old?.label,
      color: c.color ?? old?.color,
    }
  })
  const {
    cards: _legacyCards,
    cards_wh: _legacyCardsWh,
    target_xy: _legacyTargetXy,
    ...metadata
  } = raw as LegacyEpisode & { target_xy?: unknown }
  return {
    ...metadata,
    schema_version: 3,
    card_queue,
    expert_cards: raw.cards.map((c) => ({
      id: String(c.id),
      w: Number(c.w),
      h: Number(c.h),
      x: Number(c.x),
      y: Number(c.y),
    })),
  }
}

function parseStoredEpisodes(raw: string): DatasetEpisode[] {
  const parsed = JSON.parse(raw) as Array<DatasetEpisode | LegacyEpisode>
  if (!Array.isArray(parsed)) return []
  return parsed.flatMap((ep) => {
    if (
      (ep as DatasetEpisode).schema_version === 3 &&
      Array.isArray((ep as DatasetEpisode).card_queue) &&
      Array.isArray((ep as DatasetEpisode).expert_cards)
    ) {
      return [ep as DatasetEpisode]
    }
    const migrated = migrateLegacyEpisode(ep as LegacyEpisode)
    return migrated ? [migrated] : []
  })
}

export function loadHandcraftedEpisodes(): DatasetEpisode[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return parseStoredEpisodes(raw)
    const legacy = localStorage.getItem(LEGACY_STORAGE_KEY)
    if (!legacy) return []
    const migrated = parseStoredEpisodes(legacy)
    saveHandcraftedEpisodes(migrated)
    return migrated
  } catch {
    return []
  }
}

export function saveHandcraftedEpisodes(episodes: DatasetEpisode[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(episodes))
}

export function upsertHandcraftedEpisode(ep: DatasetEpisode): DatasetEpisode[] {
  const list = loadHandcraftedEpisodes()
  const idx = list.findIndex((e) => e.id === ep.id)
  if (idx >= 0) list[idx] = ep
  else list.push(ep)
  saveHandcraftedEpisodes(list)
  return list
}

export function removeHandcraftedEpisode(id: string): DatasetEpisode[] {
  const list = loadHandcraftedEpisodes().filter((e) => e.id !== id)
  saveHandcraftedEpisodes(list)
  return list
}

export function clearHandcraftedEpisodes(): DatasetEpisode[] {
  saveHandcraftedEpisodes([])
  return []
}

/**
 * 在当前 id 基础上生成下一个可用 id：`foo` → `foo-1`，`foo-1` → `foo-2`。
 * 自动跳过 alreadyTaken 中已存在的 id。
 */
export function nextHandcraftedId(
  currentId: string,
  alreadyTaken: Iterable<string> = loadHandcraftedEpisodes().map((e) => e.id),
): string {
  const taken = new Set(alreadyTaken)
  const trimmed = currentId.trim() || 'hand'
  const m = trimmed.match(/^(.*?)[-_](\d+)$/)
  const base = (m ? m[1] : trimmed).replace(/[-_]+$/, '') || 'hand'
  let n = m ? Number(m[2]) + 1 : 1
  if (!Number.isFinite(n) || n < 1) n = 1
  let candidate = `${base}-${n}`
  while (taken.has(candidate)) {
    n += 1
    candidate = `${base}-${n}`
  }
  return candidate
}
