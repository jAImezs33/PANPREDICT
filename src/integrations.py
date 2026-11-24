"""Optional Google Sheets adapter. Nothing is sent when this module is imported."""
import json
import os

import pandas as pd


def _client():
    raw = os.getenv("GOOGLE_SERVICE_ACC_JSON")
    if not raw:
        raise ValueError("Configura GOOGLE_SERVICE_ACC_JSON para usar Google Sheets.")
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise RuntimeError("Instala requirements_integrations.txt para usar Google Sheets.") from exc
    try:
        credentials = Credentials.from_service_account_info(
            json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return gspread.authorize(credentials)
    except Exception:
        raise RuntimeError("No se pudieron preparar las credenciales de Google Sheets.") from None


def save_to_gsheets(forecast: pd.DataFrame, sheet_id: str):
    if not sheet_id or forecast.empty:
        raise ValueError("Se requiere una hoja y un pronóstico no vacío.")
    client = _client()
    import gspread
    try:
        spreadsheet = client.open_by_key(sheet_id)
        try:
            worksheet = spreadsheet.worksheet("Pronóstico")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Pronóstico", rows=100, cols=20)
        wide = forecast.pivot(index="ds", columns="unique_id", values="yhat").reset_index()
        wide["ds"] = pd.to_datetime(wide["ds"]).dt.strftime("%Y-%m-%d")
        wide = wide.rename(columns={"ds": "Fecha"})
        # Upload the new table before clearing only obsolete cells.
        previous_rows, previous_cols = worksheet.row_count, worksheet.col_count
        rows, cols = len(wide) + 1, len(wide.columns)
        worksheet.resize(rows=max(rows, previous_rows), cols=max(cols, previous_cols))
        worksheet.update(values=[wide.columns.tolist()] + wide.values.tolist(),
                         range_name="A1", value_input_option="RAW")
        # Shrink after the successful write, removing stale rows/columns.
        worksheet.resize(rows=rows, cols=cols)
    except Exception:
        raise RuntimeError(
            "No se pudo publicar en Google Sheets. Comprueba credenciales, permisos y conexión."
        ) from None


def get_forecast_from_gsheets(sheet_id: str) -> pd.DataFrame:
    try:
        return pd.DataFrame(_client().open_by_key(sheet_id).worksheet("Pronóstico").get_all_records())
    except Exception:
        raise RuntimeError("No se pudo leer la pestaña Pronóstico de Google Sheets.") from None
