import os


def _static_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, "src", "jev_showdown", "web", "static")


def _read(name: str) -> str:
    with open(os.path.join(_static_dir(), name), "r", encoding="utf-8") as f:
        return f.read()


def test_frontend_assets_exist_and_use_the_battle_first_shell():
    static_dir = _static_dir()
    assert os.path.exists(os.path.join(static_dir, "index.html"))
    assert os.path.exists(os.path.join(static_dir, "style.css"))
    assert os.path.exists(os.path.join(static_dir, "app.js"))

    html = _read("index.html")
    for required in (
        'class="battle-bay"',
        'class="decision-rail"',
        'id="jev-input"',
        'id="jev-output"',
        'id="truth-strip"',
        'id="technical-inspect"',
        'id="inspect-drawer"',
        'id="showdown-arena"',
        'id="showdown-frame"',
        'id="showdown-log"',
        'id="showdown-caption"',
    ):
        assert required in html

    for obsolete in (
        'id="end-overlay"',
        'id="history-cards"',
        'id="self-team-slots"',
        'id="opp-team-slots"',
        "OBSERVABLE DATA",
        "SAME GAME. DEEPER INSIGHT.",
        "TURN HISTORY",
    ):
        assert obsolete not in html

    assert "START JEV BATTLE" in html
    assert "JEV INPUT" in html
    assert "JEV DECISION" in html
    assert "VALIDATE" in html
    assert "OBSERVED RESULT" in html
    assert 'id="arena-fallback" class="arena-fallback"' in html
    assert "PRESS START TO LOAD SHOWDOWN SCENE" in html
    assert '<iframe' not in html.lower()


def test_frontend_styles_match_retro_battle_bay_direction():
    css = _read("style.css")
    assert "#0b0d1b" in css
    assert ".scanlines" in css
    assert ".btn-error" in css
    assert "aspect-ratio: 16 / 9" in css
    assert ".showdown-stage-canvas" in css
    assert "position: absolute" in css
    assert ".showdown-log-viewport" in css


def test_frontend_client_uses_real_jev_telemetry_without_duplicate_renderers():
    js = _read("app.js")
    assert "JEV PLAYING" in js
    assert "FALLBACK ACTION" in js
    assert "jev_request" in js
    assert "submitted_order" in js
    assert "probabilities" in js
    assert "fallback_reason" in js
    assert "BATTLE_FRAME" in js

    for obsolete in (
        "renderActiveMons",
        "renderTeams",
        "renderHistory",
        "closeOverlay",
        "win chance",
        "risk (faint)",
        "MODEL v3.1",
        "jev-1.13-free",
    ):
        assert obsolete.lower() not in js.lower()


def test_frontend_uses_the_official_showdown_renderer_without_iframe():
    html = _read("index.html")
    assert "showdown-renderer.js" in html
    assert "<iframe" not in html.lower()

    adapter = _read("showdown-renderer.js")
    assert "window.JevShowdownRenderer" in adapter
    assert "js/battle.js" in adapter
    assert "BATTLE_REPLAY" not in adapter
    assert "battle.add" in adapter
    assert "battle.play" in adapter
    assert "const BASE_HEIGHT = 360" in adapter
    assert "const BASE_HEIGHT = 380" not in adapter


def test_dashboard_keeps_official_scene_and_places_messages_inside_the_bay():
    html = _read("index.html")
    assert 'class="showdown-stage-canvas"' in html
    assert 'id="showdown-caption"' in html
    assert 'id="showdown-status"' in html
    assert "TELEMETRY FALLBACK" in html

    css = _read("style.css")
    assert ".showdown-stage-viewport" in css
    assert ".showdown-caption" in css
    assert ".showdown-status" in css


def test_battle_end_preserves_final_official_scene_and_observed_result():
    js = _read("app.js")
    assert "SHOWDOWN BATTLE ENDED" in js
    assert "RESULT OBSERVED FROM SHOWDOWN" in js
    assert "JevShowdownRenderer.end" in js
    assert "JevShowdownRenderer.destroy" not in js

    adapter = _read("showdown-renderer.js")
    assert 'event === "ended") setStatus("SHOWDOWN BATTLE ENDED' in adapter
    assert 'battleEnded ? "SHOWDOWN BATTLE ENDED' in adapter


def test_dashboard_has_single_click_technical_inspector():
    html = _read("index.html")
    js = _read("app.js")
    for required in ('id="technical-inspect"', 'id="inspect-drawer"', 'id="inspect-close"'):
        assert required in html
    for required in ("STATE", "JEV REQUEST", "JEV RESPONSE", "VALIDATION", "PROTOCOL"):
        assert required in html
    for required in ("inspect", "question", "response", "BATTLE_FRAME", "JSON.stringify"):
        assert required.lower() in js.lower()
    assert "keydown" in js
    assert 'event.key === "Escape"' in js


def test_dashboard_uses_a_single_desktop_grid_and_stacks_on_small_screens():
    css = _read("style.css")
    assert ".dashboard-main" in css
    assert ".decision-rail" in css
    assert "grid-template-columns: minmax(0, 7fr) minmax(320px, 3fr)" in css
    assert "max-width: 1800px" not in css
    assert "@media (max-width: 900px)" in css
    assert "grid-template-columns: 1fr" in css
