from pathlib import Path
from html.parser import HTMLParser


class _IdParentParser(HTMLParser):
    _void_elements = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.parents = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.parents[element_id] = self.stack[-1][1] if self.stack else None
        if tag not in self._void_elements:
            self.stack.append((tag, element_id))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


ROOT = Path(__file__).parents[2]
STATIC = ROOT / "src" / "jev_showdown" / "web" / "static"


def read_static(name: str | Path) -> str:
    return (STATIC / Path(name)).read_text(encoding="utf-8")


def test_live_shell_exposes_progressive_disclosure_regions():
    html = read_static("index.html")
    assert 'id="live-view-tab"' in html
    assert 'id="open-inspector"' in html
    assert 'id="decision-rail"' in html
    assert 'id="inspection-drawer"' in html
    assert 'id="harness-calculated-disclosure"' in html
    assert 'id="harness-legal-disclosure"' in html


def test_official_battle_surface_remains_unique():
    html = read_static("index.html")
    assert html.count('id="showdown-frame"') == 1
    assert html.count('id="showdown-log"') == 1
    assert 'id="showdown-arena"' in html


def test_showdown_message_log_is_outside_the_clipped_battle_stage():
    html = read_static("index.html")
    parser = _IdParentParser()
    parser.feed(html)
    assert parser.parents["showdown-arena"] == "battle-panel"
    assert parser.parents["showdown-log"] == "battle-panel"


def test_inspection_tabs_remain_semantic_controls():
    html = read_static("index.html")
    assert 'role="tablist"' in html
    assert 'role="tabpanel"' in html
    assert 'data-inspect-tab="raw-event"' in html


def test_live_view_contains_only_compact_harness_targets():
    html = read_static("index.html")
    assert 'id="harness-observed-facts"' in html
    assert 'id="harness-calculated-disclosure"' in html
    assert 'id="harness-legal-disclosure"' in html
    assert 'id="jev-metadata"' in html
    assert 'data-inspect-tab="jev-input"' in html


def test_live_rail_exposes_complete_evidence_entry_points():
    html = read_static("index.html")
    assert 'data-inspect-tab="harness-state"' in html
    assert 'data-inspect-tab="calculated-facts"' in html
    assert 'data-inspect-tab="jev-response"' in html
    assert "FULL STATE" in html
    assert "FULL RESPONSE" in html
    assert "BACK TO LIVE" in html


def test_dashboard_mode_controls_are_wired():
    app = read_static(Path("dashboard") / "app.js")
    inspector = read_static(Path("dashboard") / "inspector.js")
    assert "setDashboardMode" in app
    assert "data-view-mode" in app
    assert "setMode" in inspector
    assert "aria-selected" in inspector


def test_calculated_facts_are_not_truncated_in_the_live_disclosure():
    render = read_static(Path("dashboard") / "render.js")
    assert ".slice(0, 5)" not in render


def test_desktop_live_layout_keeps_three_primary_columns():
    css = read_static("style.css")
    assert "minmax(0, 1.6fr)" in css
    assert "display: contents" in css


def test_harness_primary_summary_retains_context_fields():
    render = read_static(Path("dashboard") / "render.js")
    assert 'factRow("Format"' in render
    assert 'factRow("Showdown rqid"' in render
    assert 'factRow("Tera available"' in render


def test_dashboard_css_is_viewport_aware_and_responsive():
    css = read_static("style.css")
    assert "100dvh" in css
    assert "aspect-ratio" in css
    assert "#decision-rail" in css
    assert ".evidence-disclosure" in css
    assert "@media (max-width: 899px)" in css


def test_dashboard_css_uses_fluid_landscape_geometry():
    css = read_static("style.css")
    assert "100svh" in css
    assert "--layout-gap" in css
    assert "minmax(clamp(250px" in css
    assert "max-height: 800px" in css
    assert "max-height: calc(100svh" in css


def test_battle_surface_and_renderer_fit_both_dimensions():
    css = read_static("style.css")
    renderer = read_static("showdown-renderer.js")
    assert "grid-template-rows: auto minmax(0, 1fr) auto auto" in css
    assert "#showdown-log" in css
    assert "Math.min(width / BASE_WIDTH, height / BASE_HEIGHT)" in renderer
    assert "closest(\"#showdown-arena\")" in renderer


def test_evidence_columns_follow_the_responsive_battle_row():
    css = read_static("style.css")
    assert ".primary-grid > #decision-rail > #jev-panel,\n  .primary-grid > #decision-rail > #system-harness" in css
    assert ".primary-grid > #battle-panel {\n    align-self: stretch;\n    height: auto;" in css
    assert "align-self: stretch;\n    height: auto;" in css
    assert ".evidence-panel > .panel-scroll" in css
    assert "max-height: none;" in css
    assert "max-height: calc(100dvh - 390px);" not in css
    assert "max-height: calc(100svh - 390px);" not in css


def test_battle_history_gets_responsive_vertical_space():
    css = read_static("style.css")
    assert "min-height: clamp(84px, 10vh, 108px);" in css
    assert "max-height: clamp(128px, 17vh, 184px);" in css
    assert "calc(100svh - 485px)" in css
    assert "height: clamp(535px, calc(100svh - 235px), 640px);" in css
    assert "height: clamp(554px, calc(100svh - 220px), 900px);" in css


def test_dashboard_css_contains_reduced_motion_equivalent():
    css = read_static("style.css")
    assert "prefers-reduced-motion: reduce" in css
    assert "animation-duration" in css


def test_probability_bars_render_distinct_fill_and_selected_state():
    css = read_static("style.css")
    charts = read_static(Path("dashboard") / "charts.js")
    assert ".probability-fill { display: block;" in css
    assert 'style="width:${safeValue}%"' in charts
    assert 'data-selected="${id === selected}"' in charts
    assert ".probability-row[data-selected=\"true\"] .probability-fill" in css
