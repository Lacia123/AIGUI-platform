/**
 * 组件样式平铺预览：点击卡片展示 / 编辑可修改字段。
 */

import {
  COMPONENT_DEFS,
  COMPONENT_CATEGORIES,
  COMPONENT_BY_ID,
  getComponentPropsSchema,
} from "./core/registry.js";
import { renderComponent } from "./render/components.js";
import {
  renderPropsFields,
  collectPropsFromForm,
} from "./core/prop-fields.js";

const root = document.getElementById("preview-root");
const countEl = document.getElementById("preview-count");
const surfaceSelect = document.getElementById("surface-select");
const inspectorBody = document.getElementById("preview-inspector-body");

/** @type {Map<string, object>} */
const propsStore = new Map();
/** @type {string | null} */
let selectedType = null;

function catLabel(id) {
  return COMPONENT_CATEGORIES.find((c) => c.id === id)?.label || id;
}

function getProps(typeId) {
  if (!propsStore.has(typeId)) {
    const def = COMPONENT_BY_ID[typeId];
    propsStore.set(typeId, structuredClone(def?.defaultProps || {}));
  }
  return propsStore.get(typeId);
}

function setProps(typeId, props) {
  propsStore.set(typeId, props);
}

function build() {
  if (!root) return;
  root.innerHTML = "";

  const byCat = new Map();
  for (const def of COMPONENT_DEFS) {
    const cat = def.category || "other";
    if (!byCat.has(cat)) byCat.set(cat, []);
    byCat.get(cat).push(def);
  }

  const order = COMPONENT_CATEGORIES.map((c) => c.id);
  const cats = [
    ...order.filter((id) => byCat.has(id)),
    ...[...byCat.keys()].filter((id) => !order.includes(id)),
  ];

  const surface = surfaceSelect?.value || "panel";

  for (const catId of cats) {
    const defs = byCat.get(catId) || [];
    const section = document.createElement("section");
    section.className = "preview-section";
    section.innerHTML = `
      <h2 class="preview-section-title">
        ${escapeHtml(catLabel(catId))}
        <em>${defs.length} 项</em>
      </h2>
    `;

    const grid = document.createElement("div");
    grid.className = "preview-grid";

    for (const def of defs) {
      grid.appendChild(makeCard(def, surface));
    }

    section.appendChild(grid);
    root.appendChild(section);
  }

  if (countEl) {
    countEl.textContent = `共 ${COMPONENT_DEFS.length} 个组件 · ${cats.length} 组`;
  }

  if (selectedType) {
    highlightSelected();
    renderInspector(selectedType);
  }
}

function makeCard(def, surface) {
  const card = document.createElement("article");
  card.className = "preview-card";
  card.dataset.type = def.id;
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-label", `查看 ${def.label} 可修改字段`);

  const schema = getComponentPropsSchema(def.id);
  const meta = document.createElement("div");
  meta.className = "preview-card-meta";
  meta.innerHTML = `
    <span class="name">${escapeHtml(def.icon || "")} ${escapeHtml(def.label)}</span>
    <span class="id">${escapeHtml(def.id)} · ${schema.length} 字段</span>
  `;

  const body = document.createElement("div");
  body.className = `preview-card-body surface-${surface}`;

  const node = document.createElement("div");
  node.className = "node component";
  node.dataset.kind = "component";
  node.dataset.type = def.id;
  node.dataset.previewHost = "1";

  renderComponent(node, def.id, getProps(def.id));
  body.appendChild(node);

  card.appendChild(meta);
  card.appendChild(body);

  card.addEventListener("click", () => selectType(def.id));
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      selectType(def.id);
    }
  });

  return card;
}

function selectType(typeId) {
  selectedType = typeId;
  highlightSelected();
  renderInspector(typeId);
}

function highlightSelected() {
  root?.querySelectorAll(".preview-card.is-selected").forEach((el) => {
    el.classList.remove("is-selected");
  });
  const card = root?.querySelector(
    `.preview-card[data-type="${CSS.escape(selectedType || "")}"]`
  );
  card?.classList.add("is-selected");
}

function renderInspector(typeId) {
  const def = COMPONENT_BY_ID[typeId];
  if (!def || !inspectorBody) return;

  const schema = getComponentPropsSchema(typeId);
  const props = getProps(typeId);
  const cat = catLabel(def.category);

  inspectorBody.innerHTML = `
    <div class="preview-detail-head">
      <div class="preview-detail-title">
        <span class="preview-detail-icon">${escapeHtml(def.icon || "•")}</span>
        <div>
          <strong>${escapeHtml(def.label)}</strong>
          <div class="mono">${escapeHtml(def.id)}</div>
        </div>
      </div>
      <p class="muted tip">分类：${escapeHtml(cat)} · 可修改 ${schema.length} 项</p>
    </div>
    <div class="preview-live surface-${surfaceSelect?.value || "panel"}" id="preview-live">
      <div class="node component" data-preview-live="1"></div>
    </div>
    <div class="preview-fields" id="preview-fields">
      ${renderPropsFields(schema, props, { idPrefix: `pv-${typeId}` })}
    </div>
    <div class="btn-row">
      <button type="button" id="btn-reset-props">恢复默认值</button>
    </div>
    <p class="muted tip" id="preview-prop-error" hidden></p>
  `;

  const liveNode = inspectorBody.querySelector("[data-preview-live]");
  if (liveNode) renderComponent(liveNode, typeId, props);

  inspectorBody.querySelector("#btn-reset-props")?.addEventListener("click", () => {
    setProps(typeId, structuredClone(def.defaultProps || {}));
    renderInspector(typeId);
    refreshCard(typeId);
  });
}

function applyFormToSelected() {
  if (!selectedType || !inspectorBody) return;
  const fields = inspectorBody.querySelector("#preview-fields");
  if (!fields) return;

  const { props, error } = collectPropsFromForm(fields, getProps(selectedType));
  const errEl = inspectorBody.querySelector("#preview-prop-error");
  if (error) {
    if (errEl) {
      errEl.hidden = false;
      errEl.textContent = error;
    }
    return;
  }
  if (errEl) {
    errEl.hidden = true;
    errEl.textContent = "";
  }

  setProps(selectedType, props);
  const liveNode = inspectorBody.querySelector("[data-preview-live]");
  if (liveNode) renderComponent(liveNode, selectedType, props);
  refreshCard(selectedType);
}

function refreshCard(typeId) {
  const card = root?.querySelector(`.preview-card[data-type="${CSS.escape(typeId)}"]`);
  const node = card?.querySelector(".node.component");
  if (node) renderComponent(node, typeId, getProps(typeId));
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

inspectorBody?.addEventListener("input", (e) => {
  if (e.target?.matches?.("[data-prop]")) applyFormToSelected();
});
inspectorBody?.addEventListener("change", (e) => {
  if (e.target?.matches?.("[data-prop]")) applyFormToSelected();
});

surfaceSelect?.addEventListener("change", () => {
  build();
});

build();
