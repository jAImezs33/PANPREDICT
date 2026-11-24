from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_demo_renders_changes_horizon_and_backtests():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert len(app.metric) == 3
    assert app.metric[0].value == "3"
    app.slider(key="horizon").set_value(14).run()
    assert not app.exception
    assert app.metric[2].value == "14"
    app.button(key="evaluate").click().run()
    assert not app.exception
    assert any("MAE (unidades)" in frame.value.columns for frame in app.dataframe)


def test_upload_mode_waits_for_file():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    app.radio(key="source").set_value("Mi archivo CSV").run()
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 0
