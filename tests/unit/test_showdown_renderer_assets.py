from pathlib import Path


RENDERER_ROOT = (
    Path(__file__).parents[2] / "src" / "jev_showdown" / "web" / "static" / "showdown"
)

REQUIRED = {
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
    "style/battle.css",
    "style/battle-log.css",
    "NOTICE.md",
}


def test_official_renderer_subset_is_present():
    actual = {
        path.relative_to(RENDERER_ROOT).as_posix()
        for path in RENDERER_ROOT.rglob("*")
        if path.is_file()
    }

    assert REQUIRED <= actual


def test_renderer_notice_identifies_source_and_licenses():
    notice = (RENDERER_ROOT / "NOTICE.md").read_text(encoding="utf-8")

    assert "pokemon-showdown-client" in notice
    assert "showdown" in notice.lower()
    assert "license" in notice.lower()
