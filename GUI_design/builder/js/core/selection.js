/**
 * 选中态与 Inspector 操作。
 * 支持：宽度 / 布局 / 网格列数 / 子项跨列 / 一键布局模板（如 2-1-2）
 */

import { writeProps, getContainerBody } from "../render/nodes.js";
import { getDef, getComponentPropsSchema } from "./registry.js";
import { renderPropsFields, collectPropsFromForm } from "./prop-fields.js";

const WIDTHS = ["1/4", "1/3", "1/2", "1/1"];
const LAYOUTS = ["column", "row", "grid", "waterfall"];
const STYLES = ["bordered", "soft", "gradient", "glow", "plain"];
const COLS = ["2", "3", "4", "main-side"];
const ALIGNS = [
  { value: "start", label: "顶对齐" },
  { value: "center", label: "垂直居中" },
  { value: "end", label: "底对齐" },
  { value: "stretch", label: "拉伸铺满" },
];
const JUSTIFIES = [
  { value: "start", label: "靠上/靠左" },
  { value: "center", label: "居中" },
  { value: "end", label: "靠下/靠右" },
];
const SPANS = [
  { value: "1", label: "1 列" },
  { value: "2", label: "2 列" },
  { value: "3", label: "3 列" },
  { value: "full", label: "整行" },
];

/** 布局模板：按子项顺序循环应用跨列 */
const LAYOUT_PRESETS = {
  "2-1-2": { cols: "2", spans: ["1", "1", "full", "1", "1"] },
  "1-2-1": { cols: "2", spans: ["full", "1", "1", "full"] },
  "2-2": { cols: "2", spans: ["1", "1"] },
  "3-col": { cols: "3", spans: ["1", "1", "1"] },
  "1-1": { cols: "2", spans: ["full"] },
};

