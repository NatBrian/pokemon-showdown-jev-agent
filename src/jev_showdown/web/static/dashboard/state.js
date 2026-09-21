const REQUIRED_STATE_KEYS = ["schema_version", "kind", "run", "battle", "renderer", "history", "metrics"];

export function createClientState() {
  return {
    dashboard: null,
    connected: false,
    stale: false,
    socketError: null,
    rawFrames: [],
    lastEventType: null,
  };
}

export function validateDashboardEnvelope(message) {
  if (!message || message.type !== "DASHBOARD_STATE" || !message.state) return false;
  const state = message.state;
  return REQUIRED_STATE_KEYS.every((key) => Object.prototype.hasOwnProperty.call(state, key)) && state.schema_version === 1;
}

export function applyDashboardState(clientState, message) {
  if (!validateDashboardEnvelope(message)) return clientState;
  return {
    ...clientState,
    dashboard: message.state,
    stale: false,
    socketError: null,
    lastEventType: message.event_type || null,
  };
}

export function applyConnectionState(clientState, connected, error = null) {
  return { ...clientState, connected, stale: !connected && Boolean(clientState.dashboard), socketError: error };
}

export function appendFrame(clientState, message) {
  const frames = clientState.rawFrames.concat([message]).slice(-400);
  return { ...clientState, rawFrames: frames };
}

export function selectedDecision(state) {
  return state?.inspection ? (state.history || []).find((item) =>
    item.battle_tag === state.inspection.selected_battle_tag && item.turn === state.inspection.selected_turn
  ) || state.current_turn : state?.current_turn || null;
}

export function actionById(turn, id) {
  return (turn?.harness?.legal_actions || []).find((action) => action.id === id) || null;
}

export function displayAction(turn, id) {
  const action = actionById(turn, id);
  return action?.label || id || "Unknown action";
}

export function percent(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return `${Math.round(value * 100)}%`;
}

export function duration(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${Math.round(value)}ms`;
}

export function number(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("en-US").format(value);
}
