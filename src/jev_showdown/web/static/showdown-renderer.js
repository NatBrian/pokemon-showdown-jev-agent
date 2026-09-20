/*
 * Official Pokémon Showdown battle-scene adapter.
 *
 * This file intentionally stays separate from app.js: it owns loading the
 * browser-global Showdown renderer and feeding it protocol lines. The
 * dashboard owns WebSocket message routing and Jev telemetry.
 */
(function () {
  "use strict";

  const LOCAL = "/static/showdown";
  const CDN_HOST = "play.pokemonshowdown.com";
  const BASE_WIDTH = 640;
  const BASE_HEIGHT = 380;
  const SCRIPTS = [
    "js/lib/ps-polyfill.js",
    "js/lib/jquery-1.11.0.min.js",
    "js/lib/html-sanitizer-minified.js",
    "js/battle-sound.js",
    "js/battledata.js",
    "data/pokedex-mini.js",
    "data/pokedex-mini-bw.js",
    "data/graphics.js",
    "data/pokedex.js",
    "data/moves.js",
    "data/abilities.js",
    "data/items.js",
    "js/battle-tooltips.js",
    "js/battle.js",
  ];

  let loadPromise = null;
  let battle = null;
  let frameElement = null;
  let logElement = null;
  let statusElement = null;
  let resizeObserver = null;
  let battleTag = "jev-showdown";
  let pendingLines = [];
  let battleEnded = false;

  function setStatus(text) {
    if (statusElement) statusElement.textContent = text;
  }

  function injectConfig() {
    window.Config = window.Config || {};
    window.Config.routes = window.Config.routes || {};
    // battledata.js adds the protocol itself before this host.
    window.Config.routes.client = CDN_HOST;
    window.Config.routes.client2 = CDN_HOST;
    window.Config.routes.dex = "www.smogon.com/dex/";
  }

  function loadScript(path) {
    const src = LOCAL + "/" + path;
    return new Promise(function (resolve, reject) {
      const existing = document.querySelector('script[src="' + src + '"]');
      if (existing) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.async = false;
      script.onload = resolve;
      script.onerror = function () {
        reject(new Error("Failed to load " + src));
      };
      document.head.appendChild(script);
    });
  }

  function loadStyle() {
    const href = LOCAL + "/style/battle.css";
    return new Promise(function (resolve) {
      const existing = document.querySelector('link[href="' + href + '"]');
      if (existing) {
        resolve();
        return;
      }
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      // A missing stylesheet should not block the dashboard fallback.
      link.onload = resolve;
      link.onerror = resolve;
      document.head.appendChild(link);
    });
  }

  function loadBundle() {
    if (loadPromise) return loadPromise;
    loadPromise = (async function () {
      injectConfig();
      const styleReady = loadStyle();
      for (const path of SCRIPTS) await loadScript(path);
      await styleReady;
      if (typeof window.Battle !== "function") {
        throw new Error("Official Showdown Battle renderer did not load");
      }
    })();
    return loadPromise;
  }

  function clearElement(element) {
    if (!element) return;
    while (element.firstChild) element.removeChild(element.firstChild);
  }

  function resizeStage() {
    if (!frameElement) return;
    const canvas = frameElement.parentElement;
    if (!canvas) return;
    const width = canvas.clientWidth || BASE_WIDTH;
    const scale = Math.min(2.25, width / BASE_WIDTH);
    frameElement.style.width = BASE_WIDTH + "px";
    frameElement.style.height = BASE_HEIGHT + "px";
    frameElement.style.transformOrigin = "top left";
    frameElement.style.transform = "scale(" + scale + ")";
    canvas.style.height = Math.ceil(BASE_HEIGHT * scale) + "px";
  }

  function destroyBattle() {
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    if (battle && typeof battle.destroy === "function") {
      try { battle.destroy(); } catch (error) { console.warn(error); }
    }
    battle = null;
    clearElement(frameElement);
    clearElement(logElement);
  }

  function normalizeLine(line) {
    if (typeof line !== "string") return null;
    const trimmed = line.trim();
    if (!trimmed || trimmed === "|ping" || trimmed.charAt(0) === ">") return null;
    return trimmed.charAt(0) === "|" ? trimmed : "|" + trimmed;
  }

  function addLines(lines) {
    if (!battle || !Array.isArray(lines)) return;
    for (const rawLine of lines) {
      const line = normalizeLine(rawLine);
      if (!line) continue;
      try {
        battle.add(line);
      } catch (error) {
        setStatus("SHOWDOWN RENDERER ERROR — TELEMETRY FALLBACK ACTIVE");
        console.error("[jev-dashboard] Showdown renderer rejected protocol line", error);
      }
    }
    try { battle.play(); } catch (error) { console.error(error); }
  }

  function mount(nextFrame, nextLog, nextStatus) {
    frameElement = nextFrame;
    logElement = nextLog;
    statusElement = nextStatus;
    if (!frameElement || !logElement) {
      return Promise.reject(new Error("Showdown renderer mount nodes are missing"));
    }
    if (battle) return Promise.resolve(battle);

    setStatus("LOADING OFFICIAL SHOWDOWN RENDERER…");
    return loadBundle().then(function () {
      destroyBattle();
      battle = new window.Battle({
        $frame: window.jQuery(frameElement),
        $logFrame: window.jQuery(logElement),
        id: battleTag,
        subscription: function (event) {
          if (event === "ended") setStatus("SHOWDOWN BATTLE ENDED — FINAL SCENE PRESERVED");
          else if (!battleEnded && (event === "playing" || event === "turn")) setStatus("LIVE SHOWDOWN SCENE");
        },
      });
      resizeObserver = new ResizeObserver(resizeStage);
      resizeObserver.observe(frameElement.parentElement || frameElement);
      resizeStage();
      const arena = frameElement.closest ? frameElement.closest("#showdown-arena") : null;
      if (arena) arena.hidden = false;
      setStatus(battleEnded ? "SHOWDOWN BATTLE ENDED — FINAL SCENE PRESERVED" : "LIVE SHOWDOWN SCENE — RAW PROTOCOL CONNECTED");
      const queued = pendingLines;
      pendingLines = [];
      addLines(queued);
      return battle;
    }).catch(function (error) {
      setStatus("OFFICIAL SHOWDOWN RENDERER UNAVAILABLE — TELEMETRY FALLBACK ACTIVE");
      if (frameElement && frameElement.parentElement) frameElement.parentElement.classList.add("renderer-unavailable");
      console.error("[jev-dashboard] Showdown renderer unavailable", error);
      throw error;
    });
  }

  function reset(nextBattleTag) {
    battleTag = nextBattleTag || "jev-showdown";
    battleEnded = false;
    pendingLines = [];
    destroyBattle();
    setStatus("WAITING FOR SHOWDOWN BATTLE PROTOCOL…");
  }

  function feed(lines) {
    if (!Array.isArray(lines)) return 0;
    const normalized = lines.map(normalizeLine).filter(Boolean);
    if (!normalized.length) return 0;
    if (!battle) pendingLines = pendingLines.concat(normalized);
    else addLines(normalized);
    return normalized.length;
  }

  function setUnavailable(message) {
    setStatus(message || "OFFICIAL SHOWDOWN RENDERER UNAVAILABLE — TELEMETRY FALLBACK ACTIVE");
    const arena = frameElement && frameElement.closest ? frameElement.closest("#showdown-arena") : null;
    if (arena) arena.hidden = true;
  }

  function end() {
    battleEnded = true;
    setStatus("SHOWDOWN BATTLE ENDED — FINAL SCENE PRESERVED");
  }

  window.JevShowdownRenderer = {
    mount: mount,
    reset: reset,
    feed: feed,
    end: end,
    setUnavailable: setUnavailable,
    destroy: destroyBattle,
  };
})();
