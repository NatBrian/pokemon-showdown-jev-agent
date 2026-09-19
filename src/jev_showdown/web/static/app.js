/* ============================================================
   AUTONOMOUS POKÉMON BATTLE AGENT — Dashboard client
   Connects to the FastAPI WebSocket hub at /ws and renders
   live battle telemetry, Jev decisions and end-game state.

   Expected server messages (JSON):
     { type: "STATUS_UPDATE",  status: "..." }
     { type: "TURN_DECISION",  turn, snapshot, criteria,
       jev_response | jev, validation, recent_history, ... }
     { type: "BATTLE_END",     won, total_turns, winner, ... }
   ============================================================ */
"use strict";

/* ---------------- State ---------------- */

const state = {
  ws: null,
  connected: false,
  battleActive: false,
  inspect: { state: null, question: null, response: null },
  inspectTab: "state",
  inspectExpanded: false,
  historyExpanded: false,
  lastTurn: 0,
};

/* ---------------- DOM helpers ---------------- */

function $(id) { return document.getElementById(id); }

function setText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
}

function clearEl(el) { while (el.firstChild) el.removeChild(el.firstChild); }

function makeEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text != null) el.textContent = text;
  return el;
}

function fmtPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  return Math.round(Number(value) * 100) + "%";
}

function fmtLatency(ms) {
  if (ms == null || Number.isNaN(Number(ms))) return "--";
  return Math.round(Number(ms));
}

function hpClass(fraction) {
  if (fraction > 0.5) return "hp-full";
  if (fraction > 0.2) return "hp-mid";
  return "hp-low";
}

/* ---------------- Pokémon sprites & type tags ---------------- */

const TYPE_CLASS = {
  NORMAL: "normal", FIRE: "fire", WATER: "water", ELECTRIC: "electric",
  GRASS: "grass", ICE: "ice", FIGHTING: "fighting", POISON: "poison",
  GROUND: "ground", FLYING: "flying", PSYCHIC: "psychic", BUG: "bug",
  ROCK: "rock", GHOST: "ghost", DRAGON: "dragon", DARK: "dark",
  STEEL: "steel", FAIRY: "fairy",
};

function speciesSlug(species) {
  return String(species || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function frontSpriteUrl(species) {
  const slug = speciesSlug(species);
  return slug
    ? "https://img.pokemondb.net/sprites/black-white/anim/normal/" + slug + ".gif"
    : "";
}

function initials(species) {
  const s = String(species || "??").trim();
  return s.length <= 2 ? s.toUpperCase() : s.slice(0, 2).toUpperCase();
}

function showSprite(imgEl, avatarEl, url, species) {
  if (url) {
    avatarEl.style.display = "none";
    imgEl.style.display = "";
    imgEl.src = url;
    // If the sprite 404s, hide it and reveal the initials avatar fallback.
    imgEl.onerror = () => {
      imgEl.style.display = "none";
      avatarEl.style.display = "";
      avatarEl.textContent = initials(species);
    };
  } else {
    imgEl.style.display = "none";
    avatarEl.style.display = "";
    avatarEl.textContent = initials(species);
  }
}

function humanizeFormat(format) {
  let s = String(format || "").replace(/_/g, " ").trim();
  s = s.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
  s = s.replace(/([A-Za-z])(\d)/g, "$1 $2");
  s = s.replace(/(\d)([A-Za-z])/g, "$1 $2");
  // All-lowercase concatenated ids (e.g. "gen9randombattle") get a light
  // dictionary split on common battle-format words.
  const WORDS = [
    "random", "battle", "gen", "double", "triple", "single", "suspect",
    "ubers", "ultra", "national", "dex", "limited", "stadium", "custom",
    "sketchy", "veteran", "beginner", "advanced", "middle",
  ];
  WORDS.forEach((w) => {
    s = s.replace(new RegExp("(^|\\s)(" + w + ")([a-z0-9])", "gi"), "$1$2 $3");
  });
  return s.replace(/\s+/g, " ").toUpperCase();
}

function makeTypeTags(types) {
  const wrap = document.createElement("div");
  wrap.className = "type-tags";
  fillTypeTags(wrap, types);
  return wrap;
}

function fillTypeTags(container, types) {
  clearEl(container);
  (types || []).forEach((t) => {
    if (!t) return;
    const cls = TYPE_CLASS[String(t).toUpperCase()] || "";
    container.appendChild(makeEl("span", "type-tag" + (cls ? " type-" + cls : ""), String(t).toUpperCase()));
  });
}

/* ---------------- WebSocket lifecycle ---------------- */

function connectSocket() {
  if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) {
    return;
  }
  try {
    state.ws = new WebSocket("ws://" + window.location.host + "/ws");
  } catch (err) {
    scheduleReconnect();
    return;
  }

  state.ws.onopen = () => {
    state.connected = true;
    console.log("[jev-dashboard] Connected to Jev WebSocket hub");
    if (!state.battleActive) {
      setStartButton("START JEV BATTLE", false);
      setStatusLeft("CONNECTED TO TELEMETRY HUB | READY FOR SHOWDOWN BATTLE | SAME GAME. DEEPER INSIGHT.");
    }
  };

  state.ws.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.warn("[jev-dashboard] Non-JSON message ignored:", event.data);
      return;
    }
    dispatchMessage(data);
  };

  state.ws.onclose = () => {
    state.connected = false;
    if (!state.battleActive) setStartButton("RECONNECTING...", true);
    scheduleReconnect();
  };

  state.ws.onerror = () => {
    // onclose will follow; nothing extra to do.
  };
}

