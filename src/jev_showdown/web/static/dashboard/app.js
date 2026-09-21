import { appendFrame, applyConnectionState, applyDashboardState, createClientState, selectedDecision } from "./state.js";
import { announce, query, queryAll, renderDashboard } from "./render.js";
import { installInspector } from "./inspector.js";

let clientState = createClientState();
let socket = null;
let reconnectTimer = null;
let rendererReady = false;
let selected = null;
let inspector = null;

function update() {
  renderDashboard(clientState, selected);
  inspector?.refresh();
}

function rendererNodes() {
  return [query("#showdown-frame"), query("#showdown-log"), query("#showdown-status")];
}

async function ensureRenderer(battleTag) {
  if (!window.JevShowdownRenderer) return;
  if (rendererReady) return;
  window.JevShowdownRenderer.reset(battleTag || "jev-showdown");
  try {
    await window.JevShowdownRenderer.mount(...rendererNodes());
    rendererReady = true;
  } catch (error) {
    query("#showdown-status").textContent = "Official renderer unavailable · telemetry fallback active";
  }
}

function feedFrame(message) {
  clientState = appendFrame(clientState, message);
  ensureRenderer(message.battle_tag).then(() => window.JevShowdownRenderer?.feed(message.lines || []));
}

function resetRenderer(battleTag) {
  rendererReady = false;
  if (window.JevShowdownRenderer) window.JevShowdownRenderer.reset(battleTag || "jev-showdown");
}

function handleMessage(message) {
  if (message.type === "BATTLE_REPLAY") {
    resetRenderer(message.battle_tag);
    ensureRenderer(message.battle_tag).then(() => (message.frames || []).forEach((lines) => window.JevShowdownRenderer?.feed(lines)));
    return;
  }
  if (message.type === "BATTLE_FRAME") { feedFrame(message); return; }
  if (message.type === "BATTLE_END") { window.JevShowdownRenderer?.end(); return; }
  if (message.type === "DASHBOARD_STATE") {
    const previous = clientState.dashboard;
    clientState = applyDashboardState(clientState, message);
    if (message.event_type === "BATTLE_START") {
      selected = null;
      resetRenderer(message.state.battle.battle_tag);
    }
    if (message.event_type === "BATTLE_END") window.JevShowdownRenderer?.end();
    const current = message.state.current_turn;
    const previousCurrent = previous?.current_turn;
    if (current && (!previousCurrent || previousCurrent.turn !== current.turn || previousCurrent.battle_tag !== current.battle_tag)) {
      announce(`Turn ${current.turn}: ${current.lifecycle_state}`);
    }
    update();
  }
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${window.location.host}/ws`;
  socket = new WebSocket(url);
  socket.addEventListener("open", () => {
    clientState = applyConnectionState(clientState, true);
    query("#connection-state").classList.remove("is-error");
    announce("Dashboard connected");
    update();
  });
  socket.addEventListener("message", (event) => {
    try { handleMessage(JSON.parse(event.data)); } catch (error) { console.warn("Dashboard message ignored", error); }
  });
  socket.addEventListener("close", () => {
    clientState = applyConnectionState(clientState, false, "Disconnected");
    query("[data-connection-label]").textContent = "RECONNECTING";
    update();
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 1400);
  });
  socket.addEventListener("error", () => {
    clientState = applyConnectionState(clientState, false, "Connection error");
    update();
  });
}

function startBattle() {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ action: "START_BATTLE" }));
  announce("Autonomous battle requested");
}

function openInspector(tab = "overview") {
  const drawer = query("#inspection-drawer");
  drawer.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
  query("#drawer-scrim").classList.add("is-visible");
  query("#open-inspector").setAttribute("aria-expanded", "true");
  window.dispatchEvent(new CustomEvent("jev:inspect", { detail: { tab, decision: selected || selectedDecision(clientState.dashboard) } }));
}

function closeInspector() {
  const drawer = query("#inspection-drawer");
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
  query("#drawer-scrim").classList.remove("is-visible");
  query("#open-inspector").setAttribute("aria-expanded", "false");
  query("#open-inspector").focus();
}

function bind() {
  query("#start-battle").addEventListener("click", startBattle);
  query("#open-inspector").addEventListener("click", () => openInspector());
  query("#close-inspector").addEventListener("click", closeInspector);
  query("#drawer-scrim").addEventListener("click", closeInspector);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && query("#inspection-drawer").classList.contains("is-open")) closeInspector(); });
  document.addEventListener("click", (event) => {
    const historyCard = event.target.closest?.(".history-card");
    if (historyCard && clientState.dashboard) {
      selected = (clientState.dashboard.history || []).find((item) => item.battle_tag === historyCard.dataset.battleTag && String(item.turn) === historyCard.dataset.turn) || null;
      update();
      openInspector("overview");
    }
    const tabTrigger = event.target.closest?.("[data-inspect-tab]");
    if (tabTrigger) openInspector(tabTrigger.dataset.inspectTab);
    const filter = event.target.closest?.("[data-history-limit]");
    if (filter) { queryAll(".history-filter").forEach((button) => button.classList.toggle("is-active", button === filter)); update(); }
  });
}

window.JevShowdownDashboard = {
  getState: () => clientState,
  openInspector,
  closeInspector,
};

inspector = installInspector({
  getState: () => clientState,
  getSelected: () => selected || selectedDecision(clientState.dashboard),
});
bind();
update();
connect();
