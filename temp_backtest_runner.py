import os
import sys
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error
import matplotlib.pyplot as plt
import seaborn as sns
import multiprocessing as mp

# Suppress SettingWithCopyWarning
pd.options.mode.chained_assignment = None

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.main import (
    preprocess_data,
    create_features_df,
    train_and_forecast
)

def main():
    """
    Main function to run the backtesting pipeline.
    """
    # Setup visualization
    sns.set(style="whitegrid")
    plt.rcParams['figure.figsize'] = (20, 10)

    print("--- 1. Librerías y funciones cargadas. ---")

    # Load and prepare data
    print("\n--- 2. Cargando y preparando el dataset... ---")
    df_raw = pd.read_csv('data/Bakery sales.csv')
    df_raw.columns = df_raw.columns.str.strip()
    df_raw.rename(columns={'date': 'fecha', 'article': 'articulo', 'Quantity': 'unidades'}, inplace=True)
    df_raw['fecha'] = pd.to_datetime(df_raw['fecha']).dt.date
    daily_sales = df_raw.groupby(['fecha', 'articulo'])['unidades'].sum().reset_index()
    print(f"Datos cargados y agregados. Total de registros: {len(daily_sales)}")
    print("Ejemplo de datos agregados:")
    print(daily_sales.head())

    # Split data
    print("\n--- 3. Dividiendo en Entrenamiento y Prueba... ---")
    daily_sales['fecha'] = pd.to_datetime(daily_sales['fecha'])
    cutoff_date = daily_sales['fecha'].max() - pd.Timedelta(days=30)
    train_df_raw = daily_sales[daily_sales['fecha'] <= cutoff_date]
    test_df_raw = daily_sales[daily_sales['fecha'] > cutoff_date]
    print(f"Datos de entrenamiento: hasta {cutoff_date.date()} ({len(train_df_raw)} registros)")
    print(f"Datos de prueba: desde {cutoff_date.date() + pd.Timedelta(days=1)} ({len(test_df_raw)} registros)")

    # Preprocess, train, and predict
    print("\n--- 4. Preprocesando, entrenando y prediciendo... (Esto puede tardar unos minutos) ---")
    train_df_processed = preprocess_data(train_df_raw)
    HORIZON = 30
    start_date = train_df_processed['ds'].min()
    end_date = train_df_processed['ds'].max() + pd.Timedelta(days=HORIZON)
    features_df = create_features_df(start_date, end_date)
    forecast_df = train_and_forecast(train_df_processed, X_df=features_df, h=HORIZON, retrain=True)
    print("Pronóstico de 30 días generado.")
    print("Ejemplo de pronóstico:")
    print(forecast_df.head())

    # Evaluate performance
    print("\n--- 5. Evaluando el rendimiento (mAPE)... ---")
    test_df_raw.rename(columns={'fecha': 'ds', 'articulo': 'unique_id', 'unidades': 'y_true'}, inplace=True)
    comparison_df = pd.merge(
        forecast_df[['ds', 'unique_id', 'yhat']],
        test_df_raw[['ds', 'unique_id', 'y_true']],
        on=['ds', 'unique_id']
    )

    # Filter out rows where y_true is 0 to avoid infinite MAPE
    comparison_df = comparison_df[comparison_df['y_true'] > 0]

    if not comparison_df.empty:
        mape = mean_absolute_percentage_error(comparison_df['y_true'], comparison_df['yhat'])
        print(f'======================================================')
        print(f'Mean Absolute Percentage Error (mAPE) Global: {mape:.2%}')
        print(f'======================================================')

        mape_per_article = comparison_df.groupby('unique_id').apply(
            lambda x: mean_absolute_percentage_error(x['y_true'], x['yhat'])
        ).sort_values(ascending=False)
        print("\n--- mAPE por Artículo (Top 10 con más error) ---")
        print(mape_per_article.head(10).apply(lambda x: f"{x:.2%}"))

        # Visualize results
        print("\n--- 6. Generando gráfico de visualización... ---")
        try:
            PRODUCTO_A_VISUALIZAR = mape_per_article.index[0]
            hist_train = train_df_processed[train_df_processed['unique_id'] == PRODUCTO_A_VISUALIZAR].tail(90)
            hist_test = comparison_df[comparison_df['unique_id'] == PRODUCTO_A_VISUALIZAR]
            
            plt.figure()
            plt.plot(hist_train['ds'], hist_train['y'], label='Ventas Históricas (Entrenamiento)', color='royalblue')
            plt.plot(hist_test['ds'], hist_test['y_true'], label='Ventas Reales (Prueba)', color='green', marker='o', linestyle='None')
            plt.plot(hist_test['ds'], hist_test['yhat'], label='Pronóstico', color='darkorange', linestyle='--')
            
            plt.title(f'Backtesting para: {PRODUCTO_A_VISUALIZAR} (mAPE: {mape_per_article.loc[PRODUCTO_A_VISUALIZAR]:.2%})', fontsize=16)
            plt.xlabel('Fecha')
            plt.ylabel('Unidades')
            plt.legend()
            
            output_path = 'backtesting_plot.png'
            plt.savefig(output_path)
            print(f"Gráfico guardado en: {output_path}")
            plt.close()

        except IndexError:
            print("No se pudo generar el gráfico: no hay datos de prueba para los artículos pronosticados.")
        except Exception as e:
            print(f"Ocurrió un error al generar el gráfico: {e}")
    else:
        print("No hay datos superpuestos entre el pronóstico y los datos de prueba para evaluar.")

if __name__ == "__main__":
    # On macOS and Windows, 'spawn' is the default, but it's good practice
    # to be explicit to avoid issues when code is run on different platforms.
    # The guard `if __name__ == "__main__"` is essential to prevent recursive
    # process creation.
    mp.set_start_method("spawn", force=True)
    main()
