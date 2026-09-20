/*
 * JEV battle dashboard client.
 *
 * The official Showdown renderer owns the game scene. This file owns only
 * the presentation of harness input, actual Jev output, validation, action
 * submission, and protocol-observed results.
 */
"use strict";

const state = {
  ws: null,
  connected: false,
  battleActive: false,
  gamePhase: "IDLE",
  showdownBattleTag: null,
  showdownMountPromise: null,
  showdownUnavailable: false,
  inspectOpen: false,
  inspectTab: "state",
  inspect: {
    state: null,
    question: null,
    request: null,
    response: null,
    validation: null,
    frames: [],
  },
  currentTurn: null,
  currentDecision: null,
  awaitingObservedResult: false,
  reconnectTimer: null,
};

const getEl = (id) => document.getElementById(id);

function setText(id, value) {
  const element = getEl(id);
  if (element) element.textContent = value == null ? "" : String(value);
}

function clearEl(element) {
  if (!element) return;
  while (element.firstChild) element.removeChild(element.firstChild);
}

function makeEl(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = text;
  return element;
}

function fmtPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  return Math.round(Number(value) * 100) + "%";
}

function fmtLatency(value) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  return String(Math.round(Number(value)));
}

function humanize(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();
}

function upper(value, fallback = "--") {
  const text = humanize(value);
  return text ? text.toUpperCase() : fallback;
}

function formatAction(action) {
  if (!action) return "ACTION";
  return upper(action.label || action.id || action.kind || "ACTION");
}

function findAction(snapshot, id) {
  const legal = snapshot && Array.isArray(snapshot.legal_actions)
    ? snapshot.legal_actions
    : [];
  return legal.find((action) => action && action.id === id) || null;
}

function setStatusChip(id, text, mode) {
  const element = getEl(id);
  if (!element) return;
  element.textContent = text;
  element.classList.remove("online", "live", "warn", "error");
  if (mode) element.classList.add(mode);
}

function setGamePhase(phase) {
  state.gamePhase = phase;
  setText("game-state", phase);
}

function setStartButton(label, disabled) {
  const button = getEl("start-btn");
  if (!button) return;
  button.textContent = label;
  button.disabled = Boolean(disabled);
}

function setTraceStep(id, value, mode) {
  const element = getEl(id);
  if (!element) return;
  element.classList.remove("trace-active", "trace-success", "trace-pending", "trace-error");
  if (mode) element.classList.add(mode);
  const strong = element.querySelector("strong");
  if (strong) strong.textContent = value;
}

function setJevLoading(visible) {
  const loader = getEl("jev-loader");
  if (loader) loader.hidden = !visible;
}

function connectSocket() {
  if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  try {
    state.ws = new WebSocket(protocol + "://" + window.location.host + "/ws");
  } catch (error) {
    setStatusChip("backend-status", "BACKEND OFFLINE", "error");
    scheduleReconnect();
    return;
  }

  setStatusChip("backend-status", "BACKEND CONNECTING", "warn");
  state.ws.onopen = () => {
    state.connected = true;
    setStatusChip("backend-status", "BACKEND ONLINE", "online");
    if (!state.battleActive) {
      setStartButton("START JEV BATTLE", false);
      setGamePhase("IDLE");
    }
  };
  state.ws.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (error) {
      console.warn("[jev-dashboard] ignored non-JSON message", event.data);
      return;
    }
    dispatchMessage(data);
  };
  state.ws.onclose = () => {
    state.connected = false;
    setStatusChip("backend-status", "BACKEND OFFLINE", "error");
    if (!state.battleActive) {
      setStartButton("RECONNECTING...", true);
      setGamePhase("OFFLINE");
    } else {
      setGamePhase("CONNECTION LOST");
    }
    scheduleReconnect();
  };
  state.ws.onerror = () => {
    setStatusChip("backend-status", "BACKEND ERROR", "error");
  };
}

function scheduleReconnect() {
  if (state.reconnectTimer) return;
  state.reconnectTimer = window.setTimeout(() => {
    state.reconnectTimer = null;
    if (!state.connected) connectSocket();
  }, 1500);
}

function sendAction(action) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ action }));
    return true;
  }
  return false;
}

function dispatchMessage(data) {
  const type = data.type || data.event;
  if (type === "STATUS_UPDATE") handleStatusUpdate(data);
  else if (type === "BATTLE_START") handleShowdownBattleStart(data);
  else if (type === "BATTLE_FRAME") handleShowdownFrame(data);
  else if (type === "BATTLE_REPLAY") handleShowdownReplay(data);
  else if (type === "TURN_DECISION") handleTurnDecision(data);
  else if (type === "BATTLE_END") handleBattleEnd(data);
  else if (data.turn != null && (data.jev || data.jev_response)) handleTurnDecision(data);
}