function scheduleReconnect() {
  setTimeout(() => {
    if (!state.connected) connectSocket();
  }, 1500);
}

function sendAction(action) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ action: action }));
    return true;
  }
  return false;
}

function dispatchMessage(data) {
  const type = data.type || data.event;
  if (type === "STATUS_UPDATE") {
    handleStatusUpdate(data);
  } else if (type === "TURN_DECISION") {
    handleTurnDecision(data);
  } else if (type === "BATTLE_END") {
    handleBattleEnd(data);
  } else if (data.turn != null && (data.jev || data.jev_response)) {
    // Tolerate turn payloads broadcast without an explicit type tag.
    handleTurnDecision(data);
  }
}

/* ---------------- Button / status helpers ---------------- */

function setStartButton(label, disabled) {
  const btn = $("start-btn");
  if (!btn) return;
  btn.textContent = label;
  btn.disabled = !!disabled;
}

function setStatusLeft(text) {
  setText("status-left", text);
}

/* ---------------- STATUS_UPDATE ---------------- */

function handleStatusUpdate(data) {
  const status = (data.status || data.message || "").toUpperCase();
  const btn = $("start-btn");
  if (data.error) {
    // Clear, unmistakable error state (connection/auth/search failure).
    state.battleActive = false;
    setStartButton("RETRY BATTLE", false);
    btn.classList.add("btn-error");
    setStatusLeft(status + " | SAME GAME. DEEPER INSIGHT.");
    // Back to idle in the Jev Output panel (no inference is in flight).
    setLoaderStep(0, null, false);
    return;
  }
  btn.classList.remove("btn-error");
  const busy = data.busy === undefined ? true : !!data.busy;
  if (busy) {
    state.battleActive = true;
    setStartButton(status || "CONNECTING...", true);
    // The only region that should visibly "wait" is Jev Output.
    setLoaderStep(1, "JEV PROCESSING...");
    setStatusLeft(status + " | AWAITING SHOWDOWN BATTLE");
  } else {
    state.battleActive = false;
    // Back in the idle state: one clear button again.
    setStartButton("START JEV BATTLE", false);
    setStatusLeft(status === "READY"
      ? "READY FOR SHOWDOWN BATTLE | SAME GAME. DEEPER INSIGHT."
      : (status || "READY") + " | SAME GAME. DEEPER INSIGHT.");
  }
}

function onStartBattleClick() {
  if (state.battleActive) return;
  setStartButton("CONNECTING...", true);
  const sent = sendAction("START_BATTLE");
  if (!sent) {
    setStartButton("OFFLINE — RETRY", true);
    scheduleReconnect();
  }
}

/* ---------------- TURN_DECISION ---------------- */

function handleTurnDecision(data) {
  state.battleActive = true;

  const turn = data.turn != null ? data.turn
    : (data.snapshot && data.snapshot.turn != null ? data.snapshot.turn : state.lastTurn);
  const snapshot = data.snapshot || data.state || null;
  const criteria = data.criteria || data.question || {};
  const jev = data.jev_response || data.jev || {};
  const validation = data.validation || {
    chosen_id: data.chosen_id || jev.choice || null,
    is_fallback: !!data.is_fallback,
    fallback_reason: data.fallback_reason || null,
  };
  const chosenId = validation.chosen_id || jev.choice || data.chosen_id || null;
  const recentHistory = data.recent_history || [];
  const latency = fmtLatency(jev.latency_ms);
  if (turn != null) state.lastTurn = turn;

  // Header latency badge
  setText("latency-badge", "⚡ LATENCY " + (latency === "--" ? "--" : latency) + " MS");

  // Left panel: live battle
  if (snapshot) {
    renderTurnBadge(turn);
    renderBattleContext(snapshot);
    renderActiveMons(snapshot);
    renderTeams(snapshot);
    renderBattlePrompt(snapshot);
  } else if (turn != null) {
    renderTurnBadge(turn);
  }

  // Center panel: Jev input
  renderCenterPanel(snapshot, criteria, chosenId, turn);

  // Right panel: Jev output
  renderRightPanel(jev, validation, chosenId, snapshot, latency);

  // Turn history
  renderHistory(recentHistory);

  // Bottom action strip
  renderActionStrip(chosenId, snapshot, criteria, latency, validation);

  // Status bar
  renderStatusBar(turn, chosenId, latency, snapshot);

  // Inspect data
  state.inspect.state = snapshot || null;
  state.inspect.question = Object.keys(criteria).length ? criteria : null;
  state.inspect.response = Object.keys(jev).length ? jev : null;
  renderInspect();

  // Fallback alert banner (adapter attribution)
  const banner = $("fallback-banner");
  const actionLine = $("fallback-action-line");
  if (validation.is_fallback) {
    banner.classList.remove("hidden");
    const reason = validation.fallback_reason ? " (" + validation.fallback_reason + ")" : "";
    setText("fallback-banner-text", "JEV FAILED — FALLBACK USED" + reason);
    if (actionLine) {
      actionLine.textContent = "FALLBACK ACTION: " + (chosenId ? String(chosenId).toUpperCase() : "N/A");
    }
  } else {
    banner.classList.add("hidden");
  }

  // The battle is live: the button shows the observable playing state.
  if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
    setStartButton("START JEV BATTLE", false);
  } else {
    setStartButton("JEV PLAYING", true);
  }
}

