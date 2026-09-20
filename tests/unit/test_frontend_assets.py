# tests/unit/test_frontend_assets.py
import os


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_frontend_assets_exist():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")

    html_path = os.path.join(static_dir, "index.html")
    css_path = os.path.join(static_dir, "style.css")
    js_path = os.path.join(static_dir, "app.js")

    assert os.path.exists(html_path)
    assert os.path.exists(css_path)
    assert os.path.exists(js_path)

    html = _read(html_path)
    # Core layout required by docs/design/dashboard-ui-elements.md
    assert "START JEV BATTLE" in html
    assert "LIVE BATTLE" in html
    assert "JEV INPUT" in html
    assert "JEV OUTPUT" in html
    assert "INSPECT DATA" in html
    assert "TURN HISTORY" in html
    # Information-ownership labels (transparency requirement)
    assert "CALCULATED BY HARNESS" in html
    assert "API INFERENCE (MODEL)" in html
    assert "SHOWDOWN" in html
    # Fallback must be visually attributed to the adapter, never Jev
    assert "JEV FAILED — FALLBACK USED" in html
    # Bottom fast action strip
    assert "VALIDATE" in html
    assert "ACT" in html
    assert "RESULT" in html
    # Both team rows explicitly (fog-of-war opponent vs known team)
    assert "OPPONENT TEAM" in html
    assert "YOUR TEAM" in html
    # MVP battle view is local and deterministic; it must not depend on an
    # iframe login/session to show the active battle.
    assert "STATE RENDERED FROM SHOWDOWN TELEMETRY" in html
    assert '<iframe id="showdown-frame"' not in html
    # Reported token usage / cost and target remaining-HP estimate
    assert "decision-usage" in html
    assert "result-hp-wrap" in html
    assert "OBSERVED RESULT" in html


def test_frontend_styles_match_arcade_direction():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    css = _read(os.path.join(base_dir, "src", "jev_showdown", "web", "static", "style.css"))
    # 1990s arcade-retro direction: deep navy, CRT scanlines, error state
    assert "#0b0d1b" in css
    assert ".scanlines" in css
    assert ".btn-error" in css


def test_frontend_client_handles_lifecycle_states():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    js = _read(os.path.join(base_dir, "src", "jev_showdown", "web", "static", "app.js"))
    # Observable startup/playing/error states for the START JEV BATTLE flow
    assert "JEV PLAYING" in js
    assert "RETRY BATTLE" in js
    assert "btn-error" in js
    # Fallback banner is driven by validation data, with adapter attribution
    assert "FALLBACK ACTION" in js
    assert "jev_request" in js
    assert "submitted_order" in js
    assert "calculation_mode" in js
    assert "initShowdownFrame();" not in js


def test_frontend_uses_official_showdown_sprites_without_iframe():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    js = _read(os.path.join(base_dir, "src", "jev_showdown", "web", "static", "app.js"))

    assert 'https://play.pokemonshowdown.com/sprites/' in js
    assert '"xyani"' in js
    assert '"xyani-back"' in js
    assert "hyphenatedForm" in js
    assert "exeggutor-alola" not in js  # resolved generically from compact IDs


def test_frontend_surfaces_observed_match_result_after_overlay():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    js = _read(os.path.join(base_dir, "src", "jev_showdown", "web", "static", "app.js"))
    html = _read(os.path.join(base_dir, "src", "jev_showdown", "web", "static", "index.html"))

    assert "BATTLE ENDED" in js
    assert "OBSERVED RESULT" in html
    assert "img.pokemondb.net" not in js


def test_dashboard_has_official_showdown_stage_and_adapter():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    html = _read(os.path.join(static_dir, "index.html"))

    assert 'id="showdown-arena"' in html
    assert 'id="showdown-frame"' in html
    assert 'id="showdown-log"' in html
    assert "showdown-renderer.js" in html
    assert "<iframe" not in html.lower()


def test_adapter_loads_renderer_in_dependency_order_and_handles_frames():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    adapter = _read(os.path.join(static_dir, "showdown-renderer.js"))

    assert "window.JevShowdownRenderer" in adapter
    assert "js/battle.js" in adapter
    assert "BATTLE_REPLAY" not in adapter
    assert "battle.add" in adapter
    assert "battle.play" in adapter


def test_dashboard_uses_battle_first_layout_and_truth_strip():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    html = _read(os.path.join(static_dir, "index.html"))
    css = _read(os.path.join(static_dir, "style.css"))

    assert "VALIDATE" in html
    assert "ACT" in html
    assert "OBSERVED RESULT" in html
    assert "grid-template-columns: minmax(0, 1.6fr) minmax(360px, 0.85fr)" in css
    assert ".panel-battle { grid-column: 1; grid-row: 1 / span 2; }" in css


def test_frontend_has_explicit_renderer_failure_fallback_copy():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    html = _read(os.path.join(static_dir, "index.html"))

    assert "TELEMETRY FALLBACK &mdash; OFFICIAL SHOWDOWN RENDERER UNAVAILABLE" in html


def test_battle_end_preserves_final_official_scene_and_marks_result_observed():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    js = _read(os.path.join(static_dir, "app.js"))
    handler = js[js.index("function handleBattleEnd"):js.index("function closeOverlay")]

    assert 'getEl("showdown-status")' in handler
    assert "SHOWDOWN BATTLE ENDED" in handler
    assert "RESULT OBSERVED FROM SHOWDOWN" in handler
    assert "JevShowdownRenderer.end" in handler
    assert "JevShowdownRenderer.destroy" not in handler


def test_dashboard_dom_helper_does_not_collide_with_showdown_jquery():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    js = _read(os.path.join(static_dir, "app.js"))

    assert "const $ =" not in js
    assert "const getEl =" in js


def test_showdown_frame_has_flow_wrapper_for_official_absolute_scene():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    html = _read(os.path.join(static_dir, "index.html"))
    css = _read(os.path.join(static_dir, "style.css"))

    assert 'class="showdown-stage-canvas"' in html
    assert ".showdown-stage-canvas" in css


def test_showdown_ended_callback_preserves_final_scene_label():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    adapter = _read(os.path.join(static_dir, "showdown-renderer.js"))

    assert 'event === "ended") setStatus("SHOWDOWN BATTLE ENDED — FINAL SCENE PRESERVED")' in adapter


def test_slow_renderer_mount_does_not_overwrite_ended_state():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")
    adapter = _read(os.path.join(static_dir, "showdown-renderer.js"))

    assert 'battleEnded ? "SHOWDOWN BATTLE ENDED — FINAL SCENE PRESERVED"' in adapter