function handleStatusUpdate(data) {
  const status = upper(data.status || data.message || "STATUS");
  const rawStatus = String(data.status || data.message || "").toUpperCase();
  if (data.error) {
    state.battleActive = false;
    setJevLoading(false);
    setStartButton("RETRY BATTLE", false);
    const button = getEl("start-btn");
    if (button) button.classList.add("btn-error");
    setGamePhase("ERROR");
    setStatusChip("showdown-connection-status", "SHOWDOWN ERROR", "error");
    setStatusChip("jev-status", "JEV UNAVAILABLE", "error");
    return;
  }

  const button = getEl("start-btn");
  if (button) button.classList.remove("btn-error");
  const busy = data.busy === undefined ? true : Boolean(data.busy);
  if (busy) {
    state.battleActive = true;
    setStartButton(rawStatus === "JEV PLAYING" ? "JEV PLAYING" : "CONNECTING...", true);
    if (rawStatus === "JEV PLAYING") {
      setGamePhase("JEV PLAYING");
      setStatusChip("jev-status", "JEV INFERENCE", "live");
      setJevLoading(true);
    } else {
      setGamePhase(status);
      setStatusChip("showdown-connection-status", status, "warn");
    }
  } else if (!state.battleActive) {
    setJevLoading(false);
    setStartButton("START JEV BATTLE", false);
    setGamePhase(rawStatus === "READY" ? "IDLE" : status);
    if (rawStatus === "READY") {
      setStatusChip("showdown-connection-status", "SHOWDOWN READY", "online");
      setStatusChip("jev-status", "JEV READY", "online");
    }
  }
}

function onStartBattleClick() {
  if (state.battleActive) return;
  const button = getEl("start-btn");
  if (button) button.classList.remove("btn-error");
  setStartButton("CONNECTING...", true);
  setGamePhase("CONNECTING");
  if (!sendAction("START_BATTLE")) {
    setStartButton("OFFLINE - RETRY", false);
    setStatusChip("backend-status", "BACKEND OFFLINE", "error");
    scheduleReconnect();
  }
}

function renderJevInput(snapshot, criteria, chosenId) {
  const summary = getEl("input-summary");
  const facts = getEl("input-facts");
  const actions = getEl("legal-actions");
  const count = getEl("legal-action-count");
  clearEl(summary);
  clearEl(facts);
  clearEl(actions);

  const legal = snapshot && Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions : [];
  const self = snapshot && snapshot.self && snapshot.self.active_pokemon;
  const opponent = snapshot && snapshot.opponent && snapshot.opponent.active_pokemon;
  const turn = snapshot && snapshot.turn != null ? snapshot.turn : state.currentTurn;
  const summaryLine = makeEl("div", "summary-line");
  summaryLine.appendChild(makeEl("span", "turn", "TURN " + (turn != null ? turn : "--")));
  summaryLine.appendChild(document.createTextNode("  •  "));
  summaryLine.appendChild(makeEl("span", "active", upper(self && self.species, "ACTIVE UNKNOWN")));
  summaryLine.appendChild(document.createTextNode("  VS  "));
  summaryLine.appendChild(makeEl("span", "opponent", upper(opponent && opponent.species, "OPPONENT UNKNOWN")));
  summary.appendChild(summaryLine);

  const fields = snapshot && Array.isArray(snapshot.fields) ? snapshot.fields : [];
  const weather = snapshot && snapshot.weather ? String(snapshot.weather) : "";
  if (fields.length || weather) {
    const context = makeEl("div", "context-line");
    const parts = [];
    if (weather) parts.push("WEATHER: " + upper(weather));
    if (fields.length) parts.push("FIELD: " + fields.map(upper).join(", "));
    context.textContent = parts.join("  •  ");
    summary.appendChild(context);
  }

  const selected = findAction(snapshot, chosenId);
  renderFactChips(selected && selected.facts ? selected.facts : {}, facts);
  if (count) count.textContent = String(legal.length);

  const ordered = legal.slice();
  ordered.sort((a, b) => (a.id === chosenId ? -1 : b.id === chosenId ? 1 : 0));
  ordered.slice(0, 4).forEach((action) => {
    const row = makeEl("div", "legal-action" + (action.id === chosenId ? " selected" : ""));
    row.appendChild(makeEl("span", "action-marker", action.id === chosenId ? "*" : ">"));
    row.appendChild(makeEl("span", "action-name", formatAction(action)));
    row.appendChild(makeEl("span", "action-kind", upper(action.kind, "ACTION")));
    actions.appendChild(row);
  });
  if (!legal.length) actions.appendChild(makeEl("span", "empty-note", "NO LEGAL ACTIONS YET"));

  // Criteria remain available through Technical Inspection; the visible rail
  // shows only the decision-relevant state and calculated candidate facts.
  void criteria;
}

