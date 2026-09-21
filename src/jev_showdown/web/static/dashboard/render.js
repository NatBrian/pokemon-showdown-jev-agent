import { displayAction, duration, number, percent } from "./state.js";
import { renderProbabilityChart as renderProbabilityChartMarkup } from "./charts.js";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
let lastAnimationSignature = null;

function setText(selector, value) {
  const element = $(selector);
  if (element) element.textContent = value == null ? "--" : String(value);
  return element;
}

function emptyRow(text) {
  return `<div class="empty-row">${text}</div>`;
}

function factRow(label, value, mono = false) {
  const className = mono ? "fact-value mono" : "fact-value";
  return `<div class="fact-row"><span class="fact-label">${label}</span><span class="${className}">${value ?? "--"}</span></div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
}

function displayFact(value) {
  if (value == null) return null;
  if (typeof value === "object") return "structured data recorded";
  return String(value);
}

function activePokemon(snapshot, side) {
  const active = snapshot?.[side]?.active_pokemon;
  if (!active) return "Unknown";
  const species = active.species || "Unknown";
  const level = active.level ? ` · L${active.level}` : "";
  const hp = typeof active.hp_fraction === "number" ? ` · HP ${Math.round(active.hp_fraction * 100)}%` : "";
  return `${species}${level}${hp}`;
}

function renderObserved(turn) {
  const snapshot = turn?.harness?.snapshot || {};
  const request = turn?.harness?.request_metadata || {};
  const selfSlots = snapshot.self?.team?.length;
  const opponentSlots = snapshot.opponent?.team_slots || [];
  const revealed = opponentSlots.filter((slot) => slot && slot.revealed !== false && slot.species).length;
  const unknown = opponentSlots.filter((slot) => slot && slot.revealed === false).length;
  const opponentSlotsText = opponentSlots.length ? `${revealed} revealed · ${unknown} unknown` : "Unavailable";
  const rows = [
    factRow("Format", snapshot.battle_format || "Unknown", true),
    factRow("Battle", turn?.battle_tag || "Unknown", true),
    factRow("Turn", turn?.turn ?? snapshot.turn ?? "Unknown", true),
    factRow("Request type", request.request_type || "Unknown"),
    factRow("Showdown rqid", request.rqid ?? "Unknown", true),
    factRow("State version", request.state_version ?? "Unknown", true),
    factRow("Harness schema", snapshot.state_schema ?? "Unknown", true),
    factRow("Self active", activePokemon(snapshot, "self")),
    factRow("Opponent active", activePokemon(snapshot, "opponent")),
    factRow("Self team slots", selfSlots ? `${selfSlots} observed` : "Unavailable"),
    factRow("Opponent slots", opponentSlotsText),
    factRow("Tera available", snapshot.can_tera == null ? "Unknown" : snapshot.can_tera ? "Yes" : "No"),
    factRow("Weather", snapshot.weather || "None observed"),
  ];
  $("#harness-observed-facts").innerHTML = rows.join("");
}

function renderCalculations(turn) {
  const target = $("#harness-calculated-facts");
  const facts = turn?.harness?.calculated_facts || [];
  if (!facts.length) { target.innerHTML = emptyRow("No calculations yet"); return; }
  target.innerHTML = facts.slice(0, 5).map((fact) => {
    const data = fact.facts || {};
    const range = Array.isArray(data.utility_estimate) ? `${data.utility_estimate[0]}–${data.utility_estimate[1]} relative` : "Not recorded";
    const detail = [data.base_power ? `Power ${data.base_power}` : null, data.category, data.type, data.type_multiplier != null ? `Matchup ${displayFact(data.type_multiplier)}` : null].filter(Boolean).join(" · ");
    return `<article class="calculation-card"><h4>${escapeHtml(fact.label || fact.candidate_id)}</h4><span class="mono">${escapeHtml(fact.candidate_id || "unknown")}</span><p>${escapeHtml(detail || "Facts available")}</p><p>Heuristic relative estimate: ${escapeHtml(range)} · Damage/KO: unknown</p></article>`;
  }).join("");
}

function renderLegalActions(turn) {
  const actions = turn?.harness?.legal_actions || [];
  const selectedId = turn?.adapter?.validation?.chosen_id;
  const fallback = Boolean(turn?.adapter?.fallback?.is_fallback);
  setText("#legal-count", actions.length ? `${actions.length} LEGAL` : "--");
  const target = $("#legal-actions");
  if (!actions.length) { target.innerHTML = emptyRow("No legal candidates yet"); return; }
  target.innerHTML = actions.map((action) => {
    const selected = action.id === selectedId;
    const marker = selected ? (fallback ? "!" : "✓") : "✓";
    return `<div class="legal-action" data-selected="${selected}" data-fallback="${selected && fallback}" title="${escapeHtml(action.id)}"><span aria-hidden="true"></span><span class="legal-action-label">${escapeHtml(action.label || action.id)}</span><span class="legal-action-id">${escapeHtml(action.id)} <b class="legal-check">${marker}</b></span></div>`;
  }).join("");
}

function renderHandoff(turn) {
  const summary = turn?.harness?.handoff_summary;
  const target = $("#handoff-summary");
  if (!summary) { target.innerHTML = "<span>Awaiting a validated request</span>"; return; }
  target.innerHTML = [
    `<span><b class="handoff-value">${summary.candidate_count ?? "--"}</b> legal candidates</span>`,
    `<span><b class="handoff-value">${summary.question_count ?? "--"}</b> typed question</span>`,
    `<span>Schema <b class="handoff-value">${summary.state_schema ?? "--"}</b></span>`,
    `<span>rqid <b class="handoff-value">${summary.rqid ?? "--"}</b></span>`,
    `<span>State <b class="handoff-value">${summary.state_version ?? "--"}</b></span>`,
    `<span><b class="handoff-value">${summary.unknown_count ?? "--"}</b> unknown markers</span>`,
  ].join("");
}

function renderHarness(turn) {
  renderObserved(turn);
  renderCalculations(turn);
  renderLegalActions(turn);
  renderHandoff(turn);
  setText("#harness-state", turn ? (turn.lifecycle_state || "ACTIVE") : "WAITING");
}

function renderJev(turn) {
  const response = turn?.jev?.response_summary;
  const fallback = Boolean(turn?.adapter?.fallback?.is_fallback);
  const actionId = turn?.adapter?.validation?.chosen_id || response?.choice;
  setText("#jev-state", fallback ? "FALLBACK USED" : response?.error ? "INVALID RESPONSE" : response?.choice ? "RESPONSE RECEIVED" : "READY");
  setText("#selected-action", fallback ? `Fallback · ${displayAction(turn, actionId)}` : response?.choice ? displayAction(turn, response.choice) : "No decision yet");
  setText("#selected-action-id", actionId || "--");
  setText("#selected-confidence", response?.confidence != null && !fallback ? `Returned confidence ${percent(response.confidence)}` : fallback ? `Adapter fallback · ${turn.adapter.fallback.reason || "Reason unavailable"}` : "Returned confidence unavailable");
  const validation = $("#validation-result");
  validation.className = `result-row ${fallback ? "result-warning" : response?.error ? "result-error" : turn?.adapter?.validation?.chosen_id ? "result-success" : "result-neutral"}`;
  setText("#validation-label", fallback ? (turn.adapter.fallback.reason || "Fallback selected") : response?.error ? response.error : turn?.adapter?.validation?.chosen_id ? "Passed" : "Waiting for a decision");
  const submitted = turn?.adapter?.submitted_order?.message;
  setText("#submitted-order", submitted || "Waiting for Adapter");
  const metadata = $("#jev-metadata");
  if (!response) metadata.innerHTML = emptyRow("No response metadata yet");
  else metadata.innerHTML = [
    factRow("Model", response.model || "Not reported", true),
    factRow("Jev latency", duration(response.latency_ms)),
    factRow("Wrapper latency", duration(turn.timing?.wrapper_latency_ms)),
    factRow("Decision latency", duration(turn.timing?.decision_latency_ms)),
    factRow("Input tokens", response.input_tokens == null ? "Unavailable" : number(response.input_tokens)),
    factRow("Output tokens", response.output_tokens == null ? "Unavailable" : number(response.output_tokens)),
    factRow("Reported cost", response.cost == null ? "Unavailable" : response.cost),
  ].join("");
  renderProbabilityChartMarkup(turn, $("#probability-chart"));
}

function renderReliability(metrics) {
  const values = [[metrics?.jev_calls, "JEV CALLS"], [metrics?.fallbacks, "FALLBACKS"], [metrics?.illegal_actions, "ILLEGAL"]];
  $("#reliability-tiles").innerHTML = values.map(([value, label]) => `<div class="metric-tile"><strong>${value == null ? "--" : value}</strong><span>${label}</span></div>`).join("");
}

function renderStages(turn, battle) {
  const stages = $$(".lifecycle-stage");
  const snapshot = turn?.harness?.snapshot;
  const statuses = {
    observe: turn ? "complete" : "pending",
    calculate: snapshot ? "complete" : "pending",
    options: turn?.harness?.legal_actions?.length ? "complete" : "pending",
    jev: turn?.jev?.response_summary?.choice || turn?.jev?.response_summary?.error ? "complete" : turn ? "active" : "pending",
    validate: turn?.adapter?.validation?.chosen_id ? (turn.adapter.fallback?.is_fallback ? "error" : "complete") : "pending",
    act: turn?.adapter?.submitted_order?.message ? "complete" : "pending",
    result: battle?.state === "complete" ? "complete" : turn ? "active" : "pending",
  };
  const labels = {
    observe: turn ? "State captured" : "Waiting",
    calculate: snapshot ? "Facts available" : "Waiting",
    options: turn?.harness?.legal_actions?.length ? `${turn.harness.legal_actions.length} legal` : "Waiting",
    jev: turn?.jev?.response_summary?.latency_ms != null ? duration(turn.jev.response_summary.latency_ms) : turn?.jev?.response_summary?.error ? "Error" : "Waiting",
    validate: turn?.adapter?.fallback?.is_fallback ? "Fallback" : turn?.adapter?.validation?.chosen_id ? "Passed" : "Waiting",
    act: turn?.adapter?.submitted_order?.message || "Waiting",
    result: battle?.state === "complete" ? "Observed" : turn ? "Awaiting" : "Waiting",
  };
  stages.forEach((stage) => { const key = stage.dataset.stage; stage.dataset.status = statuses[key]; const small = stage.querySelector("small"); if (small) small.textContent = labels[key]; });
  setText("#turn-summary", turn ? `Turn ${turn.turn} · ${turn.lifecycle_state}` : "Awaiting a battle turn");
}

function renderHistory(history, selected) {
  const target = $("#history-list");
  if (!history?.length) { target.innerHTML = `<div class="history-empty"><span class="empty-seal" aria-hidden="true">≋</span><span>Decision records will appear here after the first Jev turn.</span></div>`; return; }
  const limitButton = $(".history-filter.is-active");
  const limit = limitButton?.dataset.historyLimit === "all" ? history.length : Number(limitButton?.dataset.historyLimit || 5);
  target.innerHTML = history.slice(-limit).reverse().map((item) => {
    const fallback = Boolean(item.adapter?.fallback?.is_fallback);
    const response = item.jev?.response_summary;
    const action = fallback ? `Fallback · ${displayAction(item, item.adapter?.validation?.chosen_id)}` : displayAction(item, response?.choice || item.adapter?.validation?.chosen_id);
    const status = fallback ? "FALLBACK" : item.adapter?.submitted_order?.message ? "SUBMITTED" : "PENDING";
    const selectedNow = selected && selected.battle_tag === item.battle_tag && selected.turn === item.turn;
    return `<button class="history-card" type="button" data-battle-tag="${escapeHtml(item.battle_tag)}" data-turn="${item.turn}" data-fallback="${fallback}" data-selected="${selectedNow}"><span class="history-card-top"><span class="history-turn">TURN ${item.turn}</span><span class="history-status">${status}</span></span><h3>${escapeHtml(action)}</h3><span class="history-card-bottom"><span>${response?.confidence != null && !fallback ? `${percent(response.confidence)} confidence` : fallback ? escapeHtml(item.adapter.fallback.reason || "Fallback") : "Confidence unavailable"}</span><span>${duration(item.timing?.decision_latency_ms)}</span></span></button>`;
  }).join("");
}

function renderBattleChrome(state) {
  const battle = state?.battle || {};
  const renderer = state?.renderer || {};
  setText("#battle-format", state?.run?.format || "RANDOM BATTLE");
  setText("#battle-tag", battle.battle_tag || "NO ACTIVE BATTLE");
  setText("#current-turn-number", state?.current_turn?.turn ?? "--");
  setText("#turn-strip-number", state?.current_turn?.turn ?? "--");
  setText("[data-connection-label]", renderer.connection_label || "READY");
  setText("#battle-state-label", battle.state === "active" ? "LIVE" : battle.state === "complete" ? "RESULT OBSERVED" : "WAITING FOR BATTLE");
  setText("#showdown-status", renderer.connection_label || "Waiting for public battle protocol");
  setText("#last-observed", renderer.last_observed_at ? new Date(renderer.last_observed_at).toLocaleTimeString() : "--");
  const active = battle.state === "active" || battle.state === "complete";
  $("#battle-empty-state").hidden = active;
  $("#showdown-canvas").hidden = !active;
}

function animateEvent(clientState, state) {
  const eventType = clientState.lastEventType;
  if (!eventType) return;
  const turn = state.current_turn;
  const signature = `${eventType}:${turn?.battle_tag || state.battle?.battle_tag || ""}:${turn?.turn || ""}`;
  if (signature === lastAnimationSignature) return;
  lastAnimationSignature = signature;
  const selectors = eventType === "BATTLE_START"
    ? ["#battle-panel", "#current-turn-strip"]
    : eventType === "BATTLE_END"
      ? ["#battle-panel", "#decision-history"]
      : eventType === "TURN_DECISION"
        ? ["#system-harness", "#jev-panel", "#decision-hero", "#current-turn-strip", "#decision-history"]
        : [];
  const fallback = eventType === "TURN_DECISION" && turn?.adapter?.fallback?.is_fallback;
  selectors.map((selector) => $(selector)).filter(Boolean).forEach((element) => {
    element.classList.remove("event-pulse", "event-fallback");
    void element.offsetWidth;
    element.classList.add(fallback ? "event-fallback" : "event-pulse");
    window.setTimeout(() => element.classList.remove("event-pulse", "event-fallback"), 850);
  });
}

export function renderDashboard(clientState, selected = null) {
  const state = clientState.dashboard;
  if (!state) return;
  renderBattleChrome(state);
  renderHarness(state.current_turn);
  renderJev(state.current_turn);
  renderReliability(state.metrics);
  renderStages(state.current_turn, state.battle);
  renderHistory(state.history, selected);
  animateEvent(clientState, state);
  const button = $("#start-battle");
  const running = state.battle.state === "active" || state.run.status === "JEV PLAYING";
  button.disabled = running;
  button.textContent = running ? "BATTLE RUNNING" : state.battle.state === "complete" ? "START NEW BATTLE" : "START JEV BATTLE";
}

export function announce(message) {
  setText("#live-announcer", message);
}

export function query(selector) { return $(selector); }
export function queryAll(selector) { return $$(selector); }
