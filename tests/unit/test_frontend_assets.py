from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = REPO_ROOT / "src" / "jev_showdown" / "web" / "static"


def _read_index() -> str:
    return (STATIC_ROOT / "index.html").read_text(encoding="utf-8")


def _read_app() -> str:
    return (STATIC_ROOT / "app.js").read_text(encoding="utf-8")


def _read_style() -> str:
    return (STATIC_ROOT / "style.css").read_text(encoding="utf-8")


def test_dashboard_shell_has_one_official_scene_and_jev_console():
    html = _read_index()
    required = [
        'id="start-btn"',
        'id="showdown-arena"',
        'id="showdown-frame"',
        'id="showdown-log"',
        'id="showdown-status"',
        'id="jev-input"',
        'id="jev-decision"',
        'id="jev-history"',
        'id="truth-strip"',
        'id="technical-inspect"',
        'id="inspect-drawer"',
    ]

    for marker in required:
        assert marker in html

    assert html.index("showdown-renderer.js") < html.index("app.js")
    assert '<button id="start-btn"' in html
    drawer_start = html.index('id="inspect-drawer"')
    drawer_tag = html[drawer_start : html.index(">", drawer_start)]
    assert "hidden" in drawer_tag


def test_dashboard_does_not_embed_or_duplicate_showdown_ui():
    html = _read_index().lower()

    assert "<iframe" not in html
    assert "play.pokemonshowdown.com/" not in html
    assert "history-cards" not in html
    assert "self-team-slots" not in html
    assert "opp-team-slots" not in html
    assert "active-pokemon-card" not in html
    assert "weather-card" not in html
    assert "terrain-card" not in html
    assert "battle-log-card" not in html
    assert "observable data" not in html
    assert "same game. deeper insight." not in html


def test_dashboard_app_exposes_injected_event_state_machine():
    app = _read_app()

    for marker in (
        "window.JevDashboard",
        "createDashboardApp",
        "summarizeProtocolLines",
        "DECISION_PHASE",
        "BATTLE_REPLAY",
        "RESULT OBSERVED",
        "FALLBACK USED",
        "textContent",
    ):
        assert marker in app

    assert "innerHTML =" not in app


def test_dashboard_css_keeps_battle_and_telemetry_visible_on_landscape_desktop():
    css = _read_style()

    for marker in (
        "aspect-ratio: 16 / 9",
        "grid-template-columns",
        "overflow-x: hidden",
        "@media",
        ".decision-rail",
        ".inspect-drawer",
    ):
        assert marker in css


def test_showdown_renderer_owns_scene_and_protocol_log_nodes_only():
    renderer = (STATIC_ROOT / "showdown-renderer.js").read_text(encoding="utf-8")

    assert "window.JevShowdownRenderer" in renderer
    assert "battle.add" in renderer
    assert "SHOWDOWN RENDERER READY" in renderer
    assert "window.JevDashboard" not in renderer
