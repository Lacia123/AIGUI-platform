import type { PaletteItem, ResolutionPreset } from './types'

export const RESOLUTION_PRESETS: ResolutionPreset[] = [
  {
    id: 'phone',
    label: '手机 390×844',
    width: 390,
    height: 844,
    cols: 6,
    rows: 13,
  },
  {
    id: 'tablet',
    label: '平板 768×1024',
    width: 768,
    height: 1024,
    cols: 8,
    rows: 12,
  },
  {
    id: 'desktop',
    label: '桌面 1280×800',
    width: 1280,
    height: 800,
    cols: 16,
    rows: 10,
  },
  {
    id: 'square',
    label: '方阵 800×800（10×10）',
    width: 800,
    height: 800,
    cols: 10,
    rows: 10,
  },
]

export const PALETTE_ITEMS: PaletteItem[] = [
  { type: 'card', label: '卡片 2×2', w: 2, h: 2, color: '#3d8bfd' },
  { type: 'banner', label: '横幅 4×1', w: 4, h: 1, color: '#5eb887' },
  { type: 'tile', label: '方块 1×1', w: 1, h: 1, color: '#e6a23c' },
  { type: 'panel', label: '面板 3×2', w: 3, h: 2, color: '#9b6bdf' },
  { type: 'list', label: '列表 2×4', w: 2, h: 4, color: '#d9776f' },
]
