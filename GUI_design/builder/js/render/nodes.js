/**
 * 节点工厂：根据注册表创建 DOM，并挂上 data-* 元信息。
 * 组件容器（preset）新建时会按 seedSlots 生成内容槽，避免用户手搓多层嵌套。
 */

import { getDef, isContainerType } from "../core/registry.js";
import { renderComponent } from "./components.js";

let _seq = 1;
export function nextId(prefix = "n") {
  return `${prefix}-${Date.now().toString(36)}-${_seq++}`;
}

export function createContainerNode(typeId, overrides = {}) {
  const def = getDef("container", typeId);
  if (!def) throw new Error(`Unknown container: ${typeId}`);

  const width = overrides.width || def.defaultWidth || "1/1";
  const layout = overrides.layout || def.defaultLayout || "column";
  const style = overrides.style || def.style || "bordered";
  const cols = String(overrides.cols || def.cols || "2");
  const span = overrides.span || "1";
  const role = def.role || "preset";
  const align = overrides.align || def.align || (layout === "row" || layout === "grid" ? "center" : "stretch");
  const justify = overrides.justify || def.justify || (role === "slot" ? "center" : "start");
  const chrome =
    overrides.chrome ||
    def.chrome ||
    (style === "plain" || role === "layout" ? "hide" : "show");

  const el = document.createElement("div");
  el.className = [
    "node",
    "container",
    `role-${role}`,
    `width-${width.replace("/", "-")}`,
    `layout-${layout}`,
    `style-${style}`,
    `cols-${cols}`,
    `span-${span}`,
    `chrome-${chrome}`,
    `align-${align}`,
    `justify-${justify}`,
  ].join(" ");

  el.dataset.nodeId = overrides.id || nextId("c");
  el.dataset.kind = "container";
  el.dataset.type = typeId;
  el.dataset.role = role;
  el.dataset.width = width;
  el.dataset.layout = layout;
  el.dataset.style = style;
  el.dataset.cols = cols;
  el.dataset.span = span;
  el.dataset.chrome = chrome;
  el.dataset.align = align;
  el.dataset.justify = justify;

  const tagText = overrides.tag || def.label;
  el.innerHTML = `
    <div class="container-chrome" contenteditable="false" data-action="select-self" title="点此选中该容器">
      <span class="container-tag">${tagText}</span>
      <span class="chrome-hint">选中 · 可改壳</span>
      <button type="button" class="btn-icon container-menu" title="菜单" data-action="menu">⋯</button>
    </div>
    <div class="container-body drop-zone" data-role="body"></div>
  `;

  // 仅从调色板新建 preset 时播种槽位；反序列化 / 递归种子时跳过
  if (!overrides.skipSeed && Array.isArray(def.seedSlots) && def.seedSlots.length) {
    seedSlots(el, def.seedSlots);
  }

  return el;
}

function seedSlots(parentEl, slots) {
  const body = getContainerBody(parentEl);
  if (!body) return;
  for (const slot of slots) {
    const cell = createContainerNode("slot-cell", {
      skipSeed: true,
      width: slot.width || "1/1",
      layout: slot.layout || "column",
      style: slot.style || "soft",
      span: slot.span || "1",
      chrome: "hide",
      tag: slot.tag || "内容槽",
      align: slot.align || "center",
      justify: slot.justify || "center",
    });
    body.appendChild(cell);
  }
}

export function createComponentNode(typeId, overrides = {}) {
  const def = getDef("component", typeId);
  if (!def) throw new Error(`Unknown component: ${typeId}`);

  const el = document.createElement("div");
  el.className = `node component comp-${typeId}`;
  el.dataset.nodeId = overrides.id || nextId("p");
  el.dataset.kind = "component";
  el.dataset.type = typeId;
  el.dataset.span = overrides.span || "1";
  el.dataset.width = overrides.width || "1/2";
  el.classList.add(
    `span-${el.dataset.span}`,
    `width-${el.dataset.width.replace("/", "-")}`
  );
  el.draggable = true;

  const props = { ...def.defaultProps, ...(overrides.props || {}) };
  el.dataset.props = JSON.stringify(props);
  renderComponent(el, typeId, props);
  return el;
}

export function createNodeFromPalette(kind, typeId) {
  if (kind === "container" || isContainerType(typeId)) {
    return createContainerNode(typeId);
  }
  return createComponentNode(typeId);
}

export function getContainerBody(containerEl) {
  return containerEl.querySelector(':scope > [data-role="body"]');
}

export function readProps(el) {
  try {
    return JSON.parse(el.dataset.props || "{}");
  } catch {
    return {};
  }
}

export function writeProps(el, props) {
  el.dataset.props = JSON.stringify(props);
  renderComponent(el, el.dataset.type, props);
}