function renderTurnBadge(turn) {
  setText("turn-badge", "TURN " + (turn != null ? turn : "--"));
}

function renderBattleContext(snapshot) {
  const format = snapshot.battle_format;
  if (format) {
    setText("format-label", humanizeFormat(format));
  }
  const weather = snapshot.weather ? String(snapshot.weather).toUpperCase() : "NONE";
  const fields = Array.isArray(snapshot.fields) && snapshot.fields.length
    ? snapshot.fields.map((f) => String(f).toUpperCase()).join(", ")
    : "NONE";
  setText("weather-label", weather);
  setText("terrain-label", fields);
}

function fmtHpLine(mon) {
  // Prefer exact values when the protocol provides them ("HP 261 / 344"),
  // fall back to a percentage otherwise.
  if (mon && mon.hp != null && mon.max_hp) {
    return {
      bar: mon.max_hp > 0 ? mon.hp / mon.max_hp : 1.0,
      text: Math.round(mon.hp) + " / " + Math.round(mon.max_hp),
      pct: fmtPct(mon.hp / mon.max_hp),
    };
  }
  const frac = mon && mon.hp_fraction != null ? Number(mon.hp_fraction) : 1.0;
  return { bar: frac, text: fmtPct(frac), pct: fmtPct(frac) };
}

function renderHpCard(prefix, mon) {
  if (!mon) return;
  const info = fmtHpLine(mon);
  const bar = $(prefix + "-hp-bar");
  bar.style.width = Math.max(0, Math.min(100, info.bar * 100)) + "%";
  bar.className = "hp-fill " + hpClass(info.bar);
  const textEl = $(prefix + "-hp-text");
  textEl.textContent = info.text;
  textEl.title = info.pct;
}

function renderActiveMons(snapshot) {
  const selfMon = snapshot.self && snapshot.self.active_pokemon;
  const oppMon = snapshot.opponent && snapshot.opponent.active_pokemon;

  if (selfMon) {
    setText("self-name", selfMon.species || "---");
    renderHpCard("self", selfMon);
    fillTypeTags($("self-types"), selfMon.types);
    renderMonStatus("self-status", selfMon.status);
    if (selfMon.level != null) setText("self-level", "Lv. " + selfMon.level);
    showSprite($("self-sprite"), $("self-avatar"), frontSpriteUrl(selfMon.species), selfMon.species);
  }

  if (oppMon) {
    setText("opp-name", oppMon.species || "???");
    renderHpCard("opp", oppMon);
    fillTypeTags($("opp-types"), oppMon.types);
    renderMonStatus("opp-status", oppMon.status);
    if (oppMon.level != null) setText("opp-level", "Lv. " + oppMon.level);
    showSprite($("opp-sprite"), $("opp-avatar"), frontSpriteUrl(oppMon.species), oppMon.species);
  }
}

function renderMonStatus(id, status) {
  const el = $(id);
  if (!el) return;
  if (status) {
    el.textContent = String(status).toUpperCase();
    el.classList.remove("hidden");
  } else {
    el.classList.add("hidden");
  }
}

function renderBattlePrompt(snapshot) {
  const selfMon = snapshot.self && snapshot.self.active_pokemon;
  if (selfMon && selfMon.species) {
    setText("prompt-label", "What will " + selfMon.species + " do?");
  }
}

/* Fog-of-war team rows */

function renderInitialTeams() {
  // Pre-populate 6 slots per side so the arena reads complete before the
  // first telemetry frame arrives. Opponent slots stay closed Poké Balls
  // (fog of war); player slots read as open until Showdown reveals the team.
  const oppSlots = $("opp-team-slots");
  clearEl(oppSlots);
  for (let i = 0; i < 6; i++) {
    const el = makeEl("div", "team-slot unknown");
    el.appendChild(makeEl("div", "pokeball-mini"));
    el.appendChild(makeEl("span", "slot-name", "?"));
    el.title = "Unrevealed Poké Ball — fog of war";
    oppSlots.appendChild(el);
  }
  const selfSlots = $("self-team-slots");
  clearEl(selfSlots);
  for (let i = 0; i < 6; i++) {
    const el = makeEl("div", "team-slot empty");
    el.appendChild(makeEl("span", "slot-name", "\u00B7"));
    el.title = "Awaiting team data";
    selfSlots.appendChild(el);
  }
}

