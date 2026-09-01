export type GridSize = { w: number; h: number }

export type GridItem = {
  id: string
  type: string
  label: string
  x: number
  y: number
  w: number
  h: number
  color: string
}

export type PaletteItem = {
  type: string
  label: string
  w: number
  h: number
  color: string
}

export type ResolutionPreset = {
  id: string
  label: string
  /** 画布逻辑像素宽（页面实际宽） */
  width: number
  /** 画布逻辑像素高（页面实际高） */
  height: number
}
