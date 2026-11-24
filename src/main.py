"""Local forecasting pipeline. Importing this module never connects to a service."""
from __future__ import annotations

import csv
import warnings

import numpy as np
import pandas as pd


class DataValidationError(ValueError):
    """The sales history cannot be used without a correction or explicit choice."""


ALIASES = {
    "unique_id": ("unique_id", "articulo", "producto", "product", "item", "descripcion"),
    "ds": ("ds", "fecha", "date", "fechas", "fecha_venta"),
    "y": ("y", "unidades", "cantidad", "quantity", "ventas", "sales"),
}


def load_data(source) -> pd.DataFrame:
    """Read UTF-8 CSV (comma, semicolon or tab), preserving product identifiers."""
    if hasattr(source, "seek"):
        source.seek(0)
    try:
        return pd.read_csv(
            source, sep=None, engine="python", encoding="utf-8-sig",
            dtype=str, keep_default_na=False,
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError, csv.Error) as exc:
        raise DataValidationError(
            "No se pudo leer el CSV. Usa UTF-8 y separador coma, punto y coma o tabulador."
        ) from exc


def preprocess_data(df: pd.DataFrame, missing_days: str = "error") -> pd.DataFrame:
    """Validate, sum duplicate sales and require an explicit policy for missing days.

    Dates: ISO YYYY-MM-DD or Spanish DD/MM/YYYY. Missing days are not zero sales
    unless missing_days='zero'. All products must end on the same historical date.
    """
    if missing_days not in {"error", "zero"}:
        raise DataValidationError("missing_days debe ser 'error' o 'zero'.")
    if df.empty:
        raise DataValidationError("El archivo no contiene ventas.")
    data = df.copy()
    data.columns = [str(c).strip().lower() for c in data.columns]
    if data.columns.duplicated().any():
        raise DataValidationError("Hay nombres de columnas duplicados.")
    rename = {}
    for target, names in ALIASES.items():
        found = [name for name in names if name in data.columns]
        if len(found) != 1:
            raise DataValidationError(
                f"Debe haber una sola columna para {target}: {', '.join(names)}."
            )
        rename[found[0]] = target
    data = data.rename(columns=rename)[["unique_id", "ds", "y"]]
    ids = data["unique_id"].astype("string").str.strip()
    if ids.isna().any() or ids.eq("").any():
        raise DataValidationError("Hay productos sin nombre.")
    data["unique_id"] = ids.astype(str)

    dates = data["ds"]
    if pd.api.types.is_datetime64_any_dtype(dates):
        if dates.dt.tz is not None:
            raise DataValidationError("Usa fechas locales sin zona horaria.")
        parsed = dates.dt.normalize()
    else:
        dates = dates.astype("string").str.strip()
        iso = pd.to_datetime(dates, format="%Y-%m-%d", errors="coerce")
        spanish = pd.to_datetime(dates, format="%d/%m/%Y", errors="coerce")
        parsed = iso.fillna(spanish)
    if parsed.isna().any():
        raise DataValidationError("Hay fechas inválidas. Usa AAAA-MM-DD o DD/MM/AAAA.")
    data["ds"] = parsed
    data["y"] = pd.to_numeric(
        data["y"].astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )
    if not np.isfinite(data["y"].to_numpy(dtype=float)).all() or data["y"].lt(0).any():
        raise DataValidationError("Las ventas deben ser números finitos mayores o iguales a cero.")
    data = data.groupby(["unique_id", "ds"], as_index=False, sort=True)["y"].sum()
    if not np.isfinite(data["y"].to_numpy(dtype=float)).all():
        raise DataValidationError("La suma de ventas es demasiado grande.")
    cutoff = data["ds"].max()
    complete = []
    for product, group in data.groupby("unique_id", sort=True):
        # Bound accidental dates such as 1900 instead of 2026 before allocating a calendar.
        if (cutoff - group["ds"].min()).days > 3660:
            raise DataValidationError("El histórico no puede superar diez años por producto.")
        dates = pd.date_range(group["ds"].min(), cutoff, freq="D")
        missing = dates.difference(pd.DatetimeIndex(group["ds"]))
        if len(missing) and missing_days == "error":
            raise DataValidationError(
                f"Faltan {len(missing)} días de '{product}'. Completa el histórico o "
                "elige explícitamente tratar los días ausentes como cero."
            )
        group = group.set_index("ds").reindex(dates)
        group.index.name = "ds"
        group["unique_id"] = product
        group["y"] = group["y"].fillna(0)
        if len(group) < 2:
            raise DataValidationError(f"'{product}' necesita al menos dos días de histórico.")
        complete.append(group.reset_index()[["unique_id", "ds", "y"]])
    return pd.concat(complete, ignore_index=True)


