"""Forecast locally by default. External writes require explicit command flags."""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from src.demo import make_demo_data
from src.main import DataValidationError, backtest, forecast_csv, load_data, preprocess_data, train_and_forecast


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="PANPREDICT: previsión local de ventas de panadería")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", help="CSV de ventas")
    source.add_argument("--demo", action="store_true", help="Usar datos sintéticos incluidos")
    parser.add_argument("--days", type=int, default=8, help="Horizonte de 1 a 90 días (por defecto 8)")
    parser.add_argument("--model", choices=["seasonal", "autoarima"], default="seasonal")
    parser.add_argument("--missing-days", choices=["error", "zero"], default="error")
    parser.add_argument("--output", default="output/pronostico.csv", help="CSV de salida")
    parser.add_argument("--backtest", action="store_true", help="Evaluar los últimos 7 días del histórico")
    parser.add_argument("--sheet-id", help="Publicar explícitamente en la pestaña Pronóstico de esta hoja")
    parser.add_argument("--send", action="store_true", help="Enviar explícitamente el primer día a Telegram")
    parser.add_argument("--retrain", action="store_true", help="Compatible con versiones previas; siempre se ajusta")
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 90:
        parser.error("--days debe estar entre 1 y 90.")
    try:
        # Check configuration before writing either local output or external services.
        if args.send and not (os.getenv("TELEGRAM_TOKEN") and os.getenv("CHAT_ID")):
            raise DataValidationError("--send requiere TELEGRAM_TOKEN y CHAT_ID en .env.")
        raw = make_demo_data() if args.demo else load_data(args.csv)
        history = preprocess_data(raw, missing_days=args.missing_days)
        forecast = train_and_forecast(history, h=args.days, retrain=args.retrain, model=args.model)
        evaluation = backtest(history, model=args.model) if args.backtest else None
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(forecast_csv(forecast), encoding="utf-8-sig")
        if args.demo:
            print("DEMO: datos sintéticos; no son resultados de una panadería real.")
        print(f"Modelo: {args.model}. Último dato: {history['ds'].max().date()}.")
        print(f"Pronóstico guardado en {output} ({len(forecast)} filas).")
        if evaluation is not None:
            print("Evaluación temporal: últimos 7 días, excluidos del entrenamiento.")
            print(evaluation.to_string(index=False))
        if args.sheet_id:
            from src.integrations import save_to_gsheets
            save_to_gsheets(forecast, args.sheet_id)
            print("Pronóstico publicado en Google Sheets.")
        if args.send:
            import asyncio
            from src.send_telegram import forecast_message, send_telegram_message
            asyncio.run(send_telegram_message(
                os.environ["TELEGRAM_TOKEN"], os.environ["CHAT_ID"], forecast_message(forecast)
            ))
            print("Mensaje enviado a Telegram.")
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