function renderTeams(snapshot) {
  const oppSlots = $("opp-team-slots");
  clearEl(oppSlots);
  const slots = snapshot.opponent && Array.isArray(snapshot.opponent.team_slots)
    ? snapshot.opponent.team_slots
    : [];
  for (let i = 0; i < 6; i++) {
    const slot = slots[i] || { revealed: false, species: null, fainted: false };
    const el = makeEl("div", "team-slot");
    if (slot.revealed && slot.species) {
      el.classList.add("revealed");
      if (slot.fainted) el.classList.add("fainted");
      const img = document.createElement("img");
      img.className = "slot-img";
      img.alt = String(slot.species);
      img.src = frontSpriteUrl(slot.species);
      img.onerror = () => img.remove();
      el.appendChild(img);
      el.appendChild(makeEl("span", "slot-name", initials(slot.species)));
      el.title = String(slot.species) + (slot.fainted ? " (fainted)" : "");
    } else {
      el.classList.add("unknown");
      el.appendChild(makeEl("div", "pokeball-mini"));
      el.appendChild(makeEl("span", "slot-name", "?"));
      el.title = "Unrevealed Poké Ball — fog of war";
    }
    oppSlots.appendChild(el);
  }

  const selfSlots = $("self-team-slots");
  clearEl(selfSlots);
  const team = snapshot.self && Array.isArray(snapshot.self.team) ? snapshot.self.team : [];
  const activeSpecies = snapshot.self && snapshot.self.active_pokemon
    ? snapshot.self.active_pokemon.species
    : null;
  for (let i = 0; i < 6; i++) {
    const mon = team[i];
    const el = makeEl("div", "team-slot");
    if (mon && mon.species) {
      el.classList.add("revealed");
      if (mon.fainted) el.classList.add("fainted");
      if (mon.species === activeSpecies) el.classList.add("active");
      const img = document.createElement("img");
      img.className = "slot-img";
      img.alt = String(mon.species);
      img.src = frontSpriteUrl(mon.species);
      img.onerror = () => img.remove();
      el.appendChild(img);
      el.appendChild(makeEl("span", "slot-name", initials(mon.species)));
      el.title = String(mon.species) +
        (mon.fainted ? " (fainted)" : " (HP " + fmtPct(mon.hp_fraction != null ? mon.hp_fraction : 1.0) + ")");
    } else {
      el.classList.add("empty");
      el.appendChild(makeEl("span", "slot-name", "·"));
      el.title = "Open team slot";
    }
    selfSlots.appendChild(el);
  }
}

/* ---------------- Center panel: Jev Input ---------------- */

function renderCenterPanel(snapshot, criteria, chosenId, turn) {
  const stateEl = $("state-summary");
  clearEl(stateEl);
  if (snapshot) {
    const selfMon = snapshot.self && snapshot.self.active_pokemon;
    const oppMon = snapshot.opponent && snapshot.opponent.active_pokemon;
    const selfName = selfMon ? selfMon.species : "???";
    const oppName = oppMon ? oppMon.species : "???";
    const selfHp = selfMon ? fmtPct(selfMon.hp_fraction) : "--";
    const oppHp = oppMon ? fmtPct(oppMon.hp_fraction) : "--";
    const kv = (label, value) => {
      const line = makeEl("span", "kv");
      const b = makeEl("b", "", label + ": ");
      line.appendChild(b);
      line.appendChild(document.createTextNode(String(value)));
      return line;
    };
    stateEl.appendChild(kv("TURN", turn != null ? turn : snapshot.turn));
    stateEl.appendChild(kv("ACTIVE", String(selfName) + " (" + selfHp + ")"));
    stateEl.appendChild(kv("OPPOS", String(oppName) + " (" + oppHp + ")"));
    if (selfMon && selfMon.status) stateEl.appendChild(kv("STATUS", selfMon.status));
    if (oppMon && oppMon.status) stateEl.appendChild(kv("OPP STATUS", oppMon.status));
  } else {
    stateEl.appendChild(makeEl("span", "empty-note", "NO BATTLE STATE RECEIVED"));
  }

  const fieldEl = $("field-summary");
  clearEl(fieldEl);
  if (snapshot) {
    const weather = snapshot.weather ? String(snapshot.weather).toUpperCase() : "NONE";
    const terrain = Array.isArray(snapshot.fields) && snapshot.fields.length
      ? snapshot.fields.map((f) => String(f).toUpperCase()).join(", ")
      : "NONE";
    const tera = snapshot.can_tera ? "AVAILABLE" : "UNAVAILABLE";
    fieldEl.appendChild(document.createTextNode("WEATHER: " + weather + " | TERRAIN: " + terrain + " | TERA: " + tera));
  } else {
    fieldEl.appendChild(makeEl("span", "empty-note", "UNKNOWN"));
  }

  renderFacts(snapshot, criteria, chosenId);
  renderLegalActions(snapshot, criteria, chosenId);
}

