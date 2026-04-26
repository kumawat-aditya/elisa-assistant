// ============================================================================
// Log Observatory — stream / grid / heatmap / timeline + filters + search
// ============================================================================
import {
  $,
  $$,
  el,
  fmtTime,
  escapeHtml,
  colorFromString,
  downloadJSONL,
  debounce,
} from "../utils.js";
import * as store from "../store.js";

const LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "PRINT"];

export function initLogs() {
  const root = $("#panel-logs");

  // ---- Filter state ------------------------------------------------------
  const filters = {
    levels: new Set(LEVELS),
    files: new Set(), // empty == all
    search: "",
    regex: false,
    case: false,
    paused: false,
    tail: true,
    view: "stream",
  };

  // ---- Stream ------------------------------------------------------------
  const streamEl = $("#logs-stream");
  const fileChipsEl = $("#file-chips");
  const lvlChipsEl = $("#lvl-chips");
  const detailEl = $("#log-detail");
  const detailBody = $("#log-detail-body");
  const expandBtn = $("#logs-expand");
  const pauseBtn = $("#logs-pause");
  const tailBtn = $("#logs-tail");
  const clearBtn = $("#logs-clear");
  const exportBtn = $("#logs-export");
  const searchInput = $("#logs-search");
  const regexCb = $("#search-regex");
  const caseCb = $("#search-case");
  const searchClear = $("#search-clear");

  // Init level chips active state
  $$("[data-level]", lvlChipsEl).forEach((c) => c.classList.add("active"));
  lvlChipsEl.addEventListener("click", (e) => {
    const t = e.target.closest("[data-level]");
    if (!t) return;
    const lv = t.dataset.level;
    if (filters.levels.has(lv)) {
      filters.levels.delete(lv);
      t.classList.remove("active");
    } else {
      filters.levels.add(lv);
      t.classList.add("active");
    }
    rebuildStream();
  });

  // File chips
  function rebuildFileChips() {
    const files = Array.from(store.state.fileMap.keys()).sort();
    if (files.length === 0) {
      fileChipsEl.innerHTML = `<span class="muted">no files yet</span>`;
      return;
    }
    fileChipsEl.innerHTML = "";
    fileChipsEl.appendChild(
      el(
        "button",
        {
          class: "file-chip" + (filters.files.size === 0 ? " active" : ""),
          onclick: () => {
            filters.files.clear();
            rebuildFileChips();
            rebuildStream();
          },
        },
        "all",
      ),
    );
    for (const f of files) {
      const color = colorFromString(f);
      const isActive = filters.files.size === 0 ? false : filters.files.has(f);
      fileChipsEl.appendChild(
        el(
          "button",
          {
            class: "file-chip" + (isActive ? " active" : ""),
            title: f,
            onclick: (ev) => {
              if (ev.ctrlKey || ev.metaKey) {
                if (filters.files.has(f)) filters.files.delete(f);
                else filters.files.add(f);
              } else {
                if (filters.files.size === 1 && filters.files.has(f))
                  filters.files.clear();
                else {
                  filters.files.clear();
                  filters.files.add(f);
                }
              }
              rebuildFileChips();
              rebuildStream();
            },
          },
          el("span", {
            class: "file-chip__swatch",
            style: `background:${color}`,
          }),
          shortName(f),
          el(
            "span",
            { class: "muted", style: "margin-left:4px" },
            `(${store.state.fileMap.get(f)})`,
          ),
        ),
      );
    }
  }

  function shortName(p) {
    const parts = p.split("/");
    return parts[parts.length - 1] || p;
  }

  // Search
  const onSearch = debounce(() => {
    filters.search = searchInput.value;
    rebuildStream();
  }, 100);
  searchInput.addEventListener("input", onSearch);
  regexCb.addEventListener("change", () => {
    filters.regex = regexCb.checked;
    rebuildStream();
  });
  caseCb.addEventListener("change", () => {
    filters.case = caseCb.checked;
    rebuildStream();
  });
  searchClear.addEventListener("click", () => {
    searchInput.value = "";
    filters.search = "";
    rebuildStream();
  });

  // Pause / tail / clear / export / expand
  pauseBtn.addEventListener("click", () => {
    filters.paused = !filters.paused;
    pauseBtn.textContent = filters.paused ? "▶ resume" : "⏸ pause";
    pauseBtn.classList.toggle("active", filters.paused);
    if (!filters.paused) rebuildStream();
  });
  tailBtn.addEventListener("click", () => {
    filters.tail = !filters.tail;
    tailBtn.classList.toggle("active", filters.tail);
  });
  clearBtn.addEventListener("click", () => {
    streamEl.innerHTML = "";
  });
  exportBtn.addEventListener("click", () => {
    const items = applyFilters(store.state.logs);
    downloadJSONL(`elisa-logs-${Date.now()}.jsonl`, items);
  });
  expandBtn.addEventListener("click", () => {
    document.querySelector(".grid").classList.toggle("grid--logs-expanded");
  });

  // View toggles
  $$(".vbtn").forEach((b) =>
    b.addEventListener("click", () => {
      $$(".vbtn").forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      filters.view = b.dataset.view;
      $$(".logs-view").forEach((v) =>
        v.classList.toggle("active", v.dataset.view === filters.view),
      );
      if (filters.view === "grid") renderGrid();
      if (filters.view === "heatmap") renderHeatmap();
      if (filters.view === "timeline") renderTimeline();
    }),
  );

  // ---- Filters / matching ----------------------------------------------
  function buildMatcher() {
    if (!filters.search) return null;
    if (filters.regex) {
      try {
        return new RegExp(filters.search, filters.case ? "g" : "ig");
      } catch {
        return null;
      }
    }
    const q = filters.case ? filters.search : filters.search.toLowerCase();
    return { test: (s) => (filters.case ? s : s.toLowerCase()).includes(q) };
  }

  function passes(log, matcher) {
    if (!filters.levels.has(log.level)) return false;
    if (filters.files.size > 0 && !filters.files.has(log.source_file))
      return false;
    if (matcher && !matcher.test(log.message)) return false;
    return true;
  }

  function applyFilters(arr) {
    const m = buildMatcher();
    return arr.filter((l) => passes(l, m));
  }

  function highlight(text, matcher) {
    if (!matcher || !filters.search) return escapeHtml(text);
    if (matcher instanceof RegExp) {
      return escapeHtml(text).replace(
        new RegExp(filters.search, filters.case ? "g" : "ig"),
        (m) => `<mark>${m}</mark>`,
      );
    }
    const idx = (filters.case ? text : text.toLowerCase()).indexOf(
      filters.case ? filters.search : filters.search.toLowerCase(),
    );
    if (idx < 0) return escapeHtml(text);
    return (
      escapeHtml(text.slice(0, idx)) +
      `<mark>${escapeHtml(text.slice(idx, idx + filters.search.length))}</mark>` +
      escapeHtml(text.slice(idx + filters.search.length))
    );
  }

  // ---- Stream rendering --------------------------------------------------
  const MAX_DOM = 600;
  function rowFor(log, matcher) {
    const swatchColor = colorFromString(log.source_file || "?");
    const row = el("div", {
      class: "log-row log-row--new",
      dataset: { level: log.level },
      onclick: () => showDetail(log),
    });
    row.innerHTML = `
      <div class="log-row__time">${escapeHtml(fmtTime(log.timestamp))}</div>
      <div class="log-row__lvl">${escapeHtml(log.level)}</div>
      <div class="log-row__src" title="${escapeHtml(log.source_file)}:${log.line}"><span class="src-swatch" style="background:${swatchColor}"></span>${escapeHtml(shortName(log.source_file))}:${log.line}</div>
      <div class="log-row__msg">${highlight(log.message, matcher)}</div>
    `;
    setTimeout(() => row.classList.remove("log-row--new"), 700);
    return row;
  }

  function rebuildStream() {
    const matcher = buildMatcher();
    const items = applyFilters(store.state.logs).slice(-MAX_DOM);
    streamEl.innerHTML = "";
    const frag = document.createDocumentFragment();
    for (const log of items) frag.appendChild(rowFor(log, matcher));
    streamEl.appendChild(frag);
    if (filters.tail) streamEl.scrollTop = streamEl.scrollHeight;
  }

  function appendStream(log) {
    if (filters.paused) return;
    const matcher = buildMatcher();
    if (!passes(log, matcher)) return;
    streamEl.appendChild(rowFor(log, matcher));
    while (streamEl.children.length > MAX_DOM) streamEl.firstChild.remove();
    if (filters.tail) streamEl.scrollTop = streamEl.scrollHeight;
  }

  // ---- Grid view --------------------------------------------------------
  const gridEl = $("#logs-grid");
  function renderGrid() {
    const files = Array.from(store.state.fileMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([f]) => f);
    gridEl.innerHTML = "";
    for (const f of files) {
      const col = el("div", { class: "logs-grid__col" });
      const head = el(
        "div",
        { class: "logs-grid__head" },
        el("span", {}, shortName(f)),
        el("span", { class: "muted" }, `${store.state.fileMap.get(f)} entries`),
      );
      const body = el("div", {
        class: "logs-grid__body",
        dataset: { file: f },
      });
      const recent = store.state.logs
        .filter((l) => l.source_file === f)
        .slice(-200);
      for (const log of recent) {
        body.appendChild(
          el(
            "div",
            {
              class: "logs-grid__row",
              dataset: { level: log.level },
              title: log.message,
            },
            `${fmtTime(log.timestamp)}  ${log.message}`,
          ),
        );
      }
      body.scrollTop = body.scrollHeight;
      col.appendChild(head);
      col.appendChild(body);
      gridEl.appendChild(col);
    }
  }

  function appendToGrid(log) {
    const body = gridEl.querySelector(
      `.logs-grid__body[data-file="${CSS.escape(log.source_file)}"]`,
    );
    if (!body) {
      renderGrid();
      return;
    }
    const row = el(
      "div",
      {
        class: "logs-grid__row",
        dataset: { level: log.level },
        title: log.message,
      },
      `${fmtTime(log.timestamp)}  ${log.message}`,
    );
    body.appendChild(row);
    while (body.children.length > 200) body.firstChild.remove();
    body.scrollTop = body.scrollHeight;
  }

  // ---- Heatmap view -----------------------------------------------------
  const heatEl = $("#logs-heatmap");
  function renderHeatmap() {
    const buckets = 60; // 1 sec each
    const now = Date.now();
    const fileBuckets = new Map();
    for (const log of store.state.logs) {
      const ts = new Date(log.timestamp).getTime();
      const bIdx = Math.floor((now - ts) / 1000);
      if (bIdx < 0 || bIdx >= buckets) continue;
      if (!fileBuckets.has(log.source_file))
        fileBuckets.set(log.source_file, {
          counts: new Array(buckets).fill(0),
          errs: new Array(buckets).fill(0),
        });
      const fb = fileBuckets.get(log.source_file);
      fb.counts[buckets - 1 - bIdx]++;
      if (log.level === "ERROR") fb.errs[buckets - 1 - bIdx]++;
    }
    const items = Array.from(fileBuckets.entries())
      .sort((a, b) => sum(b[1].counts) - sum(a[1].counts))
      .slice(0, 12);
    const max = Math.max(1, ...items.flatMap(([, v]) => v.counts));

    heatEl.innerHTML = "";
    const grid = el("div", { class: "heatmap-grid" });
    grid.appendChild(
      el(
        "div",
        { class: "heatmap-row" },
        el("div", { class: "heatmap-row__name muted" }, `last ${buckets}s →`),
        el("div", { class: "heatmap-row__cells" }),
      ),
    );
    for (const [file, fb] of items) {
      const row = el("div", { class: "heatmap-row" });
      row.appendChild(
        el("div", { class: "heatmap-row__name", title: file }, shortName(file)),
      );
      const cells = el("div", { class: "heatmap-row__cells" });
      for (let i = 0; i < buckets; i++) {
        const c = fb.counts[i],
          e = fb.errs[i];
        const intensity = c / max;
        const bg =
          e > 0
            ? `rgba(248,113,113, ${0.15 + intensity * 0.85})`
            : `rgba(0,245,255, ${0.05 + intensity * 0.65})`;
        const cell = el("div", {
          class: "heatmap-cell",
          title: `${c} entries${e ? `, ${e} errors` : ""}`,
          style: `background:${bg}`,
        });
        cells.appendChild(cell);
      }
      row.appendChild(cells);
      grid.appendChild(row);
    }
    heatEl.appendChild(grid);
  }

  function sum(a) {
    return a.reduce((x, y) => x + y, 0);
  }

  // ---- Timeline view ----------------------------------------------------
  const timelineCanvas = $("#logs-timeline");
  function renderTimeline() {
    const ctx = timelineCanvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio, 2);
    const w = timelineCanvas.clientWidth,
      h = timelineCanvas.clientHeight;
    timelineCanvas.width = w * dpr;
    timelineCanvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const now = Date.now();
    const span = 60_000; // 60s
    const recent = store.state.logs.filter(
      (l) => now - new Date(l.timestamp).getTime() < span,
    );

    // x grid
    ctx.strokeStyle = "rgba(255,255,255,0.04)";
    for (let s = 0; s <= 60; s += 5) {
      const x = w - (s / 60) * w;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    const levels = ["DEBUG", "INFO", "PRINT", "WARNING", "ERROR"];
    levels.forEach((lvl, idx) => {
      const y = (idx + 0.5) * (h / levels.length);
      ctx.fillStyle = "rgba(230,235,255,0.3)";
      ctx.font = "10px JetBrains Mono";
      ctx.fillText(lvl, 6, y + 3);
    });

    for (const log of recent) {
      const ts = new Date(log.timestamp).getTime();
      const x = w - ((now - ts) / span) * w;
      const idx = levels.indexOf(log.level);
      if (idx < 0) continue;
      const y = (idx + 0.5) * (h / levels.length);
      ctx.fillStyle =
        log.level === "ERROR"
          ? "rgba(248,113,113,0.85)"
          : log.level === "WARNING"
            ? "rgba(251,191,36,0.85)"
            : log.level === "INFO"
              ? "rgba(56,189,248,0.85)"
              : log.level === "DEBUG"
                ? "rgba(148,163,184,0.85)"
                : "rgba(229,231,235,0.85)";
      ctx.beginPath();
      ctx.arc(x, y, 2.4, 0, Math.PI * 2);
      ctx.fill();
    }

    if (filters.view === "timeline") requestAnimationFrame(renderTimeline);
  }

  // ---- Detail flyout ----------------------------------------------------
  function showDetail(log) {
    detailBody.textContent = JSON.stringify(log, null, 2);
    detailEl.hidden = false;
  }
  $("#log-detail-close").addEventListener("click", () => {
    detailEl.hidden = true;
  });
  $("#log-detail-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(detailBody.textContent);
    } catch (_) {}
  });

  // ---- Wire up store -----------------------------------------------------
  store.on("log", (log) => {
    if (filters.view === "stream") appendStream(log);
    else if (filters.view === "grid") appendToGrid(log);
    else if (filters.view === "heatmap") {
      // throttle heatmap refresh
      heatRefresh();
    }
  });
  const heatRefresh = debounce(renderHeatmap, 500);

  store.on("logs:replaced", () => {
    rebuildFileChips();
    rebuildStream();
  });
  store.on("files:changed", debounce(rebuildFileChips, 200));
  store.on("snapshot", () => {
    rebuildFileChips();
    rebuildStream();
  });

  // initial paint
  rebuildFileChips();
  rebuildStream();
}
