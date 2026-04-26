// Avatar / Neural Core panel — state machine driven by pipeline_stage events.
import { $, $$ } from "../utils.js";
import * as store from "../store.js";

export function initAvatar() {
  const orb = $(".avatar-orb");
  const sub = $("#avatar-sub");
  const wave = $("#orb-waveform");
  const shock = $("#orb-shockwave");

  const STAGE_LABEL = {
    idle: "awaiting wake word",
    wake_word: "wake word detected",
    vad: "listening",
    stt: "transcribing",
    nlu: "understanding",
    logic: "executing logic",
    tts: "responding",
    output: "speaking",
    error: "error state",
  };

  function setStage(stage, data) {
    orb.dataset.state = stage;
    sub.textContent = STAGE_LABEL[stage] || stage;

    if (stage === "wake_word") triggerShockwave();
    if (stage === "stt") {
      if (data && data.transcript)
        sub.textContent = `transcribed: "${truncate(data.transcript, 32)}"`;
    }
  }

  function triggerShockwave() {
    if (!window.gsap) {
      shock.style.opacity = "1";
      shock.style.transform = "scale(0.4)";
      requestAnimationFrame(() => {
        shock.style.transition =
          "transform 700ms ease-out, opacity 700ms ease-out";
        shock.style.transform = "scale(2.2)";
        shock.style.opacity = "0";
      });
      return;
    }
    gsap.killTweensOf(shock);
    gsap.set(shock, { opacity: 1, scale: 0.4, borderWidth: 4 });
    gsap.to(shock, {
      opacity: 0,
      scale: 2.4,
      borderWidth: 1,
      duration: 0.9,
      ease: "power2.out",
    });
  }

  // Waveform — animates whenever stage is stt or vad
  const ctx = wave.getContext("2d");
  function drawWaveform() {
    const dpr = Math.min(window.devicePixelRatio, 2);
    const w = wave.clientWidth,
      h = wave.clientHeight;
    if (wave.width !== w * dpr) {
      wave.width = w * dpr;
      wave.height = h * dpr;
      ctx.scale(dpr, dpr);
    }
    ctx.clearRect(0, 0, w, h);
    const t = performance.now() / 1000;
    const stage = store.state.pipelineStage;
    const active = stage === "stt" || stage === "vad";
    if (!active) {
      requestAnimationFrame(drawWaveform);
      return;
    }
    ctx.lineWidth = 1.5;
    ctx.strokeStyle =
      stage === "stt" ? "rgba(0, 245, 255, 0.85)" : "rgba(52, 211, 153, 0.85)";
    ctx.shadowBlur = 8;
    ctx.shadowColor = ctx.strokeStyle;
    ctx.beginPath();
    const N = 80;
    for (let i = 0; i < N; i++) {
      const x = (i / (N - 1)) * w;
      const phase = i * 0.4 + t * 6;
      const amp =
        (Math.sin(phase) + Math.sin(phase * 1.3) * 0.6) * 0.4 +
        (Math.random() - 0.5) * 0.1;
      const y = h / 2 + amp * h * 0.45;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
    requestAnimationFrame(drawWaveform);
  }
  requestAnimationFrame(drawWaveform);

  store.on("pipeline:stage", ({ stage, data }) => setStage(stage, data));
  store.on("snapshot", () =>
    setStage(store.state.pipelineStage, store.state.pipelineData),
  );

  setStage(store.state.pipelineStage, store.state.pipelineData);
}

function truncate(s, n) {
  return s.length <= n ? s : s.slice(0, n - 1) + "…";
}
