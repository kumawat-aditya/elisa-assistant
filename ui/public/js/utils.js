// ============================================================================
// utils.js — small, dependency-free helpers
// ============================================================================

export function $(sel, root = document) {
  return root.querySelector(sel);
}
export function $$(sel, root = document) {
  return Array.from(root.querySelectorAll(sel));
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "dataset") Object.assign(node.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}
export function clamp(x, lo, hi) {
  return x < lo ? lo : x > hi ? hi : x;
}

export function debounce(fn, ms = 100) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

export function throttle(fn, ms = 50) {
  let last = 0,
    queued = null,
    args;
  return function (...a) {
    const now = Date.now();
    args = a;
    if (now - last >= ms) {
      last = now;
      fn.apply(this, args);
    } else if (!queued) {
      queued = setTimeout(
        () => {
          last = Date.now();
          queued = null;
          fn.apply(this, args);
        },
        ms - (now - last),
      );
    }
  };
}

// Deterministic vibrant color from a string (HSL)
export function colorFromString(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) | 0;
  }
  const hue = Math.abs(h) % 360;
  return `hsl(${hue} 80% 60%)`;
}

export function fmtTime(iso) {
  try {
    const d = new Date(iso);
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    const ms = String(d.getMilliseconds()).padStart(3, "0");
    return `${hh}:${mm}:${ss}.${ms}`;
  } catch (_) {
    return "--:--:--";
  }
}

export function fmtRel(iso) {
  const d = new Date(iso).getTime();
  const diff = Date.now() - d;
  if (diff < 1000) return "now";
  if (diff < 60_000) return Math.floor(diff / 1000) + "s ago";
  if (diff < 3600_000) return Math.floor(diff / 60_000) + "m ago";
  return new Date(d).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtUptime(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = String(Math.floor(s / 3600)).padStart(2, "0");
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const sec = String(s % 60).padStart(2, "0");
  return `${h}:${m}:${sec}`;
}

export function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function downloadJSONL(filename, items) {
  const blob = new Blob([items.map((x) => JSON.stringify(x)).join("\n")], {
    type: "application/x-ndjson",
  });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), {
    href: url,
    download: filename,
  });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
