(function () {
  "use strict";

  const RESULT_COMMANDS = new Set([
    "move",
    "switch",
    "drag",
    "-damage",
    "-heal",
    "-status",
    "-stat",
    "faint",
    "-terastallize",
    "win",
    "tie",
    "cant",
  ]);

  function summarizeProtocolLines(lines) {
    const commands = [];
    const observed = [];
    if (!Array.isArray(lines)) {
      return { commands, observed };
    }
    lines.forEach(function (rawLine) {
      if (typeof rawLine !== "string") return;
      const parts = rawLine.trim().split("|");
      const command = parts.length > 1 ? parts[1] : "";
      if (!command) return;
      if (!commands.includes(command)) commands.push(command);
      if (RESULT_COMMANDS.has(command) && !observed.includes(command)) {
        observed.push(command);
      }
    });
    return { commands, observed };
  }

  function createDashboardApp(options) {
    options = options || {};
    const root = options.root || document;
    const renderer = options.renderer || window.JevShowdownRenderer;
    const WebSocketImpl = options.WebSocketImpl || window.WebSocket;

    const node = function (id) {
      return root.getElementById(id);
    };

    const nodes = {
      root: node("dashboard-root"),
      start: node("start-btn"),
      turn: node("turn-readout"),
      backend: node("backend-status"),
      showdown: node("showdown-connection"),
      jev: node("jev-status"),
      format: node("battle-format"),
      arena: node("showdown-arena"),
      frame: node("showdown-frame"),
      log: node("showdown-log"),
      sceneStatus: node("showdown-status"),
      rendererFallback: node("renderer-fallback"),
      input: node("jev-input"),
      inputPhase: node("input-phase"),
      inputContent: node("jev-input-content"),
      decision: node("jev-decision"),
      decisionPhase: node("decision-phase"),
      decisionContent: node("jev-decision-content"),
      history: node("jev-history-list"),
      truth: node("truth-strip"),
      truthLegal: node("truth-legal"),
      truthSubmitted: node("truth-submitted"),
      truthObserved: node("truth-observed"),
      inspectButton: node("technical-inspect"),
      inspectDrawer: node("inspect-drawer"),
      inspectClose: node("inspect-close"),
      inspectContent: node("inspect-content"),
    };

    const state = {
      socket: "closed",
      battleTag: null,
      battleFormat: "gen9randombattle",
      battleEnded: false,
      status: { text: "READY", busy: false, error: false },
      renderer: { mounted: false, failed: false },
      current: {
        decisionId: null,
        turn: null,
        phase: "IDLE",
        input: null,
        decision: null,
        validation: null,
        order: null,
        observedCommands: [],
      },
      history: [],
      recentFrames: [],
      inspectorOpen: false,
      inspectorSelection: null,
    };

    let socket = null;
    let reconnectTimer = null;
    let destroyed = false;

    function clear(element) {
      if (element) element.replaceChildren();
    }

    function makeElement(tagName, className, text) {
      const element = root.createElement(tagName);
      if (className) element.className = className;
      if (text !== undefined && text !== null) element.textContent = String(text);
      return element;
    }

    function setText(element, value) {
      if (element) element.textContent = value === undefined || value === null ? "" : String(value);
    }

    function setState(element, value) {
      if (element) element.dataset.state = value || "idle";
    }

    function isNumber(value) {
      return typeof value === "number" && Number.isFinite(value);
    }

    function formatPercent(value) {
      return isNumber(value) ? Math.round(value * 100) + "%" : null;
    }

    function formatLatency(value) {
      return isNumber(value) && value > 0 ? Math.round(value) + " ms" : null;
    }

    function formatCost(value) {
      return value !== undefined && value !== null && value !== "" ? String(value) : null;
    }

    function addDataRow(container, label, value, className) {
      if (value === undefined || value === null || value === "") return null;
      const row = makeElement("div", "data-row" + (className ? " " + className : ""));
      row.append(makeElement("span", "data-label", label));
      row.append(makeElement("span", "data-value", value));
      container.append(row);
      return row;
    }

    function addSectionHeading(container, label) {
      container.append(makeElement("div", "subheading", label));
    }

    function addJSON(container, label, value) {
      if (value === undefined || value === null) return;
      const section = makeElement("section", "inspect-block");
      section.append(makeElement("h3", "inspect-label", label));
      const pre = makeElement("pre", "inspect-json");
      pre.textContent = JSON.stringify(value, null, 2);
      section.append(pre);
      container.append(section);
    }

    function activeMatchup(snapshot) {
      const selfActive = snapshot && snapshot.self && snapshot.self.active_pokemon;
      const opponentActive = snapshot && snapshot.opponent && snapshot.opponent.active_pokemon;
      const selfName = selfActive && selfActive.species;
      const opponentName = opponentActive && opponentActive.species;
      if (!selfName && !opponentName) return null;
      return String(selfName || "Unknown") + " vs " + String(opponentName || "Unknown");
    }

    function currentSnapshot() {
      return state.current.input && state.current.input.snapshot
        ? state.current.input.snapshot
        : null;
    }

    function probabilities() {
      const decision = state.current.decision;
      return decision && decision.jev && decision.jev.probabilities
        ? decision.jev.probabilities
        : {};
    }

    function sortedLegalActions(snapshot) {
      const actions = snapshot && Array.isArray(snapshot.legal_actions)
        ? snapshot.legal_actions.slice()
        : [];
      const values = probabilities();
      if (!actions.length || !values || !Object.keys(values).length) return actions.slice(0, 4);
      return actions
        .map(function (action, index) {
          return { action, index, probability: isNumber(values[action.id]) ? values[action.id] : -1 };
        })
        .sort(function (left, right) {
          return right.probability - left.probability || left.index - right.index;
        })
        .slice(0, 4)
        .map(function (item) { return item.action; });
    }

    function factText(facts) {
      if (!facts || typeof facts !== "object") return [];
      const result = [];
      if (facts.type_multiplier !== undefined) {
        result.push(String(facts.type_multiplier) + "x TYPE");
      }
      if (Array.isArray(facts.estimated_damage_range) && facts.estimated_damage_range.length >= 2) {
        const prefix = facts.calculation_mode === "poke_env_gen9" ? "CALC" : "EST";
        result.push(prefix + " " + facts.estimated_damage_range[0] + "-" + facts.estimated_damage_range[1] + "%");
      }
      if (facts.estimated_ko === true) result.push("LIKELY KO");
      if (facts.priority !== undefined) result.push("PRIORITY " + facts.priority);
      if (facts.speed_relation !== undefined) result.push(String(facts.speed_relation));
      if (facts.switch_cost !== undefined) result.push("SWITCH " + facts.switch_cost);
      return result;
    }

    function renderHeader() {
      const currentTurn = state.current.turn;
      setText(nodes.turn, currentTurn ? "TURN " + currentTurn : "TURN --");

      const socketLabel = state.socket === "open"
        ? "BACKEND CONNECTED"
        : state.socket === "connecting"
          ? "BACKEND CONNECTING"
          : state.socket === "reconnecting"
            ? "BACKEND RECONNECTING"
            : "BACKEND OFFLINE";
      setText(nodes.backend, socketLabel);
      setState(nodes.backend, state.socket === "open" ? "good" : "warn");

      let showdownLabel = "SHOWDOWN READY";
      let showdownState = "idle";
      const statusText = state.status.text || "";
      if (state.battleEnded) {
        showdownLabel = "SHOWDOWN ENDED";
        showdownState = "good";
      } else if (state.battleTag) {
        showdownLabel = state.current.phase === "AWAITING_SHOWDOWN"
          ? "SHOWDOWN AWAITING"
          : "SHOWDOWN LIVE";
        showdownState = "good";
      } else if (statusText.includes("SEARCHING")) {
        showdownLabel = "SHOWDOWN SEARCHING";
        showdownState = "active";
      } else if (statusText.includes("AUTHENTICATING")) {
        showdownLabel = "SHOWDOWN AUTHENTICATING";
        showdownState = "active";
      } else if (statusText.includes("CONNECTING")) {
        showdownLabel = "SHOWDOWN CONNECTING";
        showdownState = "active";
      } else if (state.status.error) {
        showdownLabel = "SHOWDOWN ERROR";
        showdownState = "error";
      }
      setText(nodes.showdown, showdownLabel);
      setState(nodes.showdown, showdownState);

      let jevLabel = "JEV IDLE";
      let jevState = "idle";
      if (state.current.phase === "JEV_EVALUATING") {
        jevLabel = "JEV EVALUATING";
        jevState = "active";
      } else if (state.current.decision && state.current.decision.isFallback) {
        jevLabel = "JEV FALLBACK";
        jevState = "warn";
      } else if (state.current.decision) {
        jevLabel = "JEV RESPONDED";
        jevState = "good";
      } else if (state.status.error && statusText.includes("JEV")) {
        jevLabel = "JEV ERROR";
        jevState = "error";
      }
      setText(nodes.jev, jevLabel);
      setState(nodes.jev, jevState);

      if (nodes.start) {
        nodes.start.disabled = state.status.busy || state.socket !== "open";
        setText(nodes.start, state.status.busy ? "JEV PLAYING" : "START JEV BATTLE");
      }
      setText(nodes.format, state.battleFormat.toUpperCase());
    }

    function renderInput() {
      clear(nodes.inputContent);
      nodes.input.dataset.phase = state.current.phase;
      setText(nodes.inputPhase, state.current.phase);

      const input = state.current.input;
      const snapshot = currentSnapshot();
      if (!snapshot) {
        nodes.inputContent.append(makeElement("p", "empty-state", "WAITING FOR A BATTLE TURN"));
        return;
      }

      const matchup = activeMatchup(snapshot);
      if (state.current.turn) addDataRow(nodes.inputContent, "TURN", state.current.turn);
      if (matchup) addDataRow(nodes.inputContent, "MATCHUP", matchup);

      const actions = Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions : [];
      addDataRow(nodes.inputContent, "LEGAL ACTIONS", actions.length);
      if (actions.length) {
        addSectionHeading(nodes.inputContent, "OPTIONS");
        const optionList = makeElement("div", "option-list");
        sortedLegalActions(snapshot).forEach(function (action) {
          const row = makeElement("div", "option-row");
          row.append(makeElement("span", "option-label", action.label || action.id));
          const facts = factText(action.facts);
          if (facts.length) {
            const factsNode = makeElement("span", "fact-chips");
            facts.forEach(function (fact) {
              factsNode.append(makeElement("span", "fact-chip", fact));
            });
            row.append(factsNode);
          }
          optionList.append(row);
        });
        nodes.inputContent.append(optionList);
      }

      const question = input && input.question;
      if (question && question.instructions) {
        addDataRow(nodes.inputContent, "QUESTION", question.instructions, "question-row");
      }
    }

    function renderDecision() {
      clear(nodes.decisionContent);
      nodes.decision.dataset.phase = state.current.phase;
      setText(nodes.decisionPhase, state.current.phase);

      if (state.current.phase === "JEV_EVALUATING") {
        const loading = makeElement("div", "evaluation-loading");
        loading.append(makeElement("span", "loading-dot"));
        loading.append(makeElement("span", "loading-label", "EVALUATING"));
        nodes.decisionContent.append(loading);
        nodes.decisionContent.append(makeElement("p", "muted-note", "Waiting for the typed Jev response."));
        return;
      }

      const decision = state.current.decision;
      if (!decision) {
        nodes.decisionContent.append(makeElement("p", "empty-state", "WAITING FOR JEV DECISION"));
        return;
      }

      if (decision.isFallback) {
        const fallback = makeElement("div", "fallback-state");
        fallback.append(makeElement("div", "decision-alert", "FALLBACK USED"));
        addDataRow(fallback, "ADAPTER ACTION", decision.label || decision.chosenId);
        if (decision.fallbackReason) addDataRow(fallback, "REASON", decision.fallbackReason);
        nodes.decisionContent.append(fallback);
        return;
      }

      addDataRow(nodes.decisionContent, "SELECTED", decision.label || decision.jev.choice);
      const confidence = formatPercent(decision.jev.confidence);
      if (confidence) addDataRow(nodes.decisionContent, "CONFIDENCE", confidence);

      const model = decision.jev.model;
      if (model && model !== "unknown") addDataRow(nodes.decisionContent, "MODEL", model);
      const latency = formatLatency(decision.jev.latency_ms);
      if (latency) addDataRow(nodes.decisionContent, "LATENCY", latency);
      if (isNumber(decision.jev.input_tokens) && decision.jev.input_tokens > 0) {
        addDataRow(nodes.decisionContent, "INPUT TOKENS", decision.jev.input_tokens);
      }
      if (isNumber(decision.jev.output_tokens) && decision.jev.output_tokens > 0) {
        addDataRow(nodes.decisionContent, "OUTPUT TOKENS", decision.jev.output_tokens);
      }
      const cost = formatCost(decision.jev.cost);
      if (cost) addDataRow(nodes.decisionContent, "COST", cost);

      const values = decision.jev.probabilities || {};
      const entries = Object.entries(values).filter(function (entry) {
        return isNumber(entry[1]);
      });
      if (entries.length) {
        addSectionHeading(nodes.decisionContent, "PROBABILITIES");
        const probabilitiesNode = makeElement("div", "probability-list");
        entries
          .sort(function (left, right) { return right[1] - left[1]; })
          .forEach(function (entry) {
            const row = makeElement("div", "probability-row");
            const label = makeElement("span", "probability-label", entry[0]);
            const value = makeElement("span", "probability-value", formatPercent(entry[1]) || "-");
            const track = makeElement("span", "probability-track");
            const fill = makeElement("span", "probability-fill");
            fill.style.width = Math.max(0, Math.min(100, entry[1] * 100)) + "%";
            track.append(fill);
            row.append(label, track, value);
            probabilitiesNode.append(row);
          });
        nodes.decisionContent.append(probabilitiesNode);
      }
    }

    function renderHistory() {
      clear(nodes.history);
      if (!state.history.length) {
        nodes.history.append(makeElement("p", "empty-state", "NO DECISIONS YET"));
        return;
      }

      state.history.slice(0, 5).forEach(function (entry, index) {
        const row = makeElement("button", "history-row", "");
        row.type = "button";
        row.append(makeElement("span", "history-turn", "T" + entry.turn));
        row.append(makeElement("span", "history-action", entry.label || entry.chosenId));
        row.append(makeElement("span", "history-confidence", entry.confidence || "-"));
        row.append(makeElement("span", "history-latency", entry.latency || "-"));
        row.append(makeElement("span", "history-status " + (entry.isFallback ? "fallback" : "accepted"), entry.isFallback ? "FALLBACK" : "ACCEPTED"));
        row.addEventListener("click", function () {
          state.inspectorSelection = entry;
          state.inspectorOpen = true;
          render();
        });
        nodes.history.append(row);
      });
    }

    function renderTruth() {
      const current = state.current;
      let legal = "WAITING";
      let submitted = "WAITING";
      let observed = "AWAITING SHOWDOWN";
      if (current.validation) {
        legal = current.validation.is_fallback ? "FALLBACK USED" : "ACCEPTED";
      }
      if (current.order) {
        submitted = current.order.message || "SUBMITTED";
      }
      if (current.phase === "RESULT_OBSERVED" || state.battleEnded) {
        observed = "RESULT OBSERVED";
      }
      setText(nodes.truthLegal, legal);
      setText(nodes.truthSubmitted, submitted);
      setText(nodes.truthObserved, observed);
      if (nodes.truth) nodes.truth.dataset.phase = current.phase;
    }

    function renderInspector() {
      if (!nodes.inspectDrawer) return;
      nodes.inspectDrawer.hidden = !state.inspectorOpen;
      if (nodes.inspectButton) {
        nodes.inspectButton.setAttribute("aria-expanded", state.inspectorOpen ? "true" : "false");
      }
      if (!state.inspectorOpen) return;

      clear(nodes.inspectContent);
      const input = state.current.input || {};
      const decision = state.current.decision || {};
      addJSON(nodes.inspectContent, "CURRENT SNAPSHOT", input.snapshot);
      addJSON(nodes.inspectContent, "JEV REQUEST", input.requestPayload);
      addJSON(nodes.inspectContent, "QUESTION / CRITERIA", {
        question: input.question,
        criteria: input.criteria,
      });
      addJSON(nodes.inspectContent, "JEV RESPONSE", decision.jevResponse || decision.jev);
      addJSON(nodes.inspectContent, "VALIDATION", state.current.validation);
      addJSON(nodes.inspectContent, "SUBMITTED ORDER", state.current.order);
      addJSON(nodes.inspectContent, "SELECTED HISTORY ENTRY", state.inspectorSelection);
      addJSON(nodes.inspectContent, "RECENT SHOWDOWN FRAMES", state.recentFrames);
      if (!nodes.inspectContent.firstChild) {
        nodes.inspectContent.append(makeElement("p", "empty-state", "NO TECHNICAL DATA YET"));
      }
    }

    function render() {
      renderHeader();
      renderInput();
      renderDecision();
      renderHistory();
      renderTruth();
      renderInspector();
    }

    function replaceCurrentForDecision(message) {
      if (state.current.decisionId !== message.decision_id) {
        state.current = {
          decisionId: message.decision_id || null,
          turn: message.turn || null,
          phase: message.phase || "IDLE",
          input: null,
          decision: null,
          validation: null,
          order: null,
          observedCommands: [],
        };
      } else {
        state.current.phase = message.phase || state.current.phase;
        state.current.turn = message.turn || state.current.turn;
      }
    }

    function mergeInput(message) {
      const input = state.current.input || {
        snapshot: null,
        criteria: null,
        question: null,
        requestPayload: null,
      };
      if (message.snapshot !== undefined) input.snapshot = message.snapshot;
      if (message.criteria !== undefined) input.criteria = message.criteria;
      if (message.question !== undefined) input.question = message.question;
      if (message.request_payload !== undefined) input.requestPayload = message.request_payload;
      state.current.input = input;
    }

    function handleDecisionPhase(message) {
      replaceCurrentForDecision(message);
      if (message.phase === "CALCULATING" || message.phase === "JEV_EVALUATING") {
        mergeInput(message);
      }
      if (message.phase === "LEGAL") {
        state.current.validation = message.validation || null;
        if (message.is_fallback) {
          state.current.validation = Object.assign({}, state.current.validation || {}, {
            is_fallback: true,
            fallback_reason: message.fallback_reason || null,
          });
        }
      }
      if (message.phase === "ORDER_SUBMITTED" || message.phase === "AWAITING_SHOWDOWN") {
        state.current.order = message.submitted_order || state.current.order;
      }
      if (message.phase === "RESULT_OBSERVED") {
        state.current.observedCommands = Array.isArray(message.observed_commands)
          ? message.observed_commands.slice()
          : [];
      }
      render();
    }

    function handleTurnDecision(message) {
      replaceCurrentForDecision(message);
      state.current.phase = state.current.phase === "JEV_EVALUATING"
        ? "LEGAL"
        : state.current.phase;
      state.current.input = {
        snapshot: message.snapshot || null,
        criteria: message.criteria || null,
        question: message.question || null,
        requestPayload: message.jev_request || null,
      };
      state.current.decision = {
        chosenId: message.chosen_id,
        label: message.label,
        kind: message.kind,
        isFallback: Boolean(message.is_fallback),
        fallbackReason: message.fallback_reason || null,
        jev: message.jev || {},
        jevResponse: message.jev_response || null,
      };
      state.current.validation = message.validation || null;
      state.current.order = message.submitted_order || null;
      const entry = {
        decisionId: message.decision_id || null,
        turn: message.turn,
        chosenId: message.chosen_id,
        label: message.label,
        confidence: message.is_fallback ? null : formatPercent(message.jev && message.jev.confidence),
        latency: formatLatency(message.jev && message.jev.latency_ms),
        isFallback: Boolean(message.is_fallback),
        fallbackReason: message.fallback_reason || null,
        decision: state.current.decision,
        input: state.current.input,
        validation: state.current.validation,
        order: state.current.order,
      };
      state.history = [entry].concat(state.history.filter(function (item) {
        return item.decisionId !== entry.decisionId;
      })).slice(0, 5);
      render();
    }

    function markObserved(commands) {
      if (!commands.length) return;
      if (state.current.phase === "AWAITING_SHOWDOWN") {
        state.current.phase = "RESULT_OBSERVED";
        state.current.observedCommands = commands.slice();
        render();
      }
    }

    function handleBattleFrame(message) {
      if (message.battle_tag && !state.battleTag) state.battleTag = message.battle_tag;
      const lines = Array.isArray(message.lines) ? message.lines.slice() : [];
      if (lines.length) {
        state.recentFrames = state.recentFrames.concat([lines]).slice(-80);
      }
      try {
        if (renderer && typeof renderer.feed === "function") renderer.feed(lines);
      } catch (error) {
        failRenderer(error);
      }
      const summary = summarizeProtocolLines(lines);
      markObserved(summary.observed);
      render();
    }

    function handleBattleStart(message) {
      state.battleTag = message.battle_tag || null;
      state.battleFormat = message.battle_format || "gen9randombattle";
      state.battleEnded = false;
      state.history = [];
      state.recentFrames = [];
      state.inspectorSelection = null;
      state.current = {
        decisionId: null,
        turn: null,
        phase: "IDLE",
        input: null,
        decision: null,
        validation: null,
        order: null,
        observedCommands: [],
      };
      try {
        if (renderer && typeof renderer.reset === "function") renderer.reset(state.battleTag);
      } catch (error) {
        failRenderer(error);
      }
      render();
    }

    function handleBattleReplay(message) {
      if (message.battle_tag && state.battleTag !== message.battle_tag) {
        state.battleTag = message.battle_tag;
        state.battleEnded = false;
        try {
          if (renderer && typeof renderer.reset === "function") renderer.reset(state.battleTag);
        } catch (error) {
          failRenderer(error);
        }
      }
      const frames = Array.isArray(message.frames) ? message.frames : [];
      frames.forEach(function (lines) {
        handleBattleFrame({
          type: "BATTLE_FRAME",
          battle_tag: message.battle_tag,
          lines,
        });
      });
      render();
    }

    function handleBattleEnd(message) {
      state.battleEnded = true;
      if (message.battle_tag) state.battleTag = message.battle_tag;
      if (state.current.order) state.current.phase = "RESULT_OBSERVED";
      try {
        if (renderer && typeof renderer.end === "function") renderer.end();
      } catch (error) {
        failRenderer(error);
      }
      render();
    }

    function handleStatus(message) {
      state.status = {
        text: typeof message.status === "string" ? message.status : "STATUS",
        busy: Boolean(message.busy),
        error: Boolean(message.error),
      };
      render();
    }

    function handleMessage(message) {
      if (!message || typeof message.type !== "string") return;
      switch (message.type) {
        case "STATUS_UPDATE":
          handleStatus(message);
          break;
        case "BATTLE_START":
          handleBattleStart(message);
          break;
        case "DECISION_PHASE":
          handleDecisionPhase(message);
          break;
        case "TURN_DECISION":
          handleTurnDecision(message);
          break;
        case "BATTLE_FRAME":
          handleBattleFrame(message);
          break;
        case "BATTLE_REPLAY":
          handleBattleReplay(message);
          break;
        case "BATTLE_END":
          handleBattleEnd(message);
          break;
        default:
          break;
      }
    }

    function failRenderer(error) {
      state.renderer.failed = true;
      if (nodes.arena) nodes.arena.classList.add("renderer-unavailable");
      if (nodes.rendererFallback) {
        nodes.rendererFallback.hidden = false;
        setText(nodes.rendererFallback, "OFFICIAL SHOWDOWN RENDERER UNAVAILABLE - TELEMETRY FALLBACK ACTIVE");
      }
      try {
        if (renderer && typeof renderer.setUnavailable === "function") {
          renderer.setUnavailable("OFFICIAL SHOWDOWN RENDERER UNAVAILABLE - TELEMETRY FALLBACK ACTIVE");
        }
      } catch (ignored) {
        void ignored;
      }
      render();
      return error;
    }

    function mountRenderer() {
      if (!renderer || typeof renderer.mount !== "function") {
        failRenderer(new Error("Showdown renderer adapter missing"));
        return;
      }
      try {
        Promise.resolve(renderer.mount(nodes.frame, nodes.log, nodes.sceneStatus))
          .then(function () {
            state.renderer.mounted = true;
            render();
          })
          .catch(failRenderer);
      } catch (error) {
        failRenderer(error);
      }
    }

    function websocketUrl() {
      const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
      return scheme + "//" + window.location.host + "/ws";
    }

    function scheduleReconnect() {
      if (destroyed || reconnectTimer !== null) return;
      reconnectTimer = window.setTimeout(function () {
        reconnectTimer = null;
        connect();
      }, 1500);
    }

    function connect() {
      if (destroyed || !WebSocketImpl) {
        state.socket = "closed";
        render();
        return;
      }
      state.socket = reconnectTimer === null ? "connecting" : "reconnecting";
      render();
      try {
        socket = new WebSocketImpl(websocketUrl());
      } catch (error) {
        state.socket = "reconnecting";
        render();
        scheduleReconnect();
        return;
      }
      socket.onopen = function () {
        state.socket = "open";
        render();
      };
      socket.onmessage = function (event) {
        try {
          const message = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
          handleMessage(message);
        } catch (error) {
          void error;
        }
      };
      socket.onerror = function () {
        state.socket = "reconnecting";
        render();
      };
      socket.onclose = function () {
        state.socket = "reconnecting";
        render();
        scheduleReconnect();
      };
    }

    function sendStart() {
      if (!socket || state.socket !== "open" || typeof socket.send !== "function") return;
      socket.send(JSON.stringify({ action: "START_BATTLE" }));
    }

    if (nodes.start) nodes.start.addEventListener("click", sendStart);
    if (nodes.inspectButton) {
      nodes.inspectButton.addEventListener("click", function () {
        state.inspectorOpen = true;
        render();
      });
    }
    if (nodes.inspectClose) {
      nodes.inspectClose.addEventListener("click", function () {
        state.inspectorOpen = false;
        render();
      });
    }

    render();
    mountRenderer();
    connect();

    return {
      state,
      handleMessage,
      render,
      destroy: function () {
        destroyed = true;
        if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
        if (socket && typeof socket.close === "function") socket.close();
      },
    };
  }

  window.JevDashboard = {
    create: createDashboardApp,
    summarizeProtocolLines,
  };

  function boot() {
    window.JevDashboard.create();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
