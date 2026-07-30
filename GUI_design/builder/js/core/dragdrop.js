/**
 * 拖拽：侧栏插入 + 画布内移动；支持落入任意容器 body / 画布根。
 * 使用事件委托 + text/plain JSON，避免「先绑定后渲染」与自定义 MIME 兼容问题。
 */

import { DND, isContainerType } from "./registry.js";
import {
  createNodeFromPalette,
  getContainerBody,
} from "../render/nodes.js";

function packPayload(data) {
  return JSON.stringify(data);
}

function unpackPayload(dt) {
  const raw =
    dt.getData("application/x-aigui") ||
    dt.getData("text/plain") ||
    dt.getData(DND.SOURCE);
  if (!raw) return null;
  try {
    const obj = JSON.parse(raw);
    if (obj && (obj.kind || obj.source)) return obj;
  } catch {
    /* 兼容旧自定义字段 */
  }
  const kind = dt.getData(DND.KIND);
  const type = dt.getData(DND.TYPE);
  if (!kind || !type) return null;
  return {
    source: dt.getData(DND.SOURCE) || "palette",
    kind,
    type,
    nodeId: dt.getData(DND.NODE_ID) || "",
  };
}

export function initDragDrop({ root, board, palette, onSelect, bindNode }) {
  // 侧栏：事件委托（组件动态生成也有效）
  palette.addEventListener("dragstart", (e) => {
    const item = e.target.closest("[data-palette-item]");
    if (!item || !palette.contains(item)) return;
    const payload = {
      source: "palette",
      kind: item.dataset.kind,
      type: item.dataset.type,
    };
    e.dataTransfer.effectAllowed = "copy";
    e.dataTransfer.setData("application/x-aigui", packPayload(payload));
    e.dataTransfer.setData("text/plain", packPayload(payload));
    item.classList.add("dragging");
  });

  palette.addEventListener("dragend", (e) => {
    const item = e.target.closest("[data-palette-item]");
    if (item) item.classList.remove("dragging");
    clearDropHints();
  });

  // 画布内移动
  board.addEventListener("dragstart", (e) => {
    const node = e.target.closest(".node");
    if (!node || !board.contains(node)) return;
    if (e.target.closest(".container-chrome button, input, select, textarea")) {
      e.preventDefault();
      return;
    }
    // 从容器 chrome 或组件本身开始拖
    const payload = {
      source: "move",
      kind: node.dataset.kind,
      type: node.dataset.type,
      nodeId: node.dataset.nodeId,
    };
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("application/x-aigui", packPayload(payload));
    e.dataTransfer.setData("text/plain", packPayload(payload));
    node.classList.add("dragging");
    e.stopPropagation();
  });

  board.addEventListener("dragend", (e) => {
    const node = e.target.closest(".node");
    if (node) node.classList.remove("dragging");
    clearDropHints();
  });

  // 在整个设计区（含滚动留白）允许 drop
  const dropRoots = [root, board];
  for (const el of dropRoots) {
    el.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const zone = findDropZone(e.target);
      clearDropHints();
      if (zone) zone.classList.add("drop-hover");
      e.dataTransfer.dropEffect = "copy";
    });

    el.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      clearDropHints();
      handleDrop(e);
    });
  }

  function handleDrop(e) {
    const payload = unpackPayload(e.dataTransfer);
    if (!payload) return;

    let zone = findDropZone(e.target) || board;

    if (payload.source === "move" && payload.nodeId) {
      const moving = board.querySelector(`[data-node-id="${payload.nodeId}"]`);
      if (!moving) return;
      if (wouldNestIntoSelf(moving, zone)) return;
      insertIntoZone(zone, moving, e.clientY);
      onSelect?.(moving);
      return;
    }

    const { kind, type } = payload;
    if (!kind || !type) return;

    let targetZone = zone;
    // 叶子组件落到画布根时，自动包一层卡片容器
    if (
      (zone === board || zone?.dataset?.role === "board") &&
      kind === "component" &&
      !isContainerType(type)
    ) {
      const wrap = createNodeFromPalette("container", "preset-card");
      bindNode(wrap);
      board.appendChild(wrap);
      targetZone = getContainerBody(wrap);
      onSelect?.(wrap);
    }

    try {
      const node = createNodeFromPalette(kind, type);
      bindNode(node);
      insertIntoZone(targetZone, node, e.clientY);
      onSelect?.(node);
    } catch (err) {
      console.error("[AIGUI] drop failed:", err);
    }
  }

  function clearDropHints() {
    root.querySelectorAll(".drop-hover").forEach((el) => {
      el.classList.remove("drop-hover");
    });
  }

  function findDropZone(target) {
    if (!(target instanceof Element)) return board;
    // 落到某个容器上（含标题栏）→ 进入该容器 body，支持嵌套
    const container = target.closest(".node.container");
    if (container && board.contains(container)) {
      const body = container.querySelector(":scope > [data-role='body']");
      if (body) return body;
    }
    const body = target.closest("[data-role='body']");
    if (body && board.contains(body)) return body;
    if (board.contains(target) || target === board) return board;
    if (root.contains(target)) return board;
    return board;
  }

  function insertIntoZone(zone, node, clientY) {
    if (!zone) return;
    const children = [...zone.children].filter(
      (c) => c.classList.contains("node") && c !== node
    );
    let before = null;
    for (const child of children) {
      const rect = child.getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      if (clientY < mid) {
        before = child;
        break;
      }
    }
    if (before) zone.insertBefore(node, before);
    else zone.appendChild(node);
  }

  function wouldNestIntoSelf(moving, zone) {
    if (!moving.classList.contains("container")) return false;
    return moving === zone || moving.contains(zone);
  }
}
