import {
  CONTAINER_CATEGORIES,
  COMPONENT_DEFS,
  COMPONENT_CATEGORIES,
  listPaletteContainers,
} from "./core/registry.js";
import { initDragDrop } from "./core/dragdrop.js";
import { createSelectionController } from "./core/selection.js";
import {
  serializeTree,
  hydrateTree,
  downloadJson,
} from "./core/serialize.js";
import { DOMAIN_DEMO } from "./data/demo-domain.js";

const canvas = document.querySelector("#canvas");
const board = document.querySelector("#board");
const palette = document.querySelector("#palette");
const inspector = document.querySelector("#inspector");

function bindNode(node) {
  if (node.dataset.kind === "container") {
    node.draggable = true;
    const body = node.querySelector("[data-role='body']");
    if (body) {
      [...body.children].forEach((child) => {
        if (child.classList.contains("node")) bindNode(child);
      });
    }
  } else {
    node.draggable = true;
  }
}

function buildPalette() {
  palette.innerHTML = "";

  for (const cat of CONTAINER_CATEGORIES) {
    const items = listPaletteContainers().filter((d) => d.category === cat.id);
    if (!items.length) continue;
    palette.appendChild(sectionTitle(cat.label));
    for (const def of items) {
      palette.appendChild(paletteItem("container", def));
    }
  }

  palette.appendChild(sectionTitle("组件库"));
  for (const cat of COMPONENT_CATEGORIES) {
    const items = COMPONENT_DEFS.filter((d) => d.category === cat.id);
    if (!items.length) continue;
    const group = document.createElement("div");
    group.className = "palette-group";
    group.innerHTML = `<div class="palette-sub">${cat.label}</div>`;
    for (const def of items) {
      group.appendChild(paletteItem("component", def));
    }
    palette.appendChild(group);
  }
}

function sectionTitle(text) {
  const h = document.createElement("h3");
  h.className = "palette-title";
  h.textContent = text;
  return h;
}

function paletteItem(kind, def) {
  const el = document.createElement("div");
  el.className = "palette-item";
  el.draggable = true;
  el.dataset.paletteItem = "1";
  el.dataset.kind = kind;
  el.dataset.type = def.id;
  el.innerHTML = `
    <span class="palette-icon" draggable="false">${def.icon || "•"}</span>
    <span class="palette-meta" draggable="false">
      <strong draggable="false">${def.label}</strong>
      ${def.hint ? `<small draggable="false">${def.hint}</small>` : ""}
    </span>
  `;
  return el;
}

buildPalette();

const selection = createSelectionController({ canvas, inspector });

initDragDrop({
  root: canvas,
  board,
  palette,
  onSelect: selection.select,
  bindNode,
});

canvas.addEventListener("click", (e) => {
  if (e.target === canvas || e.target === board) selection.clear();
});

document.querySelector("#btn-demo")?.addEventListener("click", () => {
  hydrateTree(board, DOMAIN_DEMO, bindNode);
  selection.clear();
});

document.querySelector("#btn-reset")?.addEventListener("click", () => {
  board.innerHTML = "";
  selection.clear();
});

document.querySelector("#btn-export")?.addEventListener("click", () => {
  downloadJson(serializeTree(board), "aigui-layout.json");
});

document.querySelector("#btn-import")?.addEventListener("click", () => {
  document.querySelector("#import-file").click();
});

document.querySelector("#import-file")?.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    hydrateTree(board, data, bindNode);
    selection.clear();
  } catch (err) {
    alert("导入失败：" + err.message);
  }
  e.target.value = "";
});

hydrateTree(board, DOMAIN_DEMO, bindNode);
