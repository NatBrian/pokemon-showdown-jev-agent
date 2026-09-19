# tests/unit/test_frontend_assets.py
import os


def test_frontend_assets_exist():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    static_dir = os.path.join(base_dir, "src", "jev_showdown", "web", "static")

    html_path = os.path.join(static_dir, "index.html")
    css_path = os.path.join(static_dir, "style.css")
    js_path = os.path.join(static_dir, "app.js")

    assert os.path.exists(html_path)
    assert os.path.exists(css_path)
    assert os.path.exists(js_path)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
        assert "START JEV BATTLE" in html
        assert "LIVE BATTLE" in html
        assert "JEV INPUT" in html
        assert "JEV OUTPUT" in html
        assert "INSPECT DATA" in html
