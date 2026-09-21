import { actionById, displayAction, duration, number, percent } from "./state.js";
import { renderCandidateMatrix, renderLatencySummary, renderRunMetrics } from "./charts.js";

const $ = (selector, root = document) => root.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
}

function safeJson(value) {
  try { return JSON.stringify(value ?? null, null, 2); } catch { return "[unserializable]"; }
}

function fact(label, value, source = "RECORDED") {
  const printable = value == null || value === "" ? "Unavailable" : typeof value === "object" ? safeJson(value) : String(value);
  return `<div class="drawer-fact"><span>${escapeHtml(label)} <em>${escapeHtml(source)}</em></span><span>${escapeHtml(printable)}</span></div>`;
}

function section(title, body) {
  return `<section class="drawer-section"><h3>${escapeHtml(title)}</h3>${body}</section>`;
}

function jsonBlock(label, value, key) {
  return section(label, `<button type="button" class="drawer-copy" data-copy-key="${escapeHtml(key)}">COPY</button><pre class="drawer-json" data-json-key="${escapeHtml(key)}">${escapeHtml(safeJson(value))}</pre>`);
}

function decisionLabel(decision) {
  if (!decision) return "No decision selected";
  const actionId = decision.adapter?.validation?.chosen_id || decision.jev?.response_summary?.choice;
  const action = displayAction(decision, actionId);
  const status = decision.adapter?.fallback?.is_fallback ? "FALLBACK" : decision.adapter?.submitted_order?.message ? "SUBMITTED" : "RECORDED";
  return `Turn ${decision.turn ?? "--"} · ${action} · ${status} · ${decision.battle_tag || "unknown battle"}`;
}

function overview(decision) {
  if (!decision) return '<div class="drawer-empty">Select a decision card or open inspection after a real response.</div>';
  const response = decision.jev?.response_summary || {};
  const validation = decision.adapter?.validation || {};
  const fallback = decision.adapter?.fallback || {};
  return [
    section("Decision boundary", [
      fact("Battle / turn", `${decision.battle_tag || "Unknown"} / ${decision.turn ?? "Unknown"}`, "SHOWDOWN"),
      fact("Returned choice", response.choice ? displayAction(decision, response.choice) : "Unavailable", "JEV OUTPUT"),
      fact("Confidence", response.confidence == null ? "Unavailable" : percent(response.confidence), "JEV OUTPUT"),
      fact("Validation", validation.chosen_id ? (fallback.is_fallback ? "Fallback path" : "Passed") : response.error || "Unavailable", "ADAPTER"),
      fact("Submitted order", decision.adapter?.submitted_order?.message || "Unavailable", "SHOWDOWN"),
      fact("Unknown fields", decision.harness?.unknowns?.length ? decision.harness.unknowns.join(", ") : "None recorded", "HARNESS"),
    ].join("")),
    section("Recorded latency", '<div id="drawer-latency"></div>'),
    section("Candidate comparison", '<div id="drawer-candidate-matrix"></div>'),
  ].join("");
}