export function createSelectionController({ canvas, inspector }) {
  let selected = null;

  function select(node) {
    if (selected) selected.classList.remove("selected");
    selected = node || null;
    if (selected) selected.classList.add("selected");
    renderInspector();
  }

  function clear() {
    select(null);
  }

  function getSelected() {
    return selected;
  }

  function renderInspector() {
    const box = inspector.querySelector("#inspector-body");
    if (!selected) {
      box.innerHTML = `<p class="muted">选中画布中的容器或组件进行编辑。<br/>提示：悬停布局容器会浮出标题条，点标题条即可选中；Esc 选中父级；Alt+点击选中父级。</p>`;
      return;
    }

    const kind = selected.dataset.kind;
    const type = selected.dataset.type;
    const span = selected.dataset.span || "1";
    const parent = findParentContainer(selected);
    const parentIsGrid = parent?.dataset?.layout === "grid";
    const parentIsRow = parent?.dataset?.layout === "row";
    const navHtml = `
      <div class="field nav-field">
        <label>选中导航</label>
        <div class="nav-row">
          ${
            parent
              ? `<button type="button" data-act="select-parent">↑ 父容器</button>`
              : `<button type="button" disabled>已是顶层</button>`
          }
          ${
            kind === "container"
              ? `<button type="button" data-act="toggle-chrome">${
                  selected.dataset.chrome === "hide" ? "显示壳" : "隐藏壳"
                }</button>`
              : ""
          }
        </div>
        <p class="muted tip">Esc = 父级 · Alt+点击 = 父级 · 悬停布局容器点标题条</p>
      </div>`;

    if (kind === "container") {
      const layout = selected.dataset.layout || "column";
      const cols = selected.dataset.cols || "2";
      box.innerHTML = `
        ${navHtml}
        <div class="field"><label>类型</label><div class="mono">${type}${
          selected.dataset.role ? ` · ${roleLabel(selected.dataset.role)}` : ""
        }</div></div>
        <div class="field">
          <label>自身宽度（相对父级）</label>
          <select data-act="width">
            ${WIDTHS.map(
              (w) =>
                `<option value="${w}" ${
                  selected.dataset.width === w ? "selected" : ""
                }>${w}</option>`
            ).join("")}
          </select>
        </div>
        <div class="field">
          <label>内部布局</label>
          <select data-act="layout">
            ${LAYOUTS.map(
              (l) =>
                `<option value="${l}" ${layout === l ? "selected" : ""}>${
                  {
                    column: "列排列",
                    row: "行排列",
                    grid: "网格",
                    waterfall: "瀑布流",
                  }[l] || l
                }</option>`
            ).join("")}
          </select>
        </div>
        ${
          layout === "grid"
            ? `<div class="field">
                <label>网格列数</label>
                <select data-act="cols">
                  ${COLS.map(
                    (c) =>
                      `<option value="${c}" ${
                        cols === c ? "selected" : ""
                      }>${
                        c === "main-side" ? "主从 2:1" : `${c} 列`
                      }</option>`
                  ).join("")}
                </select>
              </div>
              <div class="field">
                <label>一键模板（在当前子项上套跨列）</label>
                <div class="preset-row">
                  <button type="button" data-act="preset" data-preset="2-1-2">2-1-2</button>
                  <button type="button" data-act="preset" data-preset="1-2-1">1-2-1</button>
                  <button type="button" data-act="preset" data-preset="2-2">两列</button>
                  <button type="button" data-act="preset" data-preset="3-col">三列</button>
                </div>
                <p class="muted tip">更推荐直接从左侧拖入「组件容器」预设，自带槽位。</p>
              </div>`
            : layout === "row"
              ? `<p class="muted tip">行排列：左右子项默认各占一半并垂直居中。若仍偏上，检查「垂直对齐」。</p>`
              : layout === "waterfall"
                ? `<div class="field">
                <label>瀑布流列数</label>
                <select data-act="cols">
                  ${["2", "3", "4"]
                    .map(
                      (c) =>
                        `<option value="${c}" ${
                          cols === c ? "selected" : ""
                        }>${c} 列</option>`
                    )
                    .join("")}
                </select>
              </div>
              <p class="muted tip">瀑布流：多列错落，适合卡片墙。</p>`
              : ""
        }
        <div class="field">
          <label>垂直对齐（行/网格内子项）</label>
          <select data-act="align">
            ${ALIGNS.map(
              (a) =>
                `<option value="${a.value}" ${
                  (selected.dataset.align || "center") === a.value
                    ? "selected"
                    : ""
                }>${a.label}</option>`
            ).join("")}
          </select>
        </div>
        <div class="field">
          <label>槽内内容对齐</label>
          <select data-act="justify">
            ${JUSTIFIES.map(
              (j) =>
                `<option value="${j.value}" ${
                  (selected.dataset.justify || "start") === j.value
                    ? "selected"
                    : ""
                }>${j.label}</option>`
            ).join("")}
          </select>
          <p class="muted tip">右栏只有小图时，把右槽设为「居中」，图会在栏内居中。</p>
        </div>
        <div class="field">
          <label>容器样式</label>
          <select data-act="style">
            ${STYLES.map(
              (s) =>
                `<option value="${s}" ${
                  selected.dataset.style === s ? "selected" : ""
                }>${s}</option>`
            ).join("")}
          </select>
        </div>
        <div class="field">
          <label>容器壳（标题栏）</label>
          <select data-act="chrome">
            <option value="show" ${
              (selected.dataset.chrome || "show") === "show" ? "selected" : ""
            }>显示（编辑时可见）</option>
            <option value="hide" ${
              selected.dataset.chrome === "hide" ? "selected" : ""
            }>隐藏（纯布局/对齐用）</option>
          </select>
          <p class="muted tip">嵌套排版请隐藏壳，避免 padding/标题栏把上下内容挤歪。</p>
        </div>
        ${spanField(span, parentIsGrid)}
        ${childrenOrderField(selected)}
        <div class="btn-row">
          <button type="button" data-act="cycle-layout">切换布局</button>
          <button type="button" class="danger" data-act="delete">删除</button>
        </div>
      `;
    } else {
      let props = {};
      try {
        props = JSON.parse(selected.dataset.props || "{}");
      } catch {
        props = {};
      }
      const schema = getComponentPropsSchema(type);
      box.innerHTML = `
        ${navHtml}
        <div class="field"><label>类型</label><div class="mono">${type}</div></div>
        ${
          parentIsRow
            ? `<div class="field">
                <label>宽度（父级为 Row）</label>
                <select data-act="width">
                  ${WIDTHS.map(
                    (w) =>
                      `<option value="${w}" ${
                        (selected.dataset.width || "1/2") === w ? "selected" : ""
                      }>${w}</option>`
                  ).join("")}
                </select>
              </div>`
            : ""
        }
        ${spanField(span, parentIsGrid)}
        <div class="field-group-label">可修改内容</div>
        ${renderPropsFields(schema, props)}
        <div class="btn-row">
          <button type="button" class="danger" data-act="delete">删除</button>
        </div>
      `;
    }
  }

  function findParentContainer(node) {
    if (!node) return null;
    const body = node.parentElement;
    if (!body) return null;
    const parent = body.closest(".node.container");
    return parent && parent !== node ? parent : null;
  }

  function spanField(span, show) {
    if (!show) return "";
    return `
      <div class="field">
        <label>跨列（父级 Grid）</label>
        <select data-act="span">
          ${SPANS.map(
            (s) =>
              `<option value="${s.value}" ${
                span === s.value ? "selected" : ""
              }>${s.label}</option>`
          ).join("")}
        </select>
      </div>`;
  }

  function childrenOrderField(containerEl) {
    const body = getContainerBody(containerEl);
    const children = [...(body?.children || [])].filter((n) =>
      n.classList.contains("node")
    );
    if (!children.length) {
      return `
        <div class="field">
          <label>子元素顺序</label>
          <p class="muted tip">暂无子元素，从左侧拖入后再调整顺序。</p>
        </div>`;
    }
    return `
      <div class="field">
        <label>子元素顺序</label>
        <p class="muted tip">上移 / 下移调整先后；点击名称可选中该子项。</p>
        <ul class="child-order-list">
          ${children
            .map((child, index) => {
              const title = escapeHtml(childLabel(child));
              const id = child.dataset.nodeId || "";
              return `
              <li class="child-order-item" data-child-id="${escapeHtml(id)}">
                <button type="button" class="child-pick" data-act="select-child" data-child-id="${escapeHtml(
                  id
                )}" title="选中">
                  <span class="child-idx">${index + 1}</span>
                  <span class="child-name">${title}</span>
                </button>
                <div class="child-actions">
                  <button type="button" data-act="move-child" data-dir="up" data-child-id="${escapeHtml(
                    id
                  )}" title="上移" ${index === 0 ? "disabled" : ""}>↑</button>
                  <button type="button" data-act="move-child" data-dir="down" data-child-id="${escapeHtml(
                    id
                  )}" title="下移" ${
                    index === children.length - 1 ? "disabled" : ""
                  }>↓</button>
                  <button type="button" data-act="move-child" data-dir="top" data-child-id="${escapeHtml(
                    id
                  )}" title="置顶" ${index === 0 ? "disabled" : ""}>⇈</button>
                  <button type="button" data-act="move-child" data-dir="bottom" data-child-id="${escapeHtml(
                    id
                  )}" title="置底" ${
                    index === children.length - 1 ? "disabled" : ""
                  }>⇊</button>
                </div>
              </li>`;
            })
            .join("")}
        </ul>
      </div>`;
  }

  function childLabel(el) {
    const def = getDef(el.dataset.kind, el.dataset.type);
    const base = def?.label || el.dataset.type || "未命名";
    if (el.dataset.kind === "component") {
      try {
        const props = JSON.parse(el.dataset.props || "{}");
        const hint =
          props.text || props.title || props.label || props.caption || props.value;
        if (hint) {
          const s = String(hint).replace(/\s+/g, " ").trim();
          return `${base} · ${s.length > 18 ? s.slice(0, 18) + "…" : s}`;
        }
      } catch {
        /* ignore */
      }
    }
    return base;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function roleLabel(role) {
    return (
      {
        layout: "布局容器",
        preset: "组件容器",
        slot: "内容槽",
      }[role] || role
    );
  }

  inspector.addEventListener("change", (e) => {
    const t = e.target;
    if (!selected) return;
    if (t.matches("[data-act='width']")) {
      applyWidth(selected, t.value);
    }
    if (t.matches("[data-act='layout']")) {
      applyLayout(selected, t.value);
      renderInspector();
    }
    if (t.matches("[data-act='style']")) applyStyle(selected, t.value);
    if (t.matches("[data-act='cols']")) {
      applyCols(selected, t.value);
    }
    if (t.matches("[data-act='span']")) {
      applySpan(selected, t.value);
    }
    if (t.matches("[data-act='chrome']")) {
      applyChrome(selected, t.value);
    }
    if (t.matches("[data-act='align']")) {
      applyAlign(selected, t.value);
    }
    if (t.matches("[data-act='justify']")) {
      applyJustify(selected, t.value);
    }
    if (t.matches("[data-prop]")) {
      const box = inspector.querySelector("#inspector-body");
      const { props, error } = collectPropsFromForm(
        box || inspector,
        JSON.parse(selected.dataset.props || "{}")
      );
      if (error) {
        console.warn(error);
        return;
      }
      writeProps(selected, props);
    }
  });

  inspector.addEventListener("input", (e) => {
    const t = e.target;
    if (!selected || !t.matches?.("[data-prop]")) return;
    const box = inspector.querySelector("#inspector-body");
    const { props, error } = collectPropsFromForm(
      box || inspector,
      JSON.parse(selected.dataset.props || "{}")
    );
    if (error) return;
    writeProps(selected, props);
  });

  inspector.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-act]");
    if (!btn) return;
    const act = btn.dataset.act;

    if (act === "select-parent") {
      e.stopPropagation();
      const p = findParentContainer(selected);
      if (p) select(p);
      return;
    }

    if (act === "toggle-chrome") {
      e.stopPropagation();
      if (!selected || selected.dataset.kind !== "container") return;
      const next = selected.dataset.chrome === "hide" ? "show" : "hide";
      applyChrome(selected, next);
      renderInspector();
      return;
    }

    if (act === "select-child") {
      e.stopPropagation();
      const child = findChildById(btn.dataset.childId);
      if (child) select(child);
      return;
    }

    if (act === "move-child") {
      e.stopPropagation();
      if (!selected || selected.dataset.kind !== "container") return;
      const body = getContainerBody(selected);
      const child = findChildById(btn.dataset.childId);
      if (!body || !child || !body.contains(child)) return;
      moveChild(body, child, btn.dataset.dir);
      renderInspector();
      return;
    }

    if (!selected) return;
    if (act === "delete") {
      selected.remove();
      clear();
      return;
    }
    if (act === "cycle-layout" && selected.dataset.kind === "container") {
      const i = LAYOUTS.indexOf(selected.dataset.layout);
      applyLayout(selected, LAYOUTS[(i + 1) % LAYOUTS.length]);
      renderInspector();
      return;
    }
    if (act === "preset" && selected.dataset.kind === "container") {
      applyLayoutPreset(selected, btn.dataset.preset);
      renderInspector();
    }
  });

  function findChildById(id) {
    if (!id || !selected) return null;
    const body = getContainerBody(selected);
    return body?.querySelector(`[data-node-id="${CSS.escape(id)}"]`) || null;
  }

  canvas.addEventListener("click", (e) => {
    // 点悬浮标题条 → 选中该容器（即使壳是隐藏模式）
    const chrome = e.target.closest(".container-chrome");
    if (chrome && canvas.contains(chrome)) {
      e.stopPropagation();
      const owner = chrome.closest(".node.container");
      if (owner) select(owner);
      return;
    }

    const node = e.target.closest(".node");
    if (node && canvas.contains(node)) {
      e.stopPropagation();
      // Alt + 点击：选中父容器
      if (e.altKey) {
        const p = findParentContainer(node);
        select(p || node);
        return;
      }
      select(node);
      return;
    }
    if (e.target.closest(".canvas-board") || e.target === canvas) {
      clear();
    }
  });

  // Esc：选中父级；再 Esc 取消选中
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!selected || !canvas.contains(selected)) return;
    const p = findParentContainer(selected);
    if (p) select(p);
    else clear();
  });

  return { select, clear, getSelected, renderInspector };
}

