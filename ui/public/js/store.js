// ============================================================================
// store.js — central in-memory state with pub/sub
// ============================================================================

const MAX_LOGS = 5000;
const MAX_CONV = 200;
const MAX_METRICS = 200;

const listeners = new Map(); // event -> Set<fn>

export const state = {
  connected: false,
  schemaVersion: null,
  startedAt: null,

  pipelineStage: "idle",
  pipelineData: {},
  pipelineHistory: [], // last 7 stages, dimming over time
  state: "idle",

  services: {
    rasa: "unknown",
    logic: "unknown",
    tts: "unknown",
    duckling: "unknown",
    ws: "down",
  },
  uptime: 0,

  logs: [], // ring buffer
  fileMap: new Map(), // filename -> count
  conv: [],
  metrics: new Map(), // metric name -> array of {value, timestamp}
  counters: {
    turns: 0,
    commands: 0,
    errors: 0,
    logs: 0,
    lastCmdAt: null,
    latSum: 0,
    latN: 0,
  },
};

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event).add(fn);
  return () => listeners.get(event).delete(fn);
}

export function emit(event, payload) {
  const set = listeners.get(event);
  if (set)
    for (const fn of set) {
      try {
        fn(payload);
      } catch (e) {
        console.error("listener error", event, e);
      }
    }
}

// --------------------------------------------------------------------------
// Mutators
// --------------------------------------------------------------------------
export function applySnapshot(snap) {
  state.schemaVersion = snap.schema_version;
  state.pipelineStage = snap.pipeline_stage || "idle";
  state.pipelineData = snap.pipeline_data || {};
  state.state = snap.state || "idle";
  state.uptime = snap.uptime_seconds || 0;
  state.startedAt = Date.now() - (snap.uptime_seconds || 0) * 1000;
  Object.assign(state.services, snap.services || {});

  state.logs = [];
  state.fileMap.clear();
  for (const log of snap.log_buffer || []) appendLog(log, /*silent*/ true);

  state.conv = (snap.conversation_buffer || []).slice(-MAX_CONV);
  state.metrics.clear();
  for (const m of snap.metric_buffer || []) appendMetric(m, /*silent*/ true);

  emit("snapshot", snap);
  emit("logs:replaced");
  emit("files:changed");
  emit("conv:replaced");
  emit("services:changed");
  emit("pipeline:stage", {
    stage: state.pipelineStage,
    data: state.pipelineData,
  });
}

export function appendLog(log, silent = false) {
  state.logs.push(log);
  if (state.logs.length > MAX_LOGS)
    state.logs.splice(0, state.logs.length - MAX_LOGS);
  const f = log.source_file || "<unknown>";
  state.fileMap.set(f, (state.fileMap.get(f) || 0) + 1);
  state.counters.logs++;
  if (log.level === "ERROR") state.counters.errors++;
  if (!silent) {
    emit("log", log);
    emit("files:changed");
  }
}

export function appendConvTurn(turn, silent = false) {
  state.conv.push(turn);
  if (state.conv.length > MAX_CONV) state.conv.shift();
  state.counters.turns++;
  if (turn.role === "user") {
    state.counters.commands++;
    state.counters.lastCmdAt = turn.timestamp;
  }
  if (!silent) emit("conv:turn", turn);
}

export function appendMetric(m, silent = false) {
  if (!state.metrics.has(m.name)) state.metrics.set(m.name, []);
  const arr = state.metrics.get(m.name);
  arr.push({ value: m.value, timestamp: m.timestamp });
  if (arr.length > MAX_METRICS) arr.shift();
  if (m.name.endsWith("_latency_ms") && typeof m.value === "number") {
    state.counters.latSum += m.value;
    state.counters.latN += 1;
  }
  if (!silent) emit("metric", m);
}

export function setPipelineStage(stage, data) {
  state.pipelineStage = stage;
  state.pipelineData = data || {};
  if (stage !== "idle") {
    state.pipelineHistory.push({ stage, ts: Date.now() });
    if (state.pipelineHistory.length > 30) state.pipelineHistory.shift();
  }
  emit("pipeline:stage", { stage, data });
}

export function setServiceStatus(svc, status) {
  state.services[svc] = status;
  emit("services:changed");
}

export function setConnected(connected, info) {
  state.connected = connected;
  state.services.ws = connected ? "up" : "down";
  emit("connection", { connected, info });
  emit("services:changed");
}
