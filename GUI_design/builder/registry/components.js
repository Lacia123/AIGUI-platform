/**
 * 组件类型注册表
 * 后续新增组件：在本文件追加一项，并在 render/components.js 补上 create 即可。
 *
 * kind: "leaf" 叶子内容；容器请放在 containers.js
 *
 * propsSchema.type:
 *   string | textarea | number | select | tags | json
 */

export const COMPONENT_DEFS = [
  {
    id: "heading",
    label: "Title",
    category: "content",
    icon: "T",
    defaultProps: {
      text: "The Domain",
      level: 1,
      accentWord: "Domain",
    },
    propsSchema: [
      { key: "text", label: "标题文字", type: "string" },
      {
        key: "level",
        label: "标题级别",
        type: "select",
        options: [
          { value: 1, label: "H1" },
          { value: 2, label: "H2" },
          { value: 3, label: "H3" },
        ],
      },
      { key: "accentWord", label: "高亮词（需出现在标题中）", type: "string" },
    ],
  },
  {
    id: "text",
    label: "Description",
    category: "content",
    icon: "¶",
    defaultProps: {
      text: "Think of it as the Guest List for your function.",
    },
    propsSchema: [{ key: "text", label: "描述正文", type: "textarea" }],
  },
  {
    id: "label",
    label: "Section Label",
    category: "content",
    icon: "L",
    defaultProps: {
      text: "CORE DEFINITION",
    },
    propsSchema: [{ key: "text", label: "分区标签", type: "string" }],
  },
  {
    id: "definition",
    label: "Definition Block",
    category: "content",
    icon: "D",
    defaultProps: {
      body: "The complete set of all possible <u>input values</u>.",
      footnote: "Also known as the 'Independent Variables'.",
    },
    propsSchema: [
      {
        key: "body",
        label: "定义正文（可含简单 HTML，如 <u>）",
        type: "textarea",
      },
      { key: "footnote", label: "脚注说明", type: "string" },
    ],
  },
  {
    id: "metric",
    label: "Core Metric",
    category: "metrics",
    icon: "%",
    defaultProps: {
      value: "98.5%",
      caption: "Uptime",
      trend: "+1.2%",
    },
    propsSchema: [
      { key: "value", label: "主数值", type: "string" },
      { key: "caption", label: "说明文字", type: "string" },
      { key: "trend", label: "趋势（如 +1.2%）", type: "string" },
    ],
  },
  {
    id: "metric-mini",
    label: "Mini Metric",
    category: "metrics",
    icon: "·",
    defaultProps: {
      label: "CPU",
      value: "42%",
    },
    propsSchema: [
      { key: "label", label: "指标名", type: "string" },
      { key: "value", label: "数值", type: "string" },
    ],
  },
  {
    id: "chart-line",
    label: "Line Chart",
    category: "charts",
    icon: "╱",
    defaultProps: {
      title: "Visualizing Domain: f(x) = √x",
      caption: "Allowed Inputs (Domain): [0, +∞)",
    },
    propsSchema: [
      { key: "title", label: "图表标题", type: "string" },
      { key: "caption", label: "底部说明", type: "string" },
    ],
  },
  {
    id: "chart-bar",
    label: "Bar Chart",
    category: "charts",
    icon: "▮",
    defaultProps: {
      title: "Revenue Overview",
    },
    propsSchema: [{ key: "title", label: "图表标题", type: "string" }],
  },
  {
    id: "progress",
    label: "Progress Bar",
    category: "progress",
    icon: "▬",
    defaultProps: {
      label: "Deploy",
      value: 72,
    },
    propsSchema: [
      { key: "label", label: "进度名称", type: "string" },
      { key: "value", label: "进度值 (0–100)", type: "number", min: 0, max: 100 },
    ],
  },
  {
    id: "progress-ring",
    label: "Progress Ring",
    category: "progress",
    icon: "◯",
    defaultProps: {
      value: 86,
      label: "Complete",
    },
    propsSchema: [
      { key: "value", label: "进度值 (0–100)", type: "number", min: 0, max: 100 },
      { key: "label", label: "环旁说明", type: "string" },
    ],
  },
  {
    id: "checklist",
    label: "To-do List",
    category: "lists",
    icon: "☑",
    defaultProps: {
      items: [
        { text: "Review domain constraints", done: true },
        { text: "Sketch √x for x ≥ 0", done: false, warn: true },
        { text: "Write input-output rule", done: false },
      ],
    },
    propsSchema: [
      {
        key: "items",
        label: "清单项",
        type: "json",
        hint: 'JSON 数组：[{ "text", "done", "warn" }]',
      },
    ],
  },
  {
    id: "tags",
    label: "Tag Row",
    category: "lists",
    icon: "#",
    defaultProps: {
      tags: ["Neon", "Cyber", "Art"],
    },
    propsSchema: [
      {
        key: "tags",
        label: "标签",
        type: "tags",
        hint: "用逗号分隔，例如 Neon, Cyber, Art",
      },
    ],
  },
  {
    id: "callout",
    label: "Callout Text",
    category: "content",
    icon: "!",
    defaultProps: {
      title: "The Input-Output Rule",
      body: "Every input from the domain maps to exactly one output in the range.",
    },
    propsSchema: [
      { key: "title", label: "强调标题", type: "string" },
      { key: "body", label: "正文", type: "textarea" },
    ],
  },
  {
    id: "image",
    label: "Illustration",
    category: "media",
    icon: "▣",
    defaultProps: {
      caption: "Illustration",
    },
    propsSchema: [{ key: "caption", label: "图注", type: "string" }],
  },
  {
    id: "status-bar",
    label: "Status Strip",
    category: "content",
    icon: "─",
    defaultProps: {
      text: "Allowed Inputs (Domain): [0, +∞)",
    },
    propsSchema: [{ key: "text", label: "状态条文字", type: "string" }],
  },
];

export const COMPONENT_BY_ID = Object.fromEntries(
  COMPONENT_DEFS.map((d) => [d.id, d])
);

export const COMPONENT_CATEGORIES = [
  { id: "content", label: "内容" },
  { id: "metrics", label: "指标" },
  { id: "charts", label: "图表" },
  { id: "progress", label: "进度" },
  { id: "lists", label: "列表" },
  { id: "media", label: "媒体" },
];

/** 取某组件的可编辑字段定义；无 schema 时从 defaultProps 推断 */
export function getComponentPropsSchema(typeId) {
  const def = COMPONENT_BY_ID[typeId];
  if (!def) return [];
  if (Array.isArray(def.propsSchema) && def.propsSchema.length) {
    return def.propsSchema;
  }
  const props = def.defaultProps || {};
  return Object.keys(props).map((key) => {
    const v = props[key];
    if (Array.isArray(v)) {
      return {
        key,
        label: key,
        type: typeof v[0] === "string" ? "tags" : "json",
      };
    }
    if (typeof v === "number") {
      return { key, label: key, type: "number" };
    }
    if (typeof v === "object" && v !== null) {
      return { key, label: key, type: "json" };
    }
    return { key, label: key, type: "string" };
  });
}
