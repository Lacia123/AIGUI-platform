/**
 * 根据 propsSchema 渲染可编辑表单字段，并解析回 props。
 */

export function renderPropsFields(schema, props, { idPrefix = "prop" } = {}) {
  if (!schema?.length) {
    return `<p class="muted tip">该组件暂无可编辑字段。</p>`;
  }
  return schema
    .map((field) => {
      const key = field.key;
      const val = props?.[key];
      const id = `${idPrefix}-${key}`;
      const hint = field.hint
        ? `<p class="muted tip">${escapeHtml(field.hint)}</p>`
        : "";

      if (field.type === "textarea") {
        return `
          <div class="field">
            <label for="${id}">${escapeHtml(field.label || key)}</label>
            <textarea id="${id}" data-prop="${escapeHtml(key)}" rows="3">${escapeHtml(
              val ?? ""
            )}</textarea>
            ${hint}
          </div>`;
      }

      if (field.type === "number") {
        const min =
          field.min != null ? ` min="${Number(field.min)}"` : "";
        const max =
          field.max != null ? ` max="${Number(field.max)}"` : "";
        return `
          <div class="field">
            <label for="${id}">${escapeHtml(field.label || key)}</label>
            <input id="${id}" type="number" data-prop="${escapeHtml(
              key
            )}" data-prop-type="number" value="${escapeAttr(
              val ?? ""
            )}"${min}${max} />
            ${hint}
          </div>`;
      }

      if (field.type === "select" && Array.isArray(field.options)) {
        return `
          <div class="field">
            <label for="${id}">${escapeHtml(field.label || key)}</label>
            <select id="${id}" data-prop="${escapeHtml(key)}" data-prop-type="select">
              ${field.options
                .map((opt) => {
                  const ov = opt.value;
                  const selected =
                    String(val) === String(ov) ? " selected" : "";
                  return `<option value="${escapeAttr(ov)}"${selected}>${escapeHtml(
                    opt.label ?? ov
                  )}</option>`;
                })
                .join("")}
            </select>
            ${hint}
          </div>`;
      }

      if (field.type === "tags") {
        const text = Array.isArray(val) ? val.join(", ") : String(val ?? "");
        return `
          <div class="field">
            <label for="${id}">${escapeHtml(field.label || key)}</label>
            <input id="${id}" data-prop="${escapeHtml(
              key
            )}" data-prop-type="tags" value="${escapeAttr(text)}" />
            ${hint}
          </div>`;
      }

      if (field.type === "json") {
        let text = "";
        try {
          text =
            typeof val === "string" ? val : JSON.stringify(val ?? null, null, 2);
        } catch {
          text = String(val ?? "");
        }
        return `
          <div class="field">
            <label for="${id}">${escapeHtml(field.label || key)}</label>
            <textarea id="${id}" data-prop="${escapeHtml(
              key
            )}" data-prop-type="json" rows="8">${escapeHtml(text)}</textarea>
            ${hint}
          </div>`;
      }

      return `
        <div class="field">
          <label for="${id}">${escapeHtml(field.label || key)}</label>
          <input id="${id}" data-prop="${escapeHtml(
            key
          )}" value="${escapeAttr(val ?? "")}" />
          ${hint}
        </div>`;
    })
    .join("");
}

/** 从表单控件读出一个字段值 */
export function readPropControl(el) {
  const key = el.dataset.prop;
  if (!key) return null;
  const kind = el.dataset.propType || "string";
  const raw = el.value;

  if (kind === "number") {
    const n = Number(raw);
    return { key, value: Number.isFinite(n) ? n : 0 };
  }
  if (kind === "select") {
    const n = Number(raw);
    return {
      key,
      value: raw !== "" && Number.isFinite(n) && String(n) === raw ? n : raw,
    };
  }
  if (kind === "tags") {
    return {
      key,
      value: String(raw)
        .split(/[,，]/)
        .map((s) => s.trim())
        .filter(Boolean),
    };
  }
  if (kind === "json") {
    try {
      return { key, value: JSON.parse(raw) };
    } catch {
      return { key, value: raw, error: "JSON 格式无效" };
    }
  }
  return { key, value: raw };
}

/** 从表单根节点收集全部 props（合并到 base） */
export function collectPropsFromForm(formRoot, base = {}) {
  const next = { ...base };
  let error = null;
  for (const el of formRoot.querySelectorAll("[data-prop]")) {
    const parsed = readPropControl(el);
    if (!parsed) continue;
    if (parsed.error) error = `${parsed.key}: ${parsed.error}`;
    next[parsed.key] = parsed.value;
  }
  return { props: next, error };
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, "&#39;");
}
