from pathlib import Path


ROOT = Path(__file__).parents[2]
STATIC = ROOT / "src" / "jev_showdown" / "web" / "static"


def read_static(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


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


def test_inspection_tabs_remain_semantic_controls():
    html = read_static("index.html")
    assert 'role="tablist"' in html
    assert 'role="tabpanel"' in html
    assert 'data-inspect-tab="raw-event"' in html