function renderFactChips(factObject, container) {
  const facts = factObject && typeof factObject === "object" ? factObject : {};
  const entries = Object.entries(facts).filter(([, value]) => value != null && value !== "");
  entries.slice(0, 6).forEach(([key, value]) => {
    let display = value;
    if (Array.isArray(value)) display = value.join("- ");
    else if (typeof value === "boolean") display = value ? "YES" : "NO";
    else if (typeof value === "object") return;
    const chip = makeEl("span", "fact-chip", upper(key) + ": " + upper(display, String(display)));
    container.appendChild(chip);
  });
  if (!container.childNodes.length) container.appendChild(makeEl("span", "empty-note", "NO CALCULATED FACTS"));
}

function renderJevOutput(jev, validation, chosenId, snapshot) {
  const response = jev || {};
  const isFallback = Boolean(validation && validation.is_fallback);
  setJevLoading(false);
  setText("decision-source", response.model ? String(response.model) : (isFallback ? "ADAPTER FALLBACK" : "MODEL --"));
  setText("decision-choice", chosenId ? upper(chosenId) : (isFallback ? "FALLBACK ACTION" : "AWAITING DECISION"));
  setText("decision-confidence", fmtPct(response.confidence));
  renderProbabilities(response.probabilities || {}, snapshot, chosenId);

  const meta = ["LATENCY " + fmtLatency(response.latency_ms) + " MS"];
  if (response.input_tokens != null) meta.push("IN " + response.input_tokens);
  if (response.output_tokens != null) meta.push("OUT " + response.output_tokens);
  if (response.cost != null) meta.push("COST " + response.cost);
  setText("decision-meta", meta.join(" • "));

  const banner = getEl("fallback-banner");
  if (banner) {
    if (isFallback) {
      const reason = validation.fallback_reason ? " • " + validation.fallback_reason : "";
      banner.textContent = "FALLBACK USED" + reason + " • FALLBACK ACTION: " + upper(chosenId, "NONE");
      banner.hidden = false;
    } else {
      banner.hidden = true;
      banner.textContent = "";
    }
  }
  if (isFallback) setStatusChip("jev-status", "JEV FALLBACK", "warn");
  else if (response.model) setStatusChip("jev-status", "JEV ONLINE", "online");
}

function renderProbabilities(probabilities, snapshot, chosenId) {
  const container = getEl("decision-probabilities");
  clearEl(container);
  const entries = probabilities && typeof probabilities === "object"
    ? Object.entries(probabilities)
    : [];
  if (!entries.length) {
    container.appendChild(makeEl("span", "empty-note", "NO PROBABILITY DISTRIBUTION"));
    return;
  }
  entries.sort((a, b) => Number(b[1]) - Number(a[1])).slice(0, 6).forEach(([id, value]) => {
    const probability = Number(value);
    const pct = Number.isFinite(probability) ? Math.max(0, Math.min(100, Math.round(probability * 100))) : 0;
    const row = makeEl("div", "probability-row" + (id === chosenId ? " selected" : ""));
    row.appendChild(makeEl("span", "probability-label", formatAction(findAction(snapshot, id)) || upper(id)));
    const track = makeEl("div", "probability-track");
    const fill = makeEl("div", "probability-fill");
    fill.style.width = pct + "%";
    track.appendChild(fill);
    row.appendChild(track);
    row.appendChild(makeEl("span", "probability-value", pct + "%"));
    container.appendChild(row);
  });
}

function renderActionTrace(chosenId, snapshot, validation, submittedOrder) {
  const selected = findAction(snapshot, chosenId);
  const label = selected ? formatAction(selected) : upper(chosenId, "ACTION");
  const fallback = Boolean(validation && validation.is_fallback);
  setTraceStep("validate-step", chosenId
    ? (fallback ? "FALLBACK VALIDATED" : "LEGAL ACTION")
    : "WAITING FOR DECISION", fallback ? "trace-pending" : (chosenId ? "trace-success" : "trace-active"));

  const submitted = submittedOrder && submittedOrder.message;
  setTraceStep("act-step", submitted ? "SUBMITTED " + upper(submitted) : "ORDER READY", submitted ? "trace-success" : "trace-pending");
  setTraceStep("result-step", "AWAITING SHOWDOWN", "trace-pending");
  void label;
}