export function applyWidth(el, width) {
  WIDTHS.forEach((w) => el.classList.remove(`width-${w.replace("/", "-")}`));
  el.dataset.width = width;
  el.classList.add(`width-${width.replace("/", "-")}`);
}

export function applyLayout(el, layout) {
  LAYOUTS.forEach((l) => el.classList.remove(`layout-${l}`));
  el.dataset.layout = layout;
  el.classList.add(`layout-${layout}`);
  if (layout === "grid" && !el.dataset.cols) {
    applyCols(el, "2");
  }
}

export function applyStyle(el, style) {
  STYLES.forEach((s) => el.classList.remove(`style-${s}`));
  el.dataset.style = style;
  el.classList.add(`style-${style}`);
}

export function applyCols(el, cols) {
  ["2", "3", "4", "main-side"].forEach((c) =>
    el.classList.remove(`cols-${c}`)
  );
  el.dataset.cols = cols;
  el.classList.add(`cols-${cols}`);
}

export function applySpan(el, span) {
  ["1", "2", "3", "full"].forEach((s) => el.classList.remove(`span-${s}`));
  el.dataset.span = span;
  el.classList.add(`span-${span}`);
}

export function applyChrome(el, chrome) {
  el.classList.remove("chrome-show", "chrome-hide");
  el.dataset.chrome = chrome;
  el.classList.add(`chrome-${chrome}`);
}