function tabMarkup(tab, decision, state) {
  if (!decision && tab !== "run-metrics") return overview(null);
  const response = decision?.jev?.response_summary || {};
  const harness = decision?.harness || {};
  const request = decision?.showdown?.request || harness.request_metadata;
  const validation = decision?.adapter?.validation || {};
  const submitted = decision?.adapter?.submitted_order || {};
  switch (tab) {
    case "showdown-request": return jsonBlock("Showdown request metadata", request, "showdown-request");
    case "harness-state": return [
      section("Snapshot fields", [
        fact("State schema", harness.snapshot?.state_schema, "HARNESS"),
        fact("Turn", harness.snapshot?.turn, "SHOWDOWN"),
        fact("Weather", harness.snapshot?.weather || "None observed", "SHOWDOWN"),
        fact("Tera available", harness.snapshot?.can_tera == null ? "Unknown" : harness.snapshot.can_tera ? "Yes" : "No", "SHOWDOWN"),
        fact("Unknown count", harness.unknowns?.length ?? 0, "HARNESS"),
      ].join("")),
      jsonBlock("Redacted state snapshot", harness.snapshot, "harness-state"),
    ].join("");
    case "calculated-facts": return [
      section("Harness facts", (harness.calculated_facts || []).map((item) => `<div class="drawer-fact"><span>${escapeHtml(item.label || item.candidate_id)} <em>HARNESS</em></span><span>${escapeHtml(safeJson(item.facts))}</span></div>`).join("") || '<div class="drawer-empty">No deterministic calculations recorded.</div>'),
      '<div id="drawer-candidate-matrix"></div>',
    ].join("");
    case "jev-input": return [
      section("Input summary", [
        fact("Model", decision?.jev?.request_summary?.model, "JEV INPUT"),
        fact("Candidate count", decision?.jev?.request_summary?.candidate_count, "HARNESS"),
        fact("Question", decision?.jev?.request_summary?.question, "JEV INPUT"),
      ].join("")),
      jsonBlock("Structured Jev input", decision?.raw_event?.jev_request || decision?.jev?.request_summary, "jev-input"),
    ].join("");
    case "jev-response": return [
      section("Response fields", [
        fact("Model", response.model, "JEV OUTPUT"),
        fact("Choice", response.choice ? displayAction(decision, response.choice) : "Unavailable", "JEV OUTPUT"),
        fact("Confidence", response.confidence == null ? "Unavailable" : percent(response.confidence), "JEV OUTPUT"),
        fact("Probability status", decision?.jev?.probability_status, "ADAPTER"),
        fact("Input tokens", response.input_tokens == null ? "Unavailable" : number(response.input_tokens), "JEV OUTPUT"),
        fact("Output tokens", response.output_tokens == null ? "Unavailable" : number(response.output_tokens), "JEV OUTPUT"),
        fact("Reported cost", response.cost, "JEV OUTPUT"),
        fact("Error", response.error, "JEV OUTPUT"),
      ].join("")),
      jsonBlock("Redacted Jev response", decision?.jev?.raw_response || response, "jev-response"),
    ].join("");
    case "validation": return [
      section("Validation result", [
        fact("Chosen ID", validation.chosen_id, "ADAPTER"),
        fact("Legal candidates", validation.legal_candidates, "HARNESS"),
        fact("Validation latency", duration(validation.latency_ms), "ADAPTER"),
        fact("Fallback", decision?.adapter?.fallback?.is_fallback ? "Yes" : "No", "ADAPTER"),
        fact("Fallback reason", decision?.adapter?.fallback?.reason, "ADAPTER"),
      ].join("")),
      jsonBlock("Validation record", validation, "validation"),
    ].join("");
    case "submitted-order": return [
      section("Order acknowledgement", [
        fact("Command", submitted.message, "SHOWDOWN"),
        fact("Chosen ID", submitted.chosen_id, "ADAPTER"),
        fact("Fallback", submitted.is_fallback ? "Yes" : "No", "ADAPTER"),
      ].join("")),
      submitted.message ? jsonBlock("Submitted order record", submitted, "submitted-order") : '<div class="drawer-empty">No order was submitted.</div>',
    ].join("");
    case "protocol-evidence": return [
      section("Battle protocol", [
        fact("Frame captured for this decision", decision?.showdown?.protocol_evidence?.raw_frame_captured ? "Yes" : "No", "SHOWDOWN"),
        fact("Available renderer frames", state?.rawFrames?.length || 0, "SHOWDOWN"),
        fact("Battle replay", state?.dashboard?.battle?.replay === "available" ? "Available" : "Replay unavailable", "SHOWDOWN"),
      ].join("")),
      '<div class="drawer-empty">Raw protocol frame not captured for this decision. The official renderer remains the live battle surface.</div>',
    ].join("");
    case "raw-event": return jsonBlock("Redacted raw telemetry event", decision?.raw_event, "raw-event");
    case "run-metrics": return '<div id="drawer-run-metrics"></div><div id="drawer-run-latency"></div>';
    case "overview": return overview(decision);
    default: return overview(decision);
  }
}