function renderObservedResult(message, mode = "trace-success") {
  setTraceStep("result-step", message || "RESULT OBSERVED FROM SHOWDOWN", mode);
  state.awaitingObservedResult = false;
}

function handleTurnDecision(data) {
  state.battleActive = true;
  state.currentTurn = data.turn != null
    ? data.turn
    : (data.snapshot && data.snapshot.turn != null ? data.snapshot.turn : state.currentTurn);
  const snapshot = data.snapshot || data.state || null;
  const request = data.jev_request || {};
  const question = data.question || (request.questions && request.questions.action) || {};
  const criteria = data.criteria || question.criteria || {};
  const jev = data.jev_response || data.jev || {};
  const validation = data.validation || {
    chosen_id: data.chosen_id || jev.choice || null,
    is_fallback: Boolean(data.is_fallback),
    fallback_reason: data.fallback_reason || null,
  };
  const chosenId = validation.chosen_id || jev.choice || data.chosen_id || null;
  const submittedOrder = data.submitted_order || {};

  state.currentDecision = { chosenId, turn: state.currentTurn };
  state.awaitingObservedResult = true;
  state.inspect.state = snapshot;
  state.inspect.question = question;
  state.inspect.request = request;
  state.inspect.response = data.jev_response || jev;
  state.inspect.validation = validation;

  setGamePhase("JEV PLAYING");
  setStartButton("JEV PLAYING", true);
  setStatusChip("showdown-connection-status", "SHOWDOWN LIVE", "live");
  renderJevInput(snapshot, criteria, chosenId);
  renderJevOutput(jev, validation, chosenId, snapshot);
  renderActionTrace(chosenId, snapshot, validation, submittedOrder);
  renderInspector();
}

function protocolSummary(lines) {
  const relevant = Array.isArray(lines) ? lines.slice().reverse() : [];
  for (const line of relevant) {
    const parts = String(line).split("|");
    const type = parts[1];
    if (type === "move") return "MOVE OBSERVED: " + upper(parts[3] || parts[2], "MOVE");
    if (type === "-damage") return "DAMAGE OBSERVED: " + upper(parts[2] || "TARGET");
    if (type === "-status") return "STATUS OBSERVED: " + upper(parts[3] || parts[2], "STATUS");
    if (type === "faint") return "FAINT OBSERVED: " + upper(parts[2], "POKEMON");
    if (type === "turn") return "TURN " + (parts[2] || "--") + " RESOLVED";
    if (type === "win") return "WIN OBSERVED: " + upper(parts[2], "WINNER");
    if (type === "tie") return "BATTLE TIE OBSERVED";
  }
  return "";
}

function hasResolvedProtocolEvent(lines) {
  return Array.isArray(lines) && lines.some((line) => /\|(move|-damage|-status|faint|turn|win|tie)\|/.test(String(line)));
}

function handleShowdownFrame(data) {
  const tag = data.battle_tag || "jev-showdown";
  if (state.showdownBattleTag !== tag) handleShowdownBattleStart({ battle_tag: tag });
  const lines = Array.isArray(data.lines) ? data.lines : [];
  const summary = protocolSummary(lines);
  if (summary) {
    setText("showdown-caption", summary);
    if (state.awaitingObservedResult && hasResolvedProtocolEvent(lines)) renderObservedResult(summary);
  }
  state.inspect.frames.push({ battle_tag: tag, lines: lines.slice() });
  if (state.inspect.frames.length > 40) state.inspect.frames.shift();
  renderInspector();
  if (window.JevShowdownRenderer) {
    window.JevShowdownRenderer.feed(lines);
    mountShowdownRenderer().catch(() => {});
  }
}

function handleShowdownReplay(data) {
  handleShowdownBattleStart({ battle_tag: data.battle_tag });
  (Array.isArray(data.frames) ? data.frames : []).forEach((lines) => {
    handleShowdownFrame({ battle_tag: data.battle_tag, lines });
  });
}

function showShowdownScene() {
  const arena = getEl("showdown-arena");
  const fallback = getEl("arena-fallback");
  if (arena) arena.hidden = false;
  if (fallback) fallback.hidden = true;
}

