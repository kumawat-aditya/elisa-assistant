// ============================================================================
// websocket.js — auto-reconnecting client + message router
// ============================================================================

import * as store from "./store.js";

const WS_URL_DEFAULT = `ws://${location.hostname || "localhost"}:8765`;

export class WSClient {
  constructor(url = WS_URL_DEFAULT) {
    this.url = url;
    this.ws = null;
    this.attempt = 0;
    this.shouldReconnect = true;
    this.lastPongAt = 0;
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      this._scheduleReconnect();
      return;
    }
    this.ws.addEventListener("open", () => this._onOpen());
    this.ws.addEventListener("close", () => this._onClose());
    this.ws.addEventListener("error", () => {
      /* close will fire */
    });
    this.ws.addEventListener("message", (e) => this._onMessage(e));
  }

  send(obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(obj));
      } catch (_) {}
    }
  }

  close() {
    this.shouldReconnect = false;
    try {
      this.ws && this.ws.close();
    } catch (_) {}
  }

  _onOpen() {
    this.attempt = 0;
    store.setConnected(true, { url: this.url });
  }

  _onClose() {
    store.setConnected(false, { url: this.url });
    if (this.shouldReconnect) this._scheduleReconnect();
  }

  _scheduleReconnect() {
    this.attempt++;
    const delay = Math.min(8000, 400 * Math.pow(1.6, this.attempt));
    setTimeout(() => this.connect(), delay);
  }

  _onMessage(ev) {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch (_) {
      return;
    }
    routeMessage(msg, this);
  }
}

function routeMessage(msg, client) {
  switch (msg.type) {
    case "connection_established":
      // initial handshake — snapshot follows
      break;
    case "snapshot":
      store.applySnapshot(msg);
      break;
    case "log":
      store.appendLog(msg);
      break;
    case "conversation_turn":
      store.appendConvTurn(msg);
      break;
    case "metric":
      store.appendMetric(msg);
      break;
    case "pipeline_stage":
      store.setPipelineStage(msg.stage, msg.data);
      break;
    case "state_change":
      store.state.state = msg.state;
      store.emit("state:change", msg);
      break;
    case "service_status":
      store.setServiceStatus(msg.service, msg.status);
      break;
    case "error":
      store.emit("server:error", msg);
      break;
    case "ping":
      client.send({ type: "pong" });
      break;
    case "pong":
      client.lastPongAt = Date.now();
      break;
    default:
      // Pass-through for forward compatibility
      store.emit("custom", msg);
  }
}

export function startClient() {
  const c = new WSClient();
  c.connect();
  // Periodic client-side ping for liveness
  setInterval(() => c.send({ type: "ping" }), 20_000);
  return c;
}
