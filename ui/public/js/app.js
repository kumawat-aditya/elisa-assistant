// ============================================================================
// app.js — entry point: bootstrap cosmos, panels, websocket
// ============================================================================
import { $ } from "./utils.js";
import * as store from "./store.js";
import { startClient } from "./websocket.js";
import { startCosmos } from "./cosmos.js";
import { initAvatar } from "./panels/avatar.js";
import { initPipeline } from "./panels/pipeline.js";
import { initConversation } from "./panels/conversation.js";
import { initLogs } from "./panels/logs.js";
import { initVitals } from "./panels/vitals.js";

function bootstrap() {
  // Cosmos (best-effort; depends on THREE having loaded via defer)
  try {
    startCosmos();
  } catch (e) {
    console.warn("cosmos failed:", e);
  }

  initVitals();
  initAvatar();
  initPipeline();
  initConversation();
  initLogs();

  wireConnectionBanner();
  wireStatePill();
  wireMobileNav();

  // Start websocket client
  startClient();

  // Entry sequence — fade in main grid
  document.body.classList.add("entered");
}

function wireConnectionBanner() {
  const banner = $("#conn-banner");
  const text = banner.querySelector(".conn-text");
  const meta = $("#conn-meta");

  store.on("connection", ({ connected, info }) => {
    banner.classList.toggle("conn-banner--up", connected);
    banner.classList.toggle("conn-banner--down", !connected);
    if (connected) {
      text.textContent = "live · streaming from elisa core";
      meta.textContent = info?.url || "";
      banner.classList.add("conn-banner--fade");
      setTimeout(() => {
        banner.hidden = true;
      }, 1500);
    } else {
      banner.hidden = false;
      banner.classList.remove("conn-banner--fade");
      text.textContent = "reconnecting to elisa core …";
      meta.textContent = info?.url || "";
    }
  });

  store.on("server:error", (msg) => {
    showToast(msg.message || "server error", "error");
  });
}

function wireStatePill() {
  const pill = $("#state-pill");
  const label = pill.querySelector(".state-pill__label");
  const update = () => {
    pill.dataset.state = store.state.pipelineStage;
    label.textContent = store.state.pipelineStage;
  };
  store.on("pipeline:stage", update);
  store.on("snapshot", update);
  update();
}

/**
 * Mobile / Tablet bottom nav — shows/hides panels via .mob-active class.
 * On desktop the nav is CSS display:none so this handler is effectively a no-op.
 */
function wireMobileNav() {
  const nav = document.getElementById("mob-nav");
  if (!nav) return;

  // Map data-panel → grid cell element
  const PANEL_MAP = {
    avatar: document.getElementById("panel-avatar"),
    pipeline: document.getElementById("panel-pipeline"),
    conv: document.getElementById("panel-conv"),
    vitals: document.getElementById("panel-vitals"),
    logs: document.getElementById("panel-logs"),
  };

  function activatePanel(panelKey) {
    // Update panel visibility
    for (const [key, el] of Object.entries(PANEL_MAP)) {
      if (el) el.classList.toggle("mob-active", key === panelKey);
    }
    // Update nav button states
    nav.querySelectorAll(".mob-nav__btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.panel === panelKey);
    });
  }

  nav.addEventListener("click", (e) => {
    const btn = e.target.closest(".mob-nav__btn");
    if (!btn) return;
    activatePanel(btn.dataset.panel);
  });

  // Default: show avatar panel on load
  activatePanel("avatar");
}

function showToast(text, kind = "info") {
  const host = $("#toasts");
  if (!host) return;
  const t = document.createElement("div");
  t.className = `toast toast--${kind}`;
  t.textContent = text;
  host.appendChild(t);
  setTimeout(() => t.classList.add("toast--out"), 3500);
  setTimeout(() => t.remove(), 4200);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
} else {
  bootstrap();
}
