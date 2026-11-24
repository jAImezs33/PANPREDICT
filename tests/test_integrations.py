import asyncio
import io
import json
from urllib.error import URLError
import pytest
from src.demo import make_demo_data
from src.main import preprocess_data, train_and_forecast
from src import send_telegram


def test_telegram_plain_text_confirmed_delivery(monkeypatch):
    sent = []
    def fake_urlopen(request, timeout):
        sent.append(json.loads(request.data))
        assert timeout == 20
        return io.BytesIO(b'{"ok": true}')
    monkeypatch.setattr(send_telegram, "urlopen", fake_urlopen)
    asyncio.run(send_telegram.send_telegram_message("fake-token", "fake-chat", "Integral_[test]"))
    assert sent == [{"chat_id": "fake-chat", "text": "Integral_[test]"}]


def test_telegram_errors_do_not_leak_token(monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("secret-token-in-url")
    monkeypatch.setattr(send_telegram, "urlopen", fail)
    with pytest.raises(RuntimeError) as exc:
        asyncio.run(send_telegram.send_telegram_message("secret-token", "fake-chat", "test"))
    assert "secret-token" not in str(exc.value)


def test_notification_uses_forecast_date_not_tomorrow():
    forecast = train_and_forecast(preprocess_data(make_demo_data()), h=8)
    message = send_telegram.forecast_message(forecast)
    assert "2026-11-01" in message
    assert message.count("uds.") == 3


def test_google_requires_credentials_without_network(monkeypatch):
    from src.integrations import _client
    monkeypatch.delenv("GOOGLE_SERVICE_ACC_JSON", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_SERVICE_ACC_JSON"):
        _client()