function renderFacts(snapshot, criteria, chosenId) {
  const el = $("facts-summary");
  clearEl(el);
  if (!snapshot || !chosenId) {
    el.appendChild(makeEl("span", "empty-note", "NO FACTS CALCULATED YET"));
    return;
  }
  const legal = Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions : [];
  const chosen = legal.find((a) => a.id === chosenId) || null;
  const facts = (chosen && chosen.facts) || {};
  const crit = criteria[chosenId] || null;

  const chip = (label, value, sub, tone) => {
    const c = makeEl("div", "fact-chip" + (tone ? " " + tone : ""));
    c.appendChild(makeEl("span", "fact-label", label));
    c.appendChild(makeEl("span", "fact-value", value));
    if (sub) c.appendChild(makeEl("span", "fact-sub", sub));
    return c;
  };

  const mult = facts.type_multiplier;
  if (mult != null) {
    const tone = mult > 1 ? "good" : mult < 1 ? "bad" : null;
    const oppTypes = snapshot.opponent && snapshot.opponent.active_pokemon && snapshot.opponent.active_pokemon.types
      ? snapshot.opponent.active_pokemon.types.join("/")
      : "opponent";
    el.appendChild(chip(
      String(facts.type || "TYPE").toUpperCase() + " EFFECTIVENESS",
      Number(mult).toFixed(mult % 1 ? 1 : 0) + "\u00D7",
      "vs " + oppTypes,
      tone,
    ));
  }
  if (Array.isArray(facts.estimated_damage_range) && facts.estimated_damage_range.length === 2) {
    el.appendChild(chip("EST. DAMAGE", facts.estimated_damage_range[0] + "–" + facts.estimated_damage_range[1] + "%", "deterministic estimate"));
  }
  if (facts.estimated_ko != null) {
    el.appendChild(chip("KO CHECK", facts.estimated_ko ? "LIKELY KO" : "NOT GUARANTEED", facts.estimated_ko ? "target down" : "target survives", facts.estimated_ko ? "good" : null));
  }
  if (facts.priority != null) {
    el.appendChild(chip("PRIORITY", String(facts.priority), "move priority"));
  }
  if (facts.base_power != null) {
    el.appendChild(chip("BASE POWER", String(facts.base_power), String(facts.category || "") + (facts.accuracy != null ? " | ACC " + facts.accuracy : "")));
  }
  if (chosen && chosen.kind) {
    el.appendChild(chip("ACTION KIND", String(chosen.kind).toUpperCase(), chosen.label || ""));
  }
  if (crit) {
    const c = makeEl("div", "fact-chip");
    c.style.gridColumn = "1 / -1";
    c.appendChild(makeEl("span", "fact-label", "HARNESS CRITERIA"));
    c.appendChild(makeEl("span", "fact-sub", crit));
    el.appendChild(c);
  }
  if (!el.hasChildNodes()) {
    el.appendChild(makeEl("span", "empty-note", "NO FACTS FOR SELECTED ACTION"));
  }
}

function kindIcon(kind) {
  if (kind === "move") return "\u25B2";
  if (kind === "move_tera") return "\u2605";
  if (kind === "switch") return "\u21C4";
  return "\u2022";
}

function renderLegalActions(snapshot, criteria, chosenId) {
  const list = $("legal-actions-list");
  clearEl(list);
  const title = $("legal-actions-title");
  const legal = snapshot && Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions : [];
  title.textContent = "LEGAL ACTIONS (" + legal.length + ")";
  if (!legal.length) {
    list.appendChild(makeEl("span", "empty-note", "NO LEGAL ACTIONS YET"));
    return;
  }
  legal.forEach((action) => {
    const row = makeEl("div", "action-row");
    if (action.id === chosenId) row.classList.add("selected");
    const icon = makeEl("span", "a-icon kind-" + (action.kind || "move"), kindIcon(action.kind));
    const body = makeEl("div", "a-body");
    body.appendChild(makeEl("span", "a-id", (action.label || action.id || "").toUpperCase()));
    const desc = criteria[action.id] || "";
    body.appendChild(makeEl("span", "a-desc", desc));
    row.appendChild(icon);
    row.appendChild(body);
    const factType = action.facts && action.facts.type;
    if (factType) {
      const tag = makeEl("span", "a-type", "");
      tag.appendChild(makeTypeTags([factType]).children[0]);
      row.appendChild(tag);
    }
    list.appendChild(row);
  });
}

/* ---------------- Right panel: Jev Output ---------------- */

