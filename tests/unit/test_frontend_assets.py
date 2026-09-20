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