def train_and_forecast(
    df: pd.DataFrame, X_df=None, h: int = 8, retrain: bool = False,
    model: str = "seasonal",
) -> pd.DataFrame:
    """Forecast from the last historical date, with no network or pickle cache.

    seasonal repeats the last seven days (mean for histories shorter than a week).
    autoarima is an optional StatsForecast 2.x model with model-based 90% intervals.
    """
    if isinstance(h, bool) or not isinstance(h, int) or not 1 <= h <= 90:
        raise DataValidationError("El horizonte debe ser un entero entre 1 y 90 días.")
    if X_df is not None and not X_df.empty:
        raise DataValidationError("Esta versión no utiliza regresores externos.")
    if retrain:
        warnings.warn("Los modelos se ajustan en cada ejecución; no se usa caché.", UserWarning)
    data = preprocess_data(df)
    if model == "seasonal":
        rows = []
        for product, group in data.groupby("unique_id", sort=True):
            values = group.sort_values("ds")["y"].to_numpy(dtype=float)
            pattern = values[-7:] if len(values) >= 7 else np.array([values.mean()])
            for i, date in enumerate(pd.date_range(group["ds"].max() + pd.Timedelta(days=1), periods=h)):
                rows.append({
                    "unique_id": product, "ds": date, "yhat": float(pattern[i % len(pattern)]),
                    "yhat_lower": np.nan, "yhat_upper": np.nan,
                })
        result = pd.DataFrame(rows)
    elif model == "autoarima":
        try:
            from statsforecast import StatsForecast
            from statsforecast.models import AutoARIMA
        except ImportError as exc:
            raise RuntimeError(
                "AutoARIMA requiere: python -m pip install -r requirements_models.txt"
            ) from exc
        season = 7 if data.groupby("unique_id").size().min() >= 14 else 1
        forecaster = StatsForecast(models=[AutoARIMA(season_length=season)], freq="D", n_jobs=1)
        result = forecaster.forecast(df=data, h=h, level=[90]).reset_index(drop=True)
        result = result.rename(columns={
            "AutoARIMA": "yhat", "AutoARIMA-lo-90": "yhat_lower", "AutoARIMA-hi-90": "yhat_upper",
        })[["unique_id", "ds", "yhat", "yhat_lower", "yhat_upper"]]
        if not np.isfinite(result[["yhat", "yhat_lower", "yhat_upper"]].to_numpy()).all():
            raise RuntimeError("AutoARIMA no devolvió un pronóstico finito.")
        result[["yhat", "yhat_lower", "yhat_upper"]] = result[
            ["yhat", "yhat_lower", "yhat_upper"]
        ].clip(lower=0)
    else:
        raise DataValidationError("Modelo desconocido. Usa 'seasonal' o 'autoarima'.")
    result.attrs["model"] = model
    return result.sort_values(["unique_id", "ds"]).reset_index(drop=True)


def backtest(df: pd.DataFrame, h: int = 7, model: str = "seasonal") -> pd.DataFrame:
    """One chronological holdout, fitted only on dates before the evaluation."""
    if isinstance(h, bool) or not isinstance(h, int) or not 1 <= h <= 90:
        raise DataValidationError("El horizonte debe ser un entero entre 1 y 90 días.")
    data = preprocess_data(df)
    split = data["ds"].max() - pd.Timedelta(days=h)
    train, actual = data[data["ds"] <= split], data[data["ds"] > split]
    if train.groupby("unique_id").size().reindex(data["unique_id"].unique(), fill_value=0).min() < 2:
        raise DataValidationError("Necesitas al menos horizonte + 2 días por producto para evaluar.")
    predicted = train_and_forecast(train, h=h, model=model)
    joined = actual.merge(predicted, on=["unique_id", "ds"], validate="one_to_one")
    if len(joined) != len(actual):
        raise DataValidationError("La evaluación no cubre todos los días reservados.")
    rows = []
    for product, group in joined.groupby("unique_id", sort=True):
        error = (group["y"] - group["yhat"]).abs()
        total = group["y"].sum()
        rows.append({
            "Producto": product, "MAE (unidades)": float(error.mean()),
            "WAPE (%)": float(100 * error.sum() / total) if total else np.nan,
            "Días evaluados": len(group),
        })
    return pd.DataFrame(rows)


def forecast_csv(forecast: pd.DataFrame) -> str:
    """CSV for spreadsheet import; product names cannot become formulas."""
    export = forecast.copy()
    export["ds"] = pd.to_datetime(export["ds"]).dt.strftime("%Y-%m-%d")
    export["unique_id"] = export["unique_id"].map(
        lambda value: "'" + str(value) if str(value).lstrip().startswith(("=", "+", "-", "@"))
        else str(value)
    )
    return export.to_csv(index=False)


def save_to_gsheets(forecast_df: pd.DataFrame, sheet_id: str):
    """Compatibility entry point; Sheets dependencies are imported only on request."""
    from src.integrations import save_to_gsheets as save
    return save(forecast_df, sheet_id)


if __name__ == "__main__":
    raise SystemExit("Usa: python forecast_cli.py --demo")