function setLoaderStep(step, title, done) {
  const spinner = document.querySelector("#processing-loader .arcade-spinner");
  const titleEl = $("loader-title");
  const items = document.querySelectorAll("#loader-checklist li");
  if (spinner) {
    spinner.classList.toggle("idle", !title);
    spinner.classList.toggle("done", !!done);
  }
  if (titleEl) {
    titleEl.textContent = title || "JEV IDLE";
    titleEl.classList.toggle("done", !!done);
  }
  items.forEach((li) => {
    const i = Number(li.getAttribute("data-step"));
    li.classList.remove("todo", "active", "done");
    if (done || i < step) li.classList.add("done");
    else if (i === step) li.classList.add("active");
    else li.classList.add("todo");
  });
}

function renderRightPanel(jev, validation, chosenId, snapshot, latency) {
  const isFallback = !!validation.is_fallback;
  const completed = !isFallback && chosenId != null;

  // Loader: inference is the only "meaningful wait"
  if (latency !== "--") {
    setLoaderStep(5, completed ? "API INFERENCE COMPLETE" : "FALLBACK ENGAGED", true);
    setText("loader-latency", "API INFERENCE " + latency + " MS");
  } else {
    setLoaderStep(3, "JEV ERROR — FALLBACK LADDER", true);
    setText("loader-latency", "API INFERENCE FAILED");
  }

  // Decision card
  setText("chosen-action", chosenId ? String(chosenId).toUpperCase() : (isFallback ? "FALLBACK ACTION" : "AWAITING DECISION"));
  const kindEl = $("chosen-kind");
  let kind = null;
  if (snapshot && Array.isArray(snapshot.legal_actions) && chosenId) {
    const legal = snapshot.legal_actions.find((a) => a.id === chosenId);
    if (legal) kind = legal.kind;
  }
  if (kind) {
    kindEl.textContent = String(kind).toUpperCase();
    kindEl.classList.remove("hidden");
  } else {
    kindEl.classList.add("hidden");
  }

  const confidence = jev && jev.confidence != null ? Number(jev.confidence) : null;
  setText("confidence-val", confidence != null ? Math.round(confidence * 100) + "%" : "--%");
  const confBar = $("confidence-bar");
  if (confBar) confBar.style.width = (confidence != null ? Math.max(0, Math.min(100, confidence * 100)) : 0) + "%";

  setText("decision-model", jev && jev.model ? "MODEL: " + String(jev.model).toUpperCase() : "MODEL: --");
  // Reported token usage and cost (observable model I/O, never invented).
  if (jev && (jev.input_tokens != null || jev.output_tokens != null || jev.cost != null)) {
    const tin = jev.input_tokens != null ? jev.input_tokens : "--";
    const tout = jev.output_tokens != null ? jev.output_tokens : "--";
    const cost = jev.cost != null ? String(jev.cost) : "0";
    setText("decision-usage", "IN " + tin + " \u2022 OUT " + tout + " \u2022 COST $" + cost);
  }
  const chip = $("decision-completed");
  chip.classList.toggle("hidden", !completed);

  // Probabilities bar chart
  renderProbabilities(jev, chosenId, snapshot);
}

function renderProbabilities(jev, chosenId, snapshot) {
  const container = $("prob-bars");
  clearEl(container);
  const probs = (jev && jev.probabilities) || {};
  const entries = Object.entries(probs);
  if (!entries.length) {
    container.appendChild(makeEl("span", "empty-note", "NO PROBABILITY DISTRIBUTION"));
    return;
  }
  const legal = snapshot && Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions : [];
  entries
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .forEach(([id, p]) => {
      const pct = Number.isFinite(Number(p)) ? Math.round(Number(p) * 100) : 0;
      const row = makeEl("div", "prob-bar-row");
      if (id === chosenId) row.classList.add("selected");

      const action = legal.find((a) => a.id === id);
      const factType = action && action.facts && action.facts.type;
      if (factType) {
        const typeWrap = makeEl("span", "p-type", "");
        typeWrap.appendChild(makeTypeTags([factType]).children[0]);
        row.appendChild(typeWrap);
      }
      row.appendChild(makeEl("span", "prob-label", String(id).toUpperCase()));
      const track = makeEl("div", "prob-track");
      const fill = makeEl("div", "prob-fill");
      fill.style.width = Math.max(0, Math.min(100, pct)) + "%";
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(makeEl("span", "prob-pct", pct + "%"));
      container.appendChild(row);
    });
}

/* ---------------- Turn history ---------------- */

