// Conversation Membrane panel.
import { $, el, fmtTime, fmtRel, escapeHtml } from "../utils.js";
import * as store from "../store.js";

export function initConversation() {
  const list = $("#conv");
  const empty = list.querySelector(".conv__empty");
  const jump = $("#conv-jump");
  const clearBtn = $("#conv-clear");

  let userScrolledUp = false;
  list.addEventListener("scroll", () => {
    const atBottom =
      list.scrollHeight - list.scrollTop - list.clientHeight < 60;
    userScrolledUp = !atBottom;
    jump.hidden = !userScrolledUp;
  });
  jump.addEventListener("click", () => {
    list.scrollTo({ top: list.scrollHeight, behavior: "smooth" });
  });
  clearBtn.addEventListener("click", () => {
    list.innerHTML = "";
    list.appendChild(
      el(
        "div",
        { class: "conv__empty" },
        el(
          "span",
          { class: "muted" },
          "view cleared. new turns will appear here.",
        ),
      ),
    );
  });

  function render(turn) {
    if (empty && empty.parentNode) empty.remove();
    const meta = turn.metadata || {};

    const head = el(
      "div",
      { class: "conv-turn__head" },
      el(
        "span",
        { class: "conv-turn__role" },
        turn.role === "user" ? "user" : "elisa",
      ),
      meta.intent ? el("span", {}, "·") : null,
      meta.intent ? el("span", {}, `intent: ${meta.intent}`) : null,
      el(
        "span",
        { class: "conv-turn__time", title: turn.timestamp },
        fmtTime(turn.timestamp),
      ),
    );

    const pills = [];
    if (typeof meta.confidence === "number") {
      const kind =
        meta.confidence > 0.85
          ? "conf-good"
          : meta.confidence > 0.6
            ? "conf-mid"
            : "conf-low";
      pills.push(
        el(
          "span",
          { class: "conv-pill", dataset: { kind } },
          `${(meta.confidence * 100).toFixed(0)}%`,
        ),
      );
    }
    if (typeof meta.latency_ms === "number")
      pills.push(el("span", { class: "conv-pill" }, `${meta.latency_ms}ms`));
    if (meta.action)
      pills.push(el("span", { class: "conv-pill" }, meta.action));
    if (Array.isArray(meta.entities)) {
      for (const e of meta.entities)
        pills.push(
          el("span", { class: "conv-pill" }, `${e.entity}=${e.value}`),
        );
    }
    if (meta.phase) pills.push(el("span", { class: "conv-pill" }, meta.phase));

    const body = el("div", { class: "conv-turn__body" }, turn.text);
    const metaRow = pills.length
      ? el("div", { class: "conv-turn__meta" }, ...pills)
      : null;

    const node = el(
      "div",
      { class: `conv-turn conv-turn--${turn.role}` },
      head,
      body,
      metaRow,
    );
    list.appendChild(node);
    if (!userScrolledUp) list.scrollTop = list.scrollHeight;
  }

  function renderAll() {
    list.innerHTML = "";
    if (store.state.conv.length === 0) {
      list.appendChild(
        el(
          "div",
          { class: "conv__empty" },
          el(
            "span",
            { class: "muted" },
            "no conversation yet — say the wake word.",
          ),
        ),
      );
      return;
    }
    for (const t of store.state.conv) render(t);
  }

  store.on("conv:turn", render);
  store.on("conv:replaced", renderAll);
  renderAll();
}
