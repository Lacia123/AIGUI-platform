/**
 * 画布树 ↔ JSON 序列化，便于后续扩展 XML 导出。
 */

import {
  createContainerNode,
  createComponentNode,
  getContainerBody,
  readProps,
} from "../render/nodes.js";

export function serializeTree(board) {
  return {
    version: 1,
    children: [...board.children]
      .filter((n) => n.classList.contains("node"))
      .map(serializeNode),
  };
}

function serializeNode(el) {
  const base = {
    id: el.dataset.nodeId,
    kind: el.dataset.kind,
    type: el.dataset.type,
  };
  if (el.dataset.kind === "container") {
    const body = getContainerBody(el);
    return {
      ...base,
      width: el.dataset.width,
      layout: el.dataset.layout,
      style: el.dataset.style,
      cols: el.dataset.cols || "2",
      span: el.dataset.span || "1",
      chrome: el.dataset.chrome || "show",
      align: el.dataset.align || "center",
      justify: el.dataset.justify || "start",
      role: el.dataset.role || "",
      children: [...(body?.children || [])]
        .filter((n) => n.classList.contains("node"))
        .map(serializeNode),
    };
  }
  return {
    ...base,
    props: readProps(el),
    span: el.dataset.span || "1",
    width: el.dataset.width || "1/2",
  };
}

export function hydrateTree(board, data, bindNode) {
  board.innerHTML = "";
  const children = data?.children || [];
  for (const child of children) {
    board.appendChild(hydrateNode(child, bindNode));
  }
}

function hydrateNode(data, bindNode) {
  if (data.kind === "container") {
    const el = createContainerNode(data.type, {
      id: data.id,
      width: data.width,
      layout: data.layout,
      style: data.style,
      cols: data.cols,
      span: data.span,
      chrome: data.chrome,
      align: data.align,
      justify: data.justify,
      skipSeed: true,
    });
    bindNode(el);
    const body = getContainerBody(el);
    for (const child of data.children || []) {
      body.appendChild(hydrateNode(child, bindNode));
    }
    return el;
  }
  const el = createComponentNode(data.type, {
    id: data.id,
    props: data.props,
    span: data.span,
    width: data.width,
  });
  bindNode(el);
  return el;
}

export function downloadJson(obj, filename = "layout.json") {
  const blob = new Blob([JSON.stringify(obj, null, 2)], {
    type: "application/json",
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
