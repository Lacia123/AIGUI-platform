/**
 * 统一注册入口：聚合容器与组件定义，供侧栏/渲染/序列化使用。
 */

import {
  CONTAINER_DEFS,
  CONTAINER_BY_ID,
  CONTAINER_CATEGORIES,
  listPaletteContainers,
} from "../../registry/containers.js";
import {
  COMPONENT_DEFS,
  COMPONENT_BY_ID,
  COMPONENT_CATEGORIES,
  getComponentPropsSchema,
} from "../../registry/components.js";

export {
  CONTAINER_DEFS,
  CONTAINER_BY_ID,
  CONTAINER_CATEGORIES,
  listPaletteContainers,
  COMPONENT_DEFS,
  COMPONENT_BY_ID,
  COMPONENT_CATEGORIES,
  getComponentPropsSchema,
};

export function getDef(kind, id) {
  if (kind === "container") return CONTAINER_BY_ID[id] || null;
  if (kind === "component") return COMPONENT_BY_ID[id] || null;
  return null;
}

export function isContainerType(typeId) {
  return Boolean(CONTAINER_BY_ID[typeId]);
}

export function isComponentType(typeId) {
  return Boolean(COMPONENT_BY_ID[typeId]);
}

/** 拖拽 payload 约定 */
export const DND = {
  SOURCE: "builder/source", // palette | move
  KIND: "builder/kind", // container | component
  TYPE: "builder/type",
  NODE_ID: "builder/node-id",
};
