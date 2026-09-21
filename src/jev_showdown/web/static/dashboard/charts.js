import { actionById, duration, number, percent } from "./state.js";

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));

const mount = (target, markup) => {
  if (target) target.innerHTML = markup;
  return markup;
};

export function renderProbabilityChart(turn, target = null) {
  const jev = turn?.jev;
  if (!jev) return mount(target, '<div class="empty-row">No probability map returned</div>');
  if (jev.probability_status === "rejected") {
    return mount(target, `<div class="empty-row"><strong>Probability map rejected</strong><br>${escapeHtml(jev.response_summary?.error || "Validation rejected the returned map")}</div>`);
  }
  const probabilities = jev.response_summary?.probabilities;
  if (!probabilities) return mount(target, '<div class="empty-row">Not returned by Jev</div>');
  const selected = jev.response_summary.choice;
  const rows = Object.entries(probabilities).sort(([, left], [, right]) => right - left).map(([id, value]) => {
    const action = actionById(turn, id);
    const safeValue = Math.max(0, Math.min(100, value * 100));
    return `<div class="probability-row" data-selected="${id === selected}" title="${escapeHtml(id)}"><span class="probability-label">${escapeHtml(action?.label || id)}</span><span class="probability-track" role="img" aria-label="${escapeHtml(action?.label || id)} ${Math.round(value * 100)} percent"><span class="probability-fill" style="width:${safeValue}%"></span></span><span class="probability-value">${Math.round(value * 100)}%</span></div>`;
  }).join("");
  return mount(target, rows || '<div class="empty-row">No probability entries returned</div>');
}

export function renderLatencySummary(stateOrTurn, target = null) {
  const state = stateOrTurn?.current_turn ? stateOrTurn : null;
  const turn = state ? state.current_turn : stateOrTurn;
  const metrics = state?.metrics || {};
  const rows = [
    ["Jev response", duration(turn?.timing?.response_latency_ms ?? turn?.jev?.response_summary?.latency_ms)],
    ["Wrapper", duration(turn?.timing?.wrapper_latency_ms)],
    ["Validation / decision", duration(turn?.timing?.decision_latency_ms)],
    ["Run p50", duration(metrics.latency_p50_ms)],
    ["Run p95", duration(metrics.latency_p95_ms)],
    ["Run p99", duration(metrics.latency_p99_ms)],
  ];
  const markup = `<div class="latency-grid">${rows.map(([label, value]) => `<div class="latency-cell"><span>${label}</span><strong>${value}</strong></div>`).join("")}</div>`;
  return mount(target, markup);
}

export function renderRunMetrics(metrics = {}, target = null) {
  const values = [
    ["Battles complete", metrics.battles_completed, "normal"],
    ["Jev calls", metrics.jev_calls, "normal"],
    ["Valid choices", metrics.valid_choices, "normal"],
    ["Fallbacks", metrics.fallbacks, metrics.fallbacks ? "warning" : "normal"],
    ["Illegal actions", metrics.illegal_actions, metrics.illegal_actions ? "error" : "normal"],
    ["Provider errors", metrics.provider_errors, metrics.provider_errors ? "error" : "normal"],
    ["HTTP 503 errors", metrics.provider_503_errors, metrics.provider_503_errors ? "error" : "normal"],
    ["Request timeouts", metrics.request_timeouts, metrics.request_timeouts ? "warning" : "normal"],
    ["Protocol errors", metrics.protocol_validation_errors, metrics.protocol_validation_errors ? "error" : "normal"],
    ["Stale responses", metrics.stale_responses, metrics.stale_responses ? "warning" : "normal"],
    ["Timer failures", metrics.timer_failures, metrics.timer_failures ? "error" : "normal"],
  ];
  const markup = `<div class="run-metric-grid">${values.map(([label, value, tone]) => `<div class="run-metric-cell tone-${tone}"><strong>${value == null ? "--" : number(value)}</strong><span>${label}</span></div>`).join("")}</div><p class="chart-note">Counters are recorded observations. A zero does not imply a provider or protocol check was performed.</p>`;
  return mount(target, markup);
}

export function renderCandidateMatrix(turn, target = null) {
  const actions = turn?.harness?.legal_actions || [];
  const probabilities = turn?.jev?.response_summary?.probabilities || {};
  const selected = turn?.jev?.response_summary?.choice || turn?.adapter?.validation?.chosen_id;
  const submitted = turn?.adapter?.submitted_order?.chosen_id;
  if (!actions.length) return mount(target, '<div class="drawer-empty">No legal candidate set recorded.</div>');
  const rows = actions.map((action) => {
    const probability = Object.prototype.hasOwnProperty.call(probabilities, action.id) ? percent(probabilities[action.id]) : "Not included";
    return `<tr><td class="mono">${escapeHtml(action.id)}</td><td>${escapeHtml(action.label || action.id)}</td><td>${probability}</td><td>${action.id === selected ? "Yes" : "No"}</td><td>${action.id === submitted ? "Yes" : "No"}</td></tr>`;
  }).join("");
  const markup = `<div class="matrix-scroll"><table class="candidate-matrix"><caption>Legal candidates compared with the returned Jev map</caption><thead><tr><th>Candidate ID</th><th>Action</th><th>Probability</th><th>Selected</th><th>Submitted</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  return mount(target, markup);
}
