/**
 * 叶子组件渲染器。新增组件时在此增加 case / 映射函数。
 */

const RENDERERS = {
  heading(el, props) {
    const level = Math.min(3, Math.max(1, Number(props.level) || 1));
    const text = String(props.text || "Title");
    const accent = props.accentWord ? String(props.accentWord) : "";
    let html = text;
    if (accent && text.includes(accent)) {
      html = text.replace(
        accent,
        `<span class="accent">${escapeHtml(accent)}</span>`
      );
    } else {
      html = escapeHtml(text);
    }
    el.innerHTML = `<div class="comp-heading h${level}">${html}</div>`;
  },

  text(el, props) {
    el.innerHTML = `<p class="comp-text">${escapeHtml(props.text || "")}</p>`;
  },

  label(el, props) {
    el.innerHTML = `<div class="comp-label">${escapeHtml(props.text || "")}</div>`;
  },

  definition(el, props) {
    el.innerHTML = `
      <div class="comp-definition">
        <div class="comp-definition-body">${props.body || ""}</div>
        ${
          props.footnote
            ? `<div class="comp-definition-foot"><span class="info-dot">i</span>${escapeHtml(
                props.footnote
              )}</div>`
            : ""
        }
      </div>`;
  },

  metric(el, props) {
    el.innerHTML = `
      <div class="comp-metric">
        <div class="comp-metric-value">${escapeHtml(props.value || "")}</div>
        <div class="comp-metric-meta">
          <span>${escapeHtml(props.caption || "")}</span>
          ${
            props.trend
              ? `<span class="trend">${escapeHtml(props.trend)}</span>`
              : ""
          }
        </div>
      </div>`;
  },

  "metric-mini"(el, props) {
    el.innerHTML = `
      <div class="comp-metric-mini">
        <span class="mm-label">${escapeHtml(props.label || "")}</span>
        <span class="mm-value">${escapeHtml(props.value || "")}</span>
      </div>`;
  },

  "chart-line"(el, props) {
    el.innerHTML = `
      <div class="comp-chart">
        <div class="comp-chart-title">${escapeHtml(props.title || "")}</div>
        <svg class="chart-svg" viewBox="0 0 200 80" preserveAspectRatio="none" aria-hidden="true">
          <path d="M8 72 C40 70, 50 40, 80 36 S140 20, 192 8" fill="none" stroke="currentColor" stroke-width="2.5"/>
          <circle cx="8" cy="72" r="3" fill="currentColor"/>
        </svg>
        ${
          props.caption
            ? `<div class="comp-status-strip">${escapeHtml(props.caption)}</div>`
            : ""
        }
      </div>`;
  },

  "chart-bar"(el, props) {
    el.innerHTML = `
      <div class="comp-chart">
        <div class="comp-chart-title">${escapeHtml(props.title || "")}</div>
        <div class="bar-row" aria-hidden="true">
          <i style="--h:40%"></i><i style="--h:65%"></i><i style="--h:48%"></i>
          <i style="--h:80%"></i><i style="--h:55%"></i><i style="--h:72%"></i>
        </div>
      </div>`;
  },

  progress(el, props) {
    const v = clamp(Number(props.value) || 0, 0, 100);
    el.innerHTML = `
      <div class="comp-progress">
        <div class="comp-progress-head">
          <span>${escapeHtml(props.label || "")}</span>
          <span>${v}%</span>
        </div>
        <div class="comp-progress-track"><div class="comp-progress-fill" style="width:${v}%"></div></div>
      </div>`;
  },

  "progress-ring"(el, props) {
    const v = clamp(Number(props.value) || 0, 0, 100);
    const r = 18;
    const c = 2 * Math.PI * r;
    const offset = c * (1 - v / 100);
    el.innerHTML = `
      <div class="comp-ring">
        <svg width="56" height="56" viewBox="0 0 44 44">
          <circle cx="22" cy="22" r="${r}" fill="none" stroke="#e8e6f5" stroke-width="5"/>
          <circle cx="22" cy="22" r="${r}" fill="none" stroke="#6c5ce7" stroke-width="5"
            stroke-dasharray="${c}" stroke-dashoffset="${offset}"
            stroke-linecap="round" transform="rotate(-90 22 22)"/>
        </svg>
        <div class="comp-ring-meta">
          <strong>${v}%</strong>
          <span>${escapeHtml(props.label || "")}</span>
        </div>
      </div>`;
  },

  checklist(el, props) {
    const items = Array.isArray(props.items) ? props.items : [];
    el.innerHTML = `
      <ul class="comp-checklist">
        ${items
          .map(
            (it) => `
          <li class="${it.done ? "done" : ""} ${it.warn ? "warn" : ""}">
            <span class="check">${it.done ? "✓" : ""}</span>
            <span>${escapeHtml(it.text || "")}</span>
            ${it.warn ? '<span class="warn-badge">Deadline</span>' : ""}
          </li>`
          )
          .join("")}
      </ul>`;
  },

  tags(el, props) {
    const tags = Array.isArray(props.tags) ? props.tags : [];
    el.innerHTML = `
      <div class="comp-tags">
        ${tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
      </div>`;
  },

  callout(el, props) {
    el.innerHTML = `
      <div class="comp-callout-inner">
        <div class="comp-callout-title">${escapeHtml(props.title || "")}</div>
        <p>${escapeHtml(props.body || "")}</p>
      </div>`;
  },

  image(el, props) {
    el.innerHTML = `
      <div class="comp-image" aria-label="illustration">
        <div class="comp-image-art"></div>
        <span>${escapeHtml(props.caption || "Illustration")}</span>
      </div>`;
  },

  "status-bar"(el, props) {
    el.innerHTML = `<div class="comp-status-strip">${escapeHtml(
      props.text || ""
    )}</div>`;
  },
};

export function renderComponent(el, typeId, props) {
  const fn = RENDERERS[typeId];
  if (!fn) {
    el.innerHTML = `<div class="comp-fallback">Unknown: ${escapeHtml(
      typeId
    )}</div>`;
    return;
  }
  fn(el, props || {});
}

export function registerComponentRenderer(typeId, fn) {
  RENDERERS[typeId] = fn;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}