function renderHistory(events) {
  const list = $("history-cards");
  clearEl(list);
  if (!events.length) {
    list.appendChild(makeEl("span", "empty-note", "NO EVENTS YET"));
    return;
  }
  // Most recent first so the newest action sits on top.
  events.slice().reverse().forEach((ev) => {
    const card = makeEl("div", "history-card");
    card.appendChild(makeEl("span", "h-turn", "TURN " + (ev.turn != null ? ev.turn : "?")));
    const actor = ev.actor ? String(ev.actor) + " " : "";
    const action = ev.action ? String(ev.action) : (ev.kind === "switch" ? "Switch" : "Action");
    card.appendChild(makeEl("span", "h-text", actor + action));
    const badges = makeEl("div", "h-badges");
    if (ev.damage_pct != null) badges.appendChild(makeEl("span", "h-badge dmg", "-" + ev.damage_pct + "%"));
    if (ev.status) badges.appendChild(makeEl("span", "h-badge status", String(ev.status).toUpperCase()));
    if (ev.kind === "switch" || (ev.action && /switch/i.test(String(ev.action)))) {
      badges.appendChild(makeEl("span", "h-badge switch", "SWITCH"));
    }
    if (ev.fainted) badges.appendChild(makeEl("span", "h-badge faint", "FAINT"));
    if (Array.isArray(ev.badges)) {
      ev.badges.forEach((b) => {
        badges.appendChild(makeEl("span", "h-badge stat", String(b)));
      });
    }
    if (ev.note) {
      const note = makeEl("span", "h-badge note", String(ev.note));
      note.title = String(ev.note);
      badges.appendChild(note);
    }
    card.appendChild(badges);
    list.appendChild(card);
  });
}

/* ---------------- Bottom action strip ---------------- */

function renderActionStrip(chosenId, snapshot, criteria, latency, validation) {
  const legal = snapshot && Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions : [];
  const chosen = legal.find((a) => a.id === chosenId) || null;
  const label = chosen ? (chosen.label || chosen.id) : (chosenId ? String(chosenId) : "ACTION");
  const facts = (chosen && chosen.facts) || {};
  const crit = criteria && criteria[chosenId] ? criteria[chosenId] : "";

  setText("validate-status", chosenId ? (validation && validation.is_fallback ? "FALLBACK VALIDATED" : "LEGAL ACTION") : "PENDING");
  setText(
    "validate-desc",
    chosenId
      ? label.toUpperCase() + " is a valid " + ((chosen && chosen.kind) || "action") + " in the current state."
      : "Validating Jev output against legal candidates...",
  );
  // Adapter validation is near-instant: show the measured time when known.
  const valMs = validation && validation.latency_ms != null ? Number(validation.latency_ms) : null;
  setText("validate-time", valMs != null && Number.isFinite(valMs) ? valMs.toFixed(2) + " MS" : "< 1 MS");

  setText("act-status", chosenId ? "SEND " + label.toUpperCase() : "STANDBY");
  setText("act-desc", "Execute action command and await game response");

  let damage = null;
  if (Array.isArray(facts.estimated_damage_range) && facts.estimated_damage_range.length === 2) {
    damage = facts.estimated_damage_range[0] + "–" + facts.estimated_damage_range[1] + "%";
  }
  const ko = facts.estimated_ko === true;
  setText("result-status", chosenId ? (damage ? damage + " DAMAGE" : "ACTION EXECUTED") : "PENDING");
  setText(
    "result-desc",
    chosenId
      ? (ko ? "TARGET LIKELY FAINED (next turn state computed)." : "TARGET SURVIVES (next turn state computed).")
      : "Next turn state...",
  );
  // Estimated remaining HP of the target after the chosen action.
  const hpWrap = $("result-hp-wrap");
  const oppMon = snapshot && snapshot.opponent && snapshot.opponent.active_pokemon;
  if (chosenId && Array.isArray(facts.estimated_damage_range) && facts.estimated_damage_range.length === 2) {
    const base = oppMon && oppMon.hp_fraction != null ? Number(oppMon.hp_fraction) * 100 : 100;
    const hi = Math.max(0, Math.round(base - facts.estimated_damage_range[0]));
    const lo = Math.max(0, Math.round(base - facts.estimated_damage_range[1]));
    const [low, high] = hi < lo ? [hi, lo] : [lo, hi];
    hpWrap.classList.remove("hidden");
    setText("result-hp-label", "HP \u2248 " + low + " \u2013 " + high + "%");
    const fill = $("result-hp-fill");
    fill.style.width = Math.max(2, (low + high) / 2) + "%";
    fill.className = "hp-fill " + hpClass((low + high) / 200);
  } else {
    hpWrap.classList.add("hidden");
  }
  // Small target sprite in the result panel.
  const resultSprite = $("result-sprite");
  clearEl(resultSprite);
  if (oppMon && oppMon.species) {
    const img = document.createElement("img");
    img.alt = "";
    img.src = frontSpriteUrl(oppMon.species);
    img.onerror = () => img.remove();
    resultSprite.appendChild(img);
  }
}

function renderStatusBar(turn, chosenId, latency, snapshot) {
  const legal = snapshot && Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions : [];
  const chosen = legal.find((a) => a.id === chosenId);
  const range = chosen && Array.isArray(chosen.facts.estimated_damage_range) && chosen.facts.estimated_damage_range.length === 2
    ? "Damage " + chosen.facts.estimated_damage_range[0] + "–" + chosen.facts.estimated_damage_range[1] + "%"
    : "Damage --";
  const target = chosen && chosen.facts.estimated_ko === true ? "Likely KO" : "Target survives";
  const parts = [
    "TURN " + (turn != null ? turn : "--"),
    "Jev chose " + (chosenId ? String(chosenId).toUpperCase() : "--"),
    latency !== "--" ? latency + " MS" : "-- MS",
    range,
    target,
    "Next turn state ready",
  ];
  setStatusLeft(parts.join(" | "));
}

