import type { DragPayload } from './components/dragTypes'

/** HTML5 DnD 在 dragover 常无法读 dataTransfer，用模块级状态补足 */
let activeDrag: DragPayload | null = null

export function setActiveDrag(payload: DragPayload | null) {
  activeDrag = payload
}

export function getActiveDrag() {
  return activeDrag
}
