import type { PaletteItem } from '../types'

export const DRAG_MIME = 'application/x-grid-item'

export type DragPayload =
  | { kind: 'palette'; item: PaletteItem }
  | { kind: 'move'; id: string; w: number; h: number }
