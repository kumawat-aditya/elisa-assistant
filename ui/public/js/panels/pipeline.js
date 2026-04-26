// Pipeline panel — animated stage flow with SVG connectors and tooltips.
import { $, $$ } from "../utils.js";
import * as store from "../store.js";

const ORDER = ["wake_word", "vad", "stt", "nlu", "logic", "tts", "output"];

export function initPipeline() {
  const root = $("#panel-pipeline");
  const nodes = $$(".pl-node", root);
  const svg = $("#pipeline-svg");
  const sub = $("#pipeline-sub");

  const lastData = {}; // stage -> data
  const reachedAt = {}; // stage -> ts

  function setActive(stage, data) {
    sub.textContent = stage;

    if (data) lastData[stage] = data;
    if (stage !== "idle" && ORDER.includes(stage))
      reachedAt[stage] = Date.now();

    // Reset on idle
    if (stage === "idle") {
      // After 1.4s of idle, fade everything down
      setTimeout(() => {
        if (store.state.pipelineStage === "idle")
          nodes.forEach((n) =>
            n.classList.remove("pl-node--active", "pl-node--done"),
          );
      }, 1400);
      return;
    }

    nodes.forEach((n) => {
      const s = n.dataset.stage;
      n.classList.remove("pl-node--active", "pl-node--done");
      const idxCurrent = ORDER.indexOf(stage);
      const idxThis = ORDER.indexOf(s);
      if (idxThis < idxCurrent) n.classList.add("pl-node--done");
      else if (idxThis === idxCurrent) n.classList.add("pl-node--active");
    });

    drawConnectors(stage);
    updateTips();
  }

  function drawConnectors(activeStage) {
    const { width, height } = svg.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.innerHTML = "";

    const points = nodes.map((n) => {
      const r = n.querySelector(".pl-node__core").getBoundingClientRect();
      const sR = svg.getBoundingClientRect();
      return {
        x: r.left - sR.left + r.width / 2,
        y: r.top - sR.top + r.height / 2,
      };
    });

    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i],
        b = points[i + 1];
      const mx = (a.x + b.x) / 2;
      const path = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path",
      );
      path.setAttribute(
        "d",
        `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`,
      );
      path.setAttribute("class", "pl-connector");
      const idxA = ORDER.indexOf(nodes[i].dataset.stage);
      const idxAct = ORDER.indexOf(activeStage);
      if (idxA < idxAct) path.classList.add("pl-connector--active");
      svg.appendChild(path);
    }
  }

  function updateTips() {
    nodes.forEach((n) => {
      const s = n.dataset.stage;
      const tip = n.querySelector(".pl-node__tip");
      const d = lastData[s];
      if (!d || Object.keys(d).length === 0) {
        tip.textContent = "";
        tip.dataset.empty = "true";
        return;
      }
      tip.textContent = formatTip(s, d);
      tip.dataset.empty = "false";
    });
  }

  function formatTip(stage, d) {
    const lines = [];
    for (const [k, v] of Object.entries(d)) {
      const val =
        typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(2)) : v;
      lines.push(`${k}: ${truncate(String(val), 60)}`);
    }
    return lines.join("\n");
  }

  function truncate(s, n) {
    return s.length <= n ? s : s.slice(0, n - 1) + "…";
  }

  store.on("pipeline:stage", ({ stage, data }) => setActive(stage, data));
  store.on("snapshot", () =>
    setActive(store.state.pipelineStage, store.state.pipelineData),
  );

  // Re-render connectors on resize
  const ro = new ResizeObserver(() =>
    drawConnectors(store.state.pipelineStage),
  );
  ro.observe(root);

  setActive(store.state.pipelineStage, store.state.pipelineData);
}
