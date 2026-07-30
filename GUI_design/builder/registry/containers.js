/**
 * 容器注册表
 *
 * 两类：
 * 1) layout  — 布局容器：只管排布，默认无壳，避免为排版多层嵌套
 * 2) preset  — 组件容器：带常见版式预设（参考 Domain 紫系设计），拖入即带槽位
 *
 * 字段：
 * - role: layout | preset
 * - seedSlots: 创建时自动生成的子槽（仅 palette 新建时）
 * - hidden: 不在侧栏显示（内部槽位等）
 */

export const CONTAINER_DEFS = [
  // ─── 布局容器 ───
  {
    id: "layout-row",
    label: "行排列",
    hint: "横向 · 自动换行",
    category: "layout",
    role: "layout",
    icon: "⇄",
    defaultWidth: "1/1",
    defaultLayout: "row",
    cols: "2",
    style: "plain",
    chrome: "hide",
    align: "center",
    accepts: ["*"],
  },
  {
    id: "layout-column",
    label: "列排列",
    hint: "纵向堆叠",
    category: "layout",
    role: "layout",
    icon: "⇅",
    defaultWidth: "1/1",
    defaultLayout: "column",
    cols: "2",
    style: "plain",
    chrome: "hide",
    accepts: ["*"],
  },
  {
    id: "layout-waterfall",
    label: "自适应瀑布流",
    hint: "多列错落填充",
    category: "layout",
    role: "layout",
    icon: "▦",
    defaultWidth: "1/1",
    defaultLayout: "waterfall",
    cols: "3",
    style: "plain",
    chrome: "hide",
    accepts: ["*"],
  },

  // ─── 组件容器（预设版式，参考紫色 Domain / 仪表盘设计） ───
  {
    id: "preset-split",
    label: "左右分栏",
    hint: "1 : 1 两列",
    category: "preset",
    role: "preset",
    icon: "▥",
    defaultWidth: "1/1",
    defaultLayout: "grid",
    cols: "2",
    style: "plain",
    chrome: "hide",
    align: "center",
    seedSlots: [
      { style: "soft", span: "1", tag: "左栏", justify: "center" },
      { style: "bordered", span: "1", tag: "右栏", justify: "center" },
    ],
  },
  {
    id: "preset-main-side",
    label: "主从分栏",
    hint: "一容器两槽 · 宽:窄 = 2:1",
    category: "preset",
    role: "preset",
    icon: "▤",
    defaultWidth: "1/1",
    defaultLayout: "grid",
    cols: "main-side",
    style: "plain",
    chrome: "hide",
    align: "center",
    seedSlots: [
      { style: "soft", span: "1", tag: "主栏 (宽)", justify: "start" },
      { style: "bordered", span: "1", tag: "从栏 (窄)", justify: "center" },
    ],
  },
  {
    id: "preset-quad",
    label: "四宫格",
    hint: "2×2 指标/卡片",
    category: "preset",
    role: "preset",
    icon: "▦",
    defaultWidth: "1/1",
    defaultLayout: "grid",
    cols: "2",
    style: "plain",
    chrome: "hide",
    seedSlots: [
      { style: "soft", span: "1", tag: "格 1" },
      { style: "soft", span: "1", tag: "格 2" },
      { style: "soft", span: "1", tag: "格 3" },
      { style: "soft", span: "1", tag: "格 4" },
    ],
  },
  {
    id: "preset-tri",
    label: "三列均分",
    hint: "一行三卡",
    category: "preset",
    role: "preset",
    icon: "☰",
    defaultWidth: "1/1",
    defaultLayout: "grid",
    cols: "3",
    style: "plain",
    chrome: "hide",
    seedSlots: [
      { style: "soft", span: "1", tag: "列 1" },
      { style: "soft", span: "1", tag: "列 2" },
      { style: "soft", span: "1", tag: "列 3" },
    ],
  },
  {
    id: "preset-212",
    label: "上二中一底二",
    hint: "2-1-2 经典页",
    category: "preset",
    role: "preset",
    icon: "≔",
    defaultWidth: "1/1",
    defaultLayout: "grid",
    cols: "2",
    style: "plain",
    chrome: "hide",
    seedSlots: [
      { style: "soft", span: "1", tag: "上左" },
      { style: "bordered", span: "1", tag: "上右" },
      { style: "gradient", span: "full", tag: "中通栏" },
      { style: "soft", span: "1", tag: "下左" },
      { style: "bordered", span: "1", tag: "下右" },
    ],
  },
  {
    id: "preset-domain",
    label: "Domain 页式",
    hint: "双栏定义 + 渐变强调",
    category: "preset",
    role: "preset",
    icon: "◈",
    defaultWidth: "1/1",
    defaultLayout: "grid",
    cols: "2",
    style: "plain",
    chrome: "hide",
    seedSlots: [
      { style: "soft", span: "1", tag: "定义区" },
      { style: "bordered", span: "1", tag: "可视化" },
      { style: "gradient", span: "full", tag: "强调 Callout" },
    ],
  },
  {
    id: "preset-hero",
    label: "标题叠层",
    hint: "上标题 · 下内容",
    category: "preset",
    role: "preset",
    icon: "▣",
    defaultWidth: "1/1",
    defaultLayout: "column",
    cols: "2",
    style: "plain",
    chrome: "hide",
    seedSlots: [
      { style: "plain", span: "full", tag: "标题区", width: "1/1" },
      { style: "bordered", span: "full", tag: "内容区", width: "1/1" },
    ],
  },
  {
    id: "preset-banner",
    label: "通栏强调",
    hint: "全宽渐变条",
    category: "preset",
    role: "preset",
    icon: "▬",
    defaultWidth: "1/1",
    defaultLayout: "row",
    cols: "2",
    style: "gradient",
    chrome: "hide",
    seedSlots: [],
  },
  {
    id: "preset-card",
    label: "单色内容卡",
    hint: "普通带边框卡片",
    category: "preset",
    role: "preset",
    icon: "▢",
    defaultWidth: "1/2",
    defaultLayout: "column",
    cols: "2",
    style: "bordered",
    chrome: "hide",
    seedSlots: [],
  },

  // ─── 内部槽位（不出现在侧栏） ───
  {
    id: "slot-cell",
    label: "内容槽",
    hint: "预设内的投放格",
    category: "_internal",
    role: "slot",
    icon: "·",
    hidden: true,
    defaultWidth: "1/1",
    defaultLayout: "column",
    cols: "2",
    style: "soft",
    chrome: "hide",
    accepts: ["*"],
  },
];

export const CONTAINER_BY_ID = Object.fromEntries(
  CONTAINER_DEFS.map((d) => [d.id, d])
);

export const CONTAINER_CATEGORIES = [
  { id: "layout", label: "布局容器" },
  { id: "preset", label: "组件容器（预设版式）" },
];

/** 侧栏可见的容器（排除 hidden） */
export function listPaletteContainers() {
  return CONTAINER_DEFS.filter((d) => !d.hidden);
}