export function installInspector({ getState, getSelected, setMode = () => {} }) {
  const drawer = $("#inspection-drawer");
  const content = $("#drawer-content");
  const selection = $("#drawer-selection");
  let activeTab = "overview";
  let currentDecision = null;
  const copyPayloads = new Map();

  function setTab(tab) {
    const known = new Set(Array.from(document.querySelectorAll(".drawer-tab")).map((button) => button.dataset.inspectTab));
    activeTab = known.has(tab) ? tab : "overview";
    document.querySelectorAll(".drawer-tab").forEach((button) => {
      const active = button.dataset.inspectTab === activeTab;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      if (!button.id) button.id = `drawer-tab-${button.dataset.inspectTab}`;
      if (active) button.setAttribute("aria-controls", "inspection-panel");
      else button.removeAttribute("aria-controls");
      button.tabIndex = active ? 0 : -1;
    });
  }

  function render() {
    const state = getState();
    currentDecision = getSelected() || currentDecision;
    selection.textContent = decisionLabel(currentDecision);
    setTab(activeTab);
    copyPayloads.clear();
    content.innerHTML = tabMarkup(activeTab, currentDecision, state);
    content.id = "inspection-panel";
    const activeTabButton = document.querySelector(`.drawer-tab[data-inspect-tab="${activeTab}"]`);
    content.setAttribute("aria-labelledby", activeTabButton?.id || "");
    content.querySelectorAll("[data-json-key]").forEach((node) => {
      const key = node.dataset.jsonKey;
      copyPayloads.set(key, node.textContent);
    });
    if (activeTab === "overview") {
      renderLatencySummary(state, $("#drawer-latency", content));
      renderCandidateMatrix(currentDecision, $("#drawer-candidate-matrix", content));
    }
    if (activeTab === "calculated-facts") renderCandidateMatrix(currentDecision, $("#drawer-candidate-matrix", content));
    if (activeTab === "run-metrics") {
      renderRunMetrics(state?.dashboard?.metrics || {}, $("#drawer-run-metrics", content));
      renderLatencySummary(state?.dashboard || {}, $("#drawer-run-latency", content));
    }
  }

  window.addEventListener("jev:inspect", (event) => {
    currentDecision = event.detail?.decision || getSelected() || null;
    if (event.detail?.tab) activeTab = event.detail.tab;
    render();
  });
  document.addEventListener("click", (event) => {
    const tab = event.target.closest?.(".drawer-tab");
    if (tab) { activeTab = tab.dataset.inspectTab; render(); return; }
    const contextual = event.target.closest?.("[data-inspect-tab]");
    if (contextual) { setMode("inspect"); activeTab = contextual.dataset.inspectTab; render(); return; }
    const copy = event.target.closest?.("[data-copy-key]");
    if (!copy) return;
    const payload = copyPayloads.get(copy.dataset.copyKey);
    if (!payload) return;
    navigator.clipboard?.writeText(payload).then(() => {
      const prior = copy.textContent;
      copy.textContent = "COPIED";
      setTimeout(() => { copy.textContent = prior; }, 900);
    }).catch(() => { copy.textContent = "COPY FAILED"; });
  });
  document.addEventListener("keydown", (event) => {
    const tab = event.target.closest?.(".drawer-tab");
    if (!tab || !["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    const tabs = Array.from(document.querySelectorAll(".drawer-tab"));
    const current = tabs.indexOf(tab);
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    event.preventDefault();
    activeTab = tabs[next].dataset.inspectTab;
    tabs[next].focus();
    render();
  });
  return { refresh: render };
}
