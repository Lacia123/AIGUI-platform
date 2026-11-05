import type { CSSProperties } from 'react'
import { DEFAULT_CELL_H0, DEFAULT_CELL_W0, DEFAULT_GAP } from '../data'
import type { FlexNode } from '../flexTree'

type Props = {
  tree: FlexNode
  gap?: number
  cellW?: number
  cellH?: number
  /** 铺满父容器；否则按 pageW×pageH 再乘 scale */
  fill?: boolean
  pageW?: number
  pageH?: number
  scale?: number
}

function spanPx(cells: number, cell: number, gap: number): number {
  if (cells <= 0) return 0
  return cells * cell + Math.max(0, cells - 1) * gap
}

function childFlex(
  node: FlexNode,
  parentKind: 'row' | 'column',
  cellW: number,
  cellH: number,
  gap: number,
): number {
  return parentKind === 'row'
    ? spanPx(node.bbox.w, cellW, gap)
    : spanPx(node.bbox.h, cellH, gap)
}

function boxStyle(
  direction: 'row' | 'column',
  flex: number,
  gap: number,
): CSSProperties {
  return {
    display: 'flex',
    flexDirection: direction,
    flex: `${Math.max(1, flex)} 1 0`,
    gap,
    minWidth: 0,
    minHeight: 0,
    alignItems: 'stretch',
  }
}

function FlexNodeView({
  node,
  parentKind,
  cellW,
  cellH,
  gap,
}: {
  node: FlexNode
  parentKind: 'row' | 'column'
  cellW: number
  cellH: number
  gap: number
}) {
  const flex = childFlex(node, parentKind, cellW, cellH, gap)
  if (node.kind === 'card') {
    const { card, cardIndex } = node
    return (
      <div
        className="flex-card"
        style={{
          flex: `${Math.max(1, flex)} 1 0`,
          background: card.color || '#3d8bfd',
          minWidth: 0,
          minHeight: 0,
        }}
        title={`#${cardIndex + 1} ${card.type ?? 'card'} ${card.w}×${card.h} @(${card.x},${card.y})`}
      >
        <span className="result-block-order">#{cardIndex + 1}</span>
        <span className="result-block-type">{card.type || 'card'}</span>
        <span className="result-block-meta">
          {card.label || card.type} · {card.w}×{card.h}
        </span>
      </div>
    )
  }

  return (
    <div className={`flex-box flex-${node.kind}`} style={boxStyle(node.kind, flex, gap)}>
      {node.children.map((child, i) => (
        <FlexNodeView
          key={`${child.kind}-${i}-${child.bbox.x}-${child.bbox.y}`}
          node={child}
          parentKind={node.kind}
          cellW={cellW}
          cellH={cellH}
          gap={gap}
        />
      ))}
    </div>
  )
}

/**
 * 按 row/column 树用 flex 渲染。
 * 子项权重用原网格跨度像素（含 gap），与固定网格页比例一致。
 */
export function FlexCanvas({
  tree,
  gap = DEFAULT_GAP,
  cellW = DEFAULT_CELL_W0,
  cellH = DEFAULT_CELL_H0,
  fill = false,
  pageW = 1280,
  pageH = 800,
  scale = 1,
}: Props) {
  const rootKind = tree.kind === 'card' ? 'column' : tree.kind
  const board = (
    <div className="flex-board" style={boxStyle(rootKind, 1, gap)}>
      {(tree.kind === 'card' ? [tree] : tree.children).map((child, i) => (
        <FlexNodeView
          key={`${child.kind}-${i}-${child.bbox.x}-${child.bbox.y}`}
          node={child}
          parentKind={rootKind}
          cellW={cellW}
          cellH={cellH}
          gap={gap}
        />
      ))}
    </div>
  )

  if (fill) {
    return (
      <div className="flex-canvas-stage flex-canvas-fill">
        <div className="flex-canvas-scale flex-canvas-scale-fill">{board}</div>
      </div>
    )
  }

  return (
    <div className="flex-canvas-stage">
      <div className="flex-canvas-scale" style={{ width: pageW * scale, height: pageH * scale }}>
        <div
          style={{
            width: pageW,
            height: pageH,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
        >
          {board}
        </div>
      </div>
    </div>
  )
}
