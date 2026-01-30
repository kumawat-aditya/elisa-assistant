// State management
let currentState = "connecting"; // Initial state
let logCounter = 0;

// DOM elements
const coreCircle = document.getElementById("coreCircle");
const coreIcon = document.getElementById("coreIcon");
const statusText = document.getElementById("statusText");
const logsContent = document.getElementById("logsContent");
const systemStatus = document.getElementById("systemStatus");

// State configurations
const states = {
  connecting: {
    icon: "🔗",
    text: "Connecting to backend...",
    class: "connecting",
    status: "Connecting",
  },
  idle: {
    icon: "🎧",
    text: "Waiting for wake word...",
    class: "",
    status: "Standby",
  },
  boot: {
    icon: "⚡",
    text: "System booting...",
    class: "processing",
    status: "Initializing",
  },
  listening: {
    icon: "👂",
    text: "Listening for command...",
    class: "listening",
    status: "Listening",
  },
  processing_audio: {
    icon: "🎤",
    text: "Processing audio input...",
    class: "processing",
    status: "Processing Audio",
  },
  processing: {
    icon: "🧠",
    text: "Processing command...",
    class: "processing",
    status: "Processing",
  },
  speaking: {
    icon: "💬",
    text: "Speaking response...",
    class: "speaking",
    status: "Speaking",
  },
  error: {
    icon: "⚠️",
    text: "Error occurred",
    class: "error",
    status: "Error",
  },
  reconnecting: {
    icon: "🔄",
    text: "Reconnecting to backend...",
    class: "reconnecting",
    status: "Reconnecting",
  },
  connection_lost: {
    icon: "❌",
    text: "Connection lost, attempting to reconnect...",
    class: "error",
    status: "Disconnected",
  },
};

// Update UI state
function setState(newState) {
  if (states[newState]) {
    currentState = newState;
    const config = states[newState];
    coreCircle.className = `core-circle ${config.class}`;
    coreIcon.textContent = config.icon;
    statusText.textContent = config.text;
    systemStatus.textContent = config.status;
  }
}

// Add log entry
function addLog(level, message) {
  const timestamp = new Date().toLocaleTimeString();
  const logEntry = document.createElement("div");
  logEntry.className = `log-entry ${level}`;

  logEntry.innerHTML = `
         <span class="log-timestamp">${timestamp}</span>
         <span class="log-level">${level.toUpperCase()}</span>
         ${message}
     `;

  logsContent.appendChild(logEntry);
  logsContent.scrollTop = logsContent.scrollHeight;

  // Keep only last 100 logs
  while (logsContent.children.length > 100) {
    logsContent.removeChild(logsContent.firstChild);
  }
}

// WebSocket connection
let websocket = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 100;

function connectWebSocket() {
  try {
    websocket = new WebSocket("ws://localhost:8765");
    websocket.onopen = function (event) {
      setState("idle");
      addLog("success", "Connected to Elisa Assistant backend");
      reconnectAttempts = 0;
    };

    websocket.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "state_change") {
          setState(data.state);
          // if (data.module) {
          // addLog("info", `State changed by ${data.module}: ${data.state}`);
          // }
        } else if (data.type === "log") {
          // Add module name to log message if available
          const message = data.module
            ? `[${data.module}] ${data.message}`
            : data.message;
          addLog(data.level, message);
        } else if (data.type === "connection_established") {
          addLog("success", data.message);
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    websocket.onclose = function (event) {
      addLog("warning", "Connection to backend lost");
      setState("connection_lost");

      // Attempt to reconnect
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        setState("reconnecting");
        addLog(
          "info",
          `Attempting to reconnect... (${reconnectAttempts}/${maxReconnectAttempts})`
        );
        setTimeout(connectWebSocket, 2000);
      } else {
        setState("connection_lost");
        addLog(
          "error",
          "Failed to reconnect after maximum attempts. Please check server and network."
        );
      }
    };

    websocket.onerror = function (error) {
      addLog("error", "WebSocket connection error");
    };
  } catch (error) {
    console.error("Failed to create WebSocket object:", error);
    // setState("error");
    addLog("error", "Failed to establish WebSocket connection. Check console.");
  }
}

// Create floating particles
function createFloatingParticles() {
  const backgroundEffects = document.getElementById("backgroundEffects");

  setInterval(() => {
    const particle = document.createElement("div");
    particle.className = "floating-particle";
    particle.style.left = Math.random() * 100 + "%";
    particle.style.animationDuration = Math.random() * 4 + 6 + "s";
    particle.style.opacity = Math.random() * 0.5 + 0.1;
    backgroundEffects.appendChild(particle);

    setTimeout(() => {
      particle.remove();
    }, 10000);
  }, 2000);
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  addLog("success", "Elisa Assistant UI initialized");
  addLog("info", "Attempting to connect to backend...");

  createFloatingParticles();

  // Try to connect to WebSocket server
  connectWebSocket();
});

// Manual state control for testing (can be called from console)
window.elisaControl = {
  setState,
  addLog,
  states: Object.keys(states),
};
