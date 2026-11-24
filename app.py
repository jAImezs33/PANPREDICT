"""PANPREDICT: an account-free local demo and explicit CSV upload."""
from datetime import date

import pandas as pd
import streamlit as st

from src.demo import make_demo_data
from src.main import backtest, forecast_csv, load_data, preprocess_data, train_and_forecast

st.set_page_config(page_title="PANPREDICT · Planifica tu obrador", page_icon="🥖", layout="wide")


def main():
    st.title("🥖 PANPREDICT")
    st.markdown("### Menos improvisación. Una previsión para tu obrador.")
    st.write("Explora tus ventas, estima los próximos días y comprueba el error con tu histórico.")

    with st.sidebar:
        st.header("Tu previsión")
        source = st.radio("Datos", ["Demo con datos sintéticos", "Mi archivo CSV"], key="source")
        uploaded = None
        if source == "Mi archivo CSV":
            uploaded = st.file_uploader("Histórico de ventas (UTF-8)", type=["csv"], key="sales")
        horizon = st.slider("Días de previsión", 1, 30, 8, key="horizon")
        method = st.selectbox("Método", ["Referencia semanal", "AutoARIMA"], key="method")
        zero_missing = st.checkbox(
            "Tratar días ausentes como cero ventas", value=False, key="zero_missing",
            help="Márcalo solo si sabes que los huecos representan días sin ventas.",
        )
        st.download_button(
            "Descargar CSV de ejemplo",
            make_demo_data().to_csv(index=False, sep=";").encode("utf-8-sig"),
            "ventas_demo.csv", "text/csv", key="sample",
        )
        st.caption("La demo funciona sin API, Google Sheets ni Telegram.")

    demo = source == "Demo con datos sintéticos"
    if demo:
        st.info("DEMO · Historial sintético de tres productos. No representa ventas ni resultados reales.")
        raw = make_demo_data()
    elif uploaded is None:
        st.info("Sube un CSV con fecha, articulo y unidades. También se aceptan producto/cantidad.")
        st.code("fecha;articulo;unidades\n2026-10-01;Barra;110\n2026-10-02;Barra;0", language="text")
        return
    else:
        try:
            raw = load_data(uploaded)
        except (ValueError, OSError) as exc:
            st.error(str(exc))
            return

    model = "seasonal" if method == "Referencia semanal" else "autoarima"
    try:
        history = preprocess_data(raw, missing_days="zero" if zero_missing else "error")
        forecast = train_and_forecast(history, h=horizon, model=model)
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
        return

    cutoff = history["ds"].max().date()
    a, b, c = st.columns(3)
    a.metric("Productos", history["unique_id"].nunique())
    b.metric("Última venta registrada", cutoff.strftime("%d/%m/%Y"))
    c.metric("Días previstos", horizon)
    st.caption("La previsión empieza después del último día del archivo, no después de hoy.")
    if not demo and (date.today() - cutoff).days > 7:
        st.warning("El histórico termina hace más de siete días. Actualízalo para planificar fechas actuales.")
    if model == "seasonal":
        st.caption(
            "Referencia semanal: repite los últimos siete días. Con menos de siete días usa su media. "
            "No se calculan intervalos de confianza para este método."
        )
    else:
        st.caption("AutoARIMA: intervalos del 90% estimados por el modelo; no garantizan ventas futuras.")

    overview, detail, quality = st.tabs(["Plan del obrador", "Histórico y detalle", "Comprobar error"])
    with overview:
        st.subheader("Ventas previstas por producto")
        summary = forecast.groupby("unique_id", as_index=False)["yhat"].sum()
        summary.columns = ["Producto", "Unidades previstas"]
        st.dataframe(summary, hide_index=True, use_container_width=True)
        st.subheader("Previsión diaria")
        daily = forecast.pivot(index="ds", columns="unique_id", values="yhat")
        st.line_chart(daily)
        st.download_button(
            "Descargar previsión completa", forecast_csv(forecast).encode("utf-8-sig"),
            "pronostico.csv", "text/csv", key="forecast_download",
        )
        st.caption(
            "Las ventas observadas pueden estar limitadas por falta de existencias. "
            "Revisa stock, cierres y pedidos antes de decidir cuánto producir."
        )

    with detail:
        product = st.selectbox("Producto", sorted(history["unique_id"].unique()), key="product")
        observed = history[history["unique_id"] == product].set_index("ds")["y"].tail(42)
        predicted = forecast[forecast["unique_id"] == product].set_index("ds")["yhat"]
        chart = pd.concat([observed.rename("Ventas observadas"), predicted.rename("Previsión")], axis=1)
        st.line_chart(chart)
        table = forecast[forecast["unique_id"] == product].copy()
        table["ds"] = table["ds"].dt.strftime("%Y-%m-%d")
        columns = ["ds", "yhat"] if model == "seasonal" else ["ds", "yhat", "yhat_lower", "yhat_upper"]
        st.dataframe(table[columns].rename(columns={
            "ds": "Fecha", "yhat": "Previsión", "yhat_lower": "Límite inferior 90%",
            "yhat_upper": "Límite superior 90%",
        }), hide_index=True, use_container_width=True)
        with st.expander("Ver histórico validado"):
            st.dataframe(history, hide_index=True, use_container_width=True)

    with quality:
        st.write(
            "Reservamos los últimos siete días, ajustamos el método con el histórico anterior "
            "y comparamos la previsión con las ventas que sí ocurrieron."
        )
        if st.button("Evaluar con los últimos 7 días", key="evaluate"):
            try:
                evaluation = backtest(history, h=7, model=model)
                st.dataframe(evaluation, hide_index=True, use_container_width=True)
                st.caption(
                    "MAE: error medio en unidades. WAPE: error absoluto total dividido por ventas totales. "
                    "Sin ventas, WAPE no se define. Es una única ventana de evaluación."
                )
                if demo:
                    st.caption("El error de estos datos sintéticos no demuestra rendimiento en un negocio real.")
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))


if __name__ == "__main__":
    main()