export function applyAlign(el, align) {
  ["start", "center", "end", "stretch"].forEach((a) =>
    el.classList.remove(`align-${a}`)
  );
  el.dataset.align = align;
  el.classList.add(`align-${align}`);
}

export function applyJustify(el, justify) {
  ["start", "center", "end"].forEach((j) =>
    el.classList.remove(`justify-${j}`)
  );
  el.dataset.justify = justify;
  el.classList.add(`justify-${justify}`);
}

export function applyLayoutPreset(containerEl, presetId) {
  const preset = LAYOUT_PRESETS[presetId];
  if (!preset) return;
  applyLayout(containerEl, "grid");
  applyCols(containerEl, preset.cols);
  const body = getContainerBody(containerEl);
  if (!body) return;
  const children = [...body.children].filter((n) => n.classList.contains("node"));
  children.forEach((child, i) => {
    const span = preset.spans[i % preset.spans.length];
    applySpan(child, span);
    // grid 下宽度交给 span，避免 flex 宽度干扰
    if (child.dataset.kind === "component") {
      WIDTHS.forEach((w) =>
        child.classList.remove(`width-${w.replace("/", "-")}`)
      );
    }
  });
}

function moveChild(body, child, dir) {
  const nodes = [...body.children].filter((n) => n.classList.contains("node"));
  const index = nodes.indexOf(child);
  if (index < 0) return;

  if (dir === "up" && index > 0) {
    body.insertBefore(child, nodes[index - 1]);
    return;
  }
  if (dir === "down" && index < nodes.length - 1) {
    const next = nodes[index + 1];
    if (next.nextSibling) body.insertBefore(child, next.nextSibling);
    else body.appendChild(child);
    return;
  }
  if (dir === "top" && index > 0) {
    body.insertBefore(child, nodes[0]);
    return;
  }
  if (dir === "bottom" && index < nodes.length - 1) {
    body.appendChild(child);
  }
}
