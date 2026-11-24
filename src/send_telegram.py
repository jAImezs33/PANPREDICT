"""Explicit Telegram delivery, using the standard library and plain text."""
import asyncio
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.integrations import get_forecast_from_gsheets


def forecast_message(forecast):
    first = forecast[forecast["ds"] == forecast["ds"].min()]
    date = first["ds"].iloc[0].strftime("%Y-%m-%d")
    lines = [f"PANPREDICT · Previsión para {date}"]
    lines.extend(f"• {row.unique_id}: {row.yhat:.1f} uds." for row in first.itertuples())
    message = "\n".join(lines)
    if len(message) > 4096:
        raise ValueError("Demasiados productos para un mensaje de Telegram.")
    return message


def _send(token: str, chat_id: str, message: str):
    if not token or not chat_id:
        raise ValueError("Faltan TELEGRAM_TOKEN o CHAT_ID.")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
        if not result.get("ok"):
            raise RuntimeError("Telegram no confirmó la entrega.")
    except (HTTPError, URLError, TimeoutError, ValueError):
        # URLs and API errors can contain the token: do not echo them.
        raise RuntimeError("No se pudo enviar a Telegram. Comprueba token, chat y conexión.") from None


async def send_telegram_message(token: str, chat_id: str, message: str):
    await asyncio.to_thread(_send, token, chat_id, message)


if __name__ == "__main__":
    raise SystemExit("Para enviar usa: python forecast_cli.py --csv ventas.csv --send")
