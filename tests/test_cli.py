import os
from pathlib import Path
import subprocess
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, env=None):
    return subprocess.run([sys.executable, str(ROOT / "forecast_cli.py"), *args],
                          cwd=ROOT, text=True, capture_output=True, env=env, timeout=90)


def test_demo_works_without_credentials_even_if_sheet_env_is_set(tmp_path):
    output = tmp_path / "result.csv"
    env = os.environ.copy()
    env["GOOGLE_SHEET_ID"] = "must-not-be-used-without-an-explicit-flag"
    for name in ("GOOGLE_SERVICE_ACC_JSON", "TELEGRAM_TOKEN", "CHAT_ID"):
        env.pop(name, None)
    result = run_cli("--demo", "--days", "8", "--backtest", "--output", str(output), env=env)
    assert result.returncode == 0, result.stderr
    assert len(pd.read_csv(output)) == 24
    assert "DEMO" in result.stdout
    assert "MAE" in result.stdout


def test_invalid_csv_exits_nonzero_without_output(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("fecha;articulo;unidades\n2026-10-01;Barra;-1\n", encoding="utf-8")
    output = tmp_path / "result.csv"
    result = run_cli("--csv", str(source), "--output", str(output))
    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert not output.exists()


def test_csv_example_pipeline(tmp_path):
    result = run_cli("--csv", str(ROOT / "examples" / "ventas_demo.csv"),
                     "--output", str(tmp_path / "forecast.csv"))
    assert result.returncode == 0, result.stderr


def test_out_of_range_days_are_cli_error(tmp_path):
    output = tmp_path / "no.csv"
    result = run_cli("--demo", "--days", "0", "--output", str(output))
    assert result.returncode == 2
    assert not output.exists()


def test_send_requires_configuration_before_generating_files(tmp_path, monkeypatch):
    import forecast_cli
    monkeypatch.setattr(forecast_cli, "load_dotenv", lambda: None)
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("CHAT_ID", raising=False)
    output = tmp_path / "no.csv"
    assert forecast_cli.main(["--demo", "--send", "--output", str(output)]) == 1
    assert not output.exists()
