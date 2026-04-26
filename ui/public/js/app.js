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