function showArenaFallback(message) {
  const arena = getEl("showdown-arena");
  const fallback = getEl("arena-fallback");
  if (arena) arena.hidden = true;
  if (fallback) fallback.hidden = false;
  if (message) setText("fallback-arena-copy", message);
}

function mountShowdownRenderer() {
  if (state.showdownUnavailable || !window.JevShowdownRenderer) {
    return Promise.reject(new Error("Showdown renderer adapter is unavailable"));
  }
  if (state.showdownMountPromise) return state.showdownMountPromise;
  state.showdownMountPromise = window.JevShowdownRenderer.mount(
    getEl("showdown-frame"),
    getEl("showdown-log"),
    getEl("showdown-status"),
  ).then(() => {
    showShowdownScene();
    return true;
  }).catch((error) => {
    state.showdownUnavailable = true;
    showArenaFallback("OFFICIAL SHOWDOWN RENDERER UNAVAILABLE - TELEMETRY FALLBACK ACTIVE");
    if (window.JevShowdownRenderer) {
      window.JevShowdownRenderer.setUnavailable("OFFICIAL SHOWDOWN RENDERER UNAVAILABLE - TELEMETRY FALLBACK ACTIVE");
    }
    return Promise.reject(error);
  });
  return state.showdownMountPromise;
}

function handleShowdownBattleStart(data) {
  state.showdownBattleTag = data.battle_tag || "jev-showdown";
  state.showdownUnavailable = false;
  state.showdownMountPromise = null;
  state.inspect.frames = [];
  setStatusChip("showdown-connection-status", "SHOWDOWN STARTING", "live");
  if (window.JevShowdownRenderer) window.JevShowdownRenderer.reset(state.showdownBattleTag);
  showArenaFallback("LOADING OFFICIAL SHOWDOWN SCENE...");
  mountShowdownRenderer().catch(() => {});
}

function handleBattleEnd(data) {
  state.battleActive = false;
  state.awaitingObservedResult = false;
  setJevLoading(false);
  setStartButton("START JEV BATTLE", false);
  setGamePhase("BATTLE COMPLETE");
  setStatusChip("showdown-connection-status", "SHOWDOWN BATTLE ENDED", "online");
  setStatusChip("jev-status", "JEV READY", "online");
  const outcome = data.won === true ? "VICTORY" : data.won === false ? "DEFEAT" : "BATTLE OVER";
  const turns = data.total_turns != null ? " AFTER " + data.total_turns + " TURNS" : "";
  renderObservedResult(outcome + turns + " - RESULT OBSERVED FROM SHOWDOWN");
  if (window.JevShowdownRenderer && state.showdownMountPromise && !state.showdownUnavailable) {
    window.JevShowdownRenderer.end();
  }
  const arena = getEl("showdown-arena");
  if (arena && state.showdownMountPromise && !state.showdownUnavailable) arena.hidden = false;
}

function renderInspector() {
  const content = getEl("inspect-content");
  if (!content) return;
  const data = state.inspect[state.inspectTab];
  content.textContent = data == null ? "No data for this tab yet." : JSON.stringify(data, null, 2);
  document.querySelectorAll(".inspect-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.inspectTab === state.inspectTab);
  });
}

function toggleInspector(open) {
  state.inspectOpen = open == null ? !state.inspectOpen : Boolean(open);
  const drawer = getEl("inspect-drawer");
  if (drawer) drawer.hidden = !state.inspectOpen;
  if (state.inspectOpen) renderInspector();
}

function selectInspectTab(tab) {
  state.inspectTab = tab;
  renderInspector();
}

document.addEventListener("DOMContentLoaded", () => {
  const start = getEl("start-btn");
  if (start) start.addEventListener("click", onStartBattleClick);
  const inspect = getEl("technical-inspect");
  if (inspect) inspect.addEventListener("click", () => toggleInspector(true));
  const close = getEl("inspect-close");
  if (close) close.addEventListener("click", () => toggleInspector(false));
  document.querySelectorAll(".inspect-tab").forEach((tab) => {
    tab.addEventListener("click", () => selectInspectTab(tab.dataset.inspectTab));
  });
  setStatusChip("backend-status", "BACKEND CONNECTING", "warn");
  setStatusChip("showdown-connection-status", "SHOWDOWN IDLE");
  setStatusChip("jev-status", "JEV IDLE");
  setGamePhase("IDLE");
  setTraceStep("validate-step", "READY");
  setTraceStep("act-step", "STANDBY");
  setTraceStep("result-step", "AWAITING SHOWDOWN");
  renderInspector();
  connectSocket();
});
