import io
import numpy as np
import pandas as pd
import pytest
from src.demo import make_demo_data
from src.main import DataValidationError, backtest, forecast_csv, load_data, preprocess_data, train_and_forecast


def sales(values, product="Barra", start="2026-10-01"):
    return pd.DataFrame({"fecha": pd.date_range(start, periods=len(values), freq="D"),
                         "producto": product, "cantidad": values})


@pytest.mark.parametrize("separator", [",", ";", "\t"])
def test_csv_separators_and_product_identifiers(separator):
    content = separator.join(["date", "product", "quantity"]) + "\n"
    content += separator.join(["2026-10-01", "001", "0"]) + "\n"
    content += separator.join(["2026-10-02", "001", "4"]) + "\n"
    history = preprocess_data(load_data(io.StringIO(content)))
    assert history["unique_id"].tolist() == ["001", "001"]
    assert history["y"].tolist() == [0, 4]


def test_decimal_comma_and_spanish_dates():
    history = preprocess_data(load_data(io.StringIO(
        "fecha;articulo;unidades\n01/10/2026;Barra;1,5\n02/10/2026;Barra;0\n")))
    assert history["y"].tolist() == [1.5, 0.0]
    assert history["ds"].iloc[0] == pd.Timestamp("2026-10-01")


def test_zero_sales_are_preserved_and_duplicates_summed():
    raw = pd.concat([sales([0, 2]), sales([0, 3])], ignore_index=True)
    assert preprocess_data(raw)["y"].tolist() == [0, 5]


def test_does_not_mutate_uploaded_dataframe():
    raw = sales([0, 2])
    original = raw.copy(deep=True)
    preprocess_data(raw)
    pd.testing.assert_frame_equal(raw, original)


@pytest.mark.parametrize("bad", [-1, "abc", np.inf, -np.inf, np.nan, ""])
def test_invalid_quantities_are_rejected(bad):
    with pytest.raises(DataValidationError, match="ventas"):
        preprocess_data(sales([bad, 2]))


def test_invalid_dates_are_rejected():
    raw = sales([1, 2]).astype({"fecha": str})
    raw.loc[0, "fecha"] = "2026-02-30"
    with pytest.raises(DataValidationError, match="fechas"):
        preprocess_data(raw)


@pytest.mark.parametrize("name", ["", "   ", None])
def test_empty_product_is_rejected(name):
    with pytest.raises(DataValidationError, match="productos"):
        preprocess_data(sales([1, 2], product=name))


def test_missing_days_require_explicit_choice():
    raw = sales([3, 4, 5]).iloc[[0, 2]]
    with pytest.raises(DataValidationError, match="Faltan 1"):
        preprocess_data(raw)
    assert preprocess_data(raw, missing_days="zero")["y"].tolist() == [3, 0, 5]


def test_stale_products_require_an_explicit_choice():
    raw = pd.concat([sales([2, 3], "A"), sales([4, 5, 6], "B")])
    with pytest.raises(DataValidationError, match="Faltan 1"):
        preprocess_data(raw)
    data = preprocess_data(raw, missing_days="zero")
    assert data.groupby("unique_id")["ds"].max().nunique() == 1
    assert data[data["unique_id"] == "A"]["y"].tolist() == [2, 3, 0]


def test_ambiguous_columns_are_rejected():
    raw = sales([1, 2])
    raw["articulo"] = "Other"
    with pytest.raises(DataValidationError, match="una sola"):
        preprocess_data(raw)


@pytest.mark.parametrize("horizon", [0, -1, 91, 1.5, True])
def test_invalid_horizon(horizon):
    with pytest.raises(DataValidationError, match="horizonte"):
        train_and_forecast(preprocess_data(sales([1, 2])), h=horizon)


def test_weekly_reference_repeats_last_week_without_fake_intervals():
    history = preprocess_data(sales(list(range(1, 15))))
    forecast = train_and_forecast(history, h=9)
    assert forecast["yhat"].tolist() == [8, 9, 10, 11, 12, 13, 14, 8, 9]
    assert forecast["ds"].min() == pd.Timestamp("2026-10-15")
    assert forecast["yhat_lower"].isna().all()
    assert forecast["yhat_upper"].isna().all()


def test_short_series_and_zero_series():
    history = preprocess_data(pd.concat([sales([0, 0], "A"), sales([2, 4], "B")]))
    forecast = train_and_forecast(history, h=3)
    assert forecast.groupby("unique_id")["yhat"].apply(list).to_dict() == {
        "A": [0, 0, 0], "B": [3, 3, 3]}


def test_backtest_excludes_future_sales_from_training():
    history = preprocess_data(sales([1] * 14 + [1000] * 7))
    metrics = backtest(history, h=7)
    assert metrics["MAE (unidades)"].iloc[0] == 999
    assert metrics["WAPE (%)"].iloc[0] == pytest.approx(99.9)
    assert metrics["Días evaluados"].iloc[0] == 7


def test_zero_sales_backtest():
    metrics = backtest(preprocess_data(sales([0] * 21)))
    assert metrics["MAE (unidades)"].iloc[0] == 0
    assert pd.isna(metrics["WAPE (%)"].iloc[0])


def test_backtest_rejects_too_short_history():
    with pytest.raises(DataValidationError, match="horizonte"):
        backtest(preprocess_data(sales([1] * 8)))


def test_csv_escapes_spreadsheet_formulas_in_product_names():
    forecast = train_and_forecast(preprocess_data(sales([1, 2], "=1+1")), h=1)
    assert "'=1+1" in forecast_csv(forecast)


def test_autoarima_optional_real_model():
    pytest.importorskip("statsforecast")
    history = preprocess_data(make_demo_data(days=28))
    forecast = train_and_forecast(history, h=3, model="autoarima")
    assert len(forecast) == 9
    assert forecast["ds"].min() == history["ds"].max() + pd.Timedelta(days=1)
    assert np.isfinite(forecast[["yhat", "yhat_lower", "yhat_upper"]].to_numpy()).all()
    assert forecast["yhat_lower"].le(forecast["yhat"]).all()
    assert forecast["yhat"].le(forecast["yhat_upper"]).all()
