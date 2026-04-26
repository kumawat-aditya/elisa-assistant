// System Vitals panel — services, sparklines, counters.
import { $, $$, el, fmtRel, fmtUptime } from "../utils.js";
import * as store from "../store.js";

export function initVitals() {
  const list = $("#services-list");

  function renderServices() {
    $$("li", list).forEach((li) => {
      const svc = li.dataset.svc;
      const status = store.state.services[svc] || "unknown";
      li.dataset.status = status;
      const meta = li.querySelector(".svc-meta");
      meta.textContent =
        status === "up" ? "live" : status === "down" ? "down" : status;
    });
  }

  // Sparkline canvases
  function drawSparkline(canvas, name) {
    const arr = store.state.metrics.get(name) || [];
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio, 2);
    const w = canvas.clientWidth,
      h = canvas.clientHeight;
    if (canvas.width !== w * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    ctx.clearRect(0, 0, w, h);
    if (arr.length < 2) {
      ctx.fillStyle = "rgba(230,235,255,0.3)";
      ctx.font = "10px JetBrains Mono";
      ctx.fillText("—", w / 2 - 4, h / 2 + 4);
      return;
    }
    const N = Math.min(60, arr.length);
    const data = arr.slice(-N).map((x) => x.value);
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = Math.max(1, max - min);

    // Gradient
    const grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, "rgba(0,245,255,0.9)");
    grad.addColorStop(1, "rgba(255,46,201,0.9)");

    ctx.beginPath();
    data.forEach((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - 4 - ((v - min) / range) * (h - 8);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = grad;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Fill below
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = "rgba(0,245,255,0.08)";
    ctx.fill();

    const valEl = $(`[data-metric="${name}"]`);
    if (valEl) valEl.textContent = `${Math.round(data[data.length - 1])}ms`;
  }

  function renderSparklines() {
    $$("[data-spark]").forEach((c) => drawSparkline(c, c.dataset.spark));
  }

  function renderCounters() {
    $("#ctr-turns").textContent = store.state.counters.turns;
    $("#ctr-commands").textContent = store.state.counters.commands;
    $("#ctr-errors").textContent = store.state.counters.errors;
    $("#ctr-logs").textContent = store.state.counters.logs;
    if (store.state.counters.latN > 0) {
      $("#ctr-avg-lat").textContent =
        Math.round(store.state.counters.latSum / store.state.counters.latN) +
        "ms";
    }
    $("#ctr-last-cmd").textContent = store.state.counters.lastCmdAt
      ? fmtRel(store.state.counters.lastCmdAt)
      : "—";
  }

  function renderUptime() {
    if (!store.state.startedAt) return;
    const sec = Math.floor((Date.now() - store.state.startedAt) / 1000);
    $("#topbar-uptime").textContent = `uptime ${fmtUptime(sec)}`;
  }

  function renderClock() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    $("#topbar-clock").textContent = `${hh}:${mm}:${ss}`;
  }

  store.on("services:changed", renderServices);
  store.on("metric", renderSparklines);
  store.on("conv:turn", renderCounters);
  store.on("log", renderCounters);
  store.on("snapshot", () => {
    renderServices();
    renderSparklines();
    renderCounters();
  });

  renderServices();
  renderSparklines();
  renderCounters();

  setInterval(() => {
    renderClock();
    renderUptime();
    renderCounters();
    renderSparklines();
  }, 1000);
  renderClock();
}