/* ---------------- Inspect Data ---------------- */

function renderInspect() {
  const preview = $("inspect-preview");
  const box = $("inspect-content");
  const data = state.inspect[state.inspectTab];

  // Compact structured preview (never a wall of JSON by default)
  const snapshot = state.inspect.state;
  if (snapshot) {
    const turn = snapshot.turn != null ? snapshot.turn : (state.lastTurn || "--");
    const active = snapshot.self && snapshot.self.active_pokemon ? snapshot.self.active_pokemon.species : "---";
    const nLegal = Array.isArray(snapshot.legal_actions) ? snapshot.legal_actions.length : "--";
    preview.textContent = "TURN " + turn + " | ACTIVE: " + active + " | LEGAL ACTIONS " + nLegal;
  } else {
    preview.textContent = "TURN -- | ACTIVE: --- | LEGAL ACTIONS --";
  }

  if (state.inspectExpanded) {
    box.classList.remove("hidden");
    box.textContent = data == null
      ? "-- AWAITING DATA --"
      : JSON.stringify(data, null, 2);
  } else {
    box.classList.add("hidden");
  }
}

function switchTab(tab, btn) {
  state.inspectTab = tab;
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderInspect();
}

function toggleInspectExpand() {
  state.inspectExpanded = !state.inspectExpanded;
  const btn = $("inspect-expand");
  if (btn) btn.textContent = state.inspectExpanded ? "COLLAPSE \u25B4" : "EXPAND \u25BE";
  renderInspect();
}

function toggleHistoryExpand() {
  state.historyExpanded = !state.historyExpanded;
  const btn = $("history-expand");
  const list = $("history-cards");
  if (btn) btn.textContent = state.historyExpanded ? "COLLAPSE \u25B4" : "EXPAND \u25BE";
  if (list) list.classList.toggle("expanded", state.historyExpanded);
}

/* ---------------- BATTLE_END ---------------- */

function handleBattleEnd(data) {
  let won = data.won;
  if (won == null) {
    const hint = String(data.result || data.outcome || data.winner || "").toLowerCase();
    if (/win|victory|you/i.test(hint)) won = true;
    else if (/loss|defeat|opponent|enemy|lose/i.test(hint)) won = false;
  }

  const titleEl = $("end-title");
  const box = $("overlay-box");
  titleEl.classList.remove("victory-text", "defeat-text");
  box.classList.remove("victory", "defeat");

  if (won === true) {
    titleEl.textContent = "VICTORY";
    titleEl.classList.add("victory-text");
    box.classList.add("victory");
  } else if (won === false) {
    titleEl.textContent = "DEFEAT";
    titleEl.classList.add("defeat-text");
    box.classList.add("defeat");
  } else {
    titleEl.textContent = "BATTLE OVER";
  }

  const stats = [];
  if (data.total_turns != null || data.turns != null) {
    stats.push("COMPLETED IN " + (data.total_turns != null ? data.total_turns : data.turns) + " TURNS");
  }
  if (data.winner != null) stats.push("WINNER: " + String(data.winner).toUpperCase());
  if (data.battle_format) stats.push("FORMAT: " + humanizeFormat(data.battle_format));
  if (data.summary) stats.push(String(data.summary).toUpperCase());
  if (data.score != null) stats.push("RECORD: " + data.score);
  setText("end-stats", stats.length ? stats.join(" \u2022 ") : "BATTLE COMPLETED");

  $("end-overlay").classList.remove("hidden");

  // Reset for the next battle
  state.battleActive = false;
  setStartButton("START JEV BATTLE", false);
  setLoaderStep(0, null, false);
  setText("loader-latency", "API INFERENCE -- MS");
  if (data.total_turns != null) renderTurnBadge(data.total_turns);
  setStatusLeft(
    (won === true ? "VICTORY" : won === false ? "DEFEAT" : "BATTLE OVER") +
    " | " + (data.total_turns != null ? data.total_turns + " TURNS" : "") +
    " | SAME GAME. DEEPER INSIGHT.",
  );
}

function closeOverlay() {
  $("end-overlay").classList.add("hidden");
}

/* ---------------- Boot ---------------- */

document.addEventListener("DOMContentLoaded", () => {
  $("start-btn").addEventListener("click", onStartBattleClick);
  $("inspect-expand").addEventListener("click", toggleInspectExpand);
  $("history-expand").addEventListener("click", toggleHistoryExpand);
  $("end-dismiss").addEventListener("click", closeOverlay);

  // Idle state until the first telemetry arrives
  setLoaderStep(0, null, false);
  renderInitialTeams();
  connectSocket();
});
