import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import numpy as np
from src.main import load_data, preprocess_data, train_and_forecast

# Set page config
st.set_page_config(
    page_title="Panadería Predictor",
    page_icon="🥖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {font-size:24px; color: #8B4513; font-weight: bold;}
    .sub-header {font-size:20px; color: #A0522D; margin-top: 20px;}
    .highlight {background-color: #FFF8DC; padding: 10px; border-radius: 5px; margin: 10px 0;}
    .stButton>button {background-color: #8B4513; color: white;}
    .stFileUploader>div>div>div>button {background-color: #8B4513; color: white;}
</style>
""", unsafe_allow_html=True)

def main():
    st.title("🥖 Panadería Predictor")
    st.markdown("### Pronóstico de ventas para tu panadería")
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("Configuración")
        st.markdown("### Cargar datos de ventas")
        
        # File uploader
        uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])
        
        # Date range selector
        st.markdown("### Período de pronóstico")
        forecast_days = st.slider("Días a predecir", 7, 30, 14, 1)
        
        # Confidence level
        confidence_level = st.slider("Nivel de confianza", 70, 99, 90, 1)
        
        # Example file download
        with st.expander("¿Necesitas un ejemplo de formato?"):
            st.write("Descarga este archivo de ejemplo y modifícalo con tus datos:")
            example_data = {
                'fecha': [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(10, 0, -1)],
                'producto': ['Pan Blanco'] * 5 + ['Pan Integral'] * 5,
                'cantidad': [120, 115, 125, 118, 122, 80, 85, 78, 82, 85]
            }
            example_df = pd.DataFrame(example_data)
            st.download_button(
                label="Descargar ejemplo CSV",
                data=example_df.to_csv(index=False).encode('utf-8'),
                file_name="ejemplo_ventas_panaderia.csv",
                mime="text/csv"
            )
    
    # Main content
    if uploaded_file is not None:
        # Load and preprocess data
        st.info("Procesando archivo...")
        
        # Read the uploaded file with explicit error handling
        try:
            raw_data = pd.read_csv(uploaded_file)
            st.success(f"✅ Archivo leído correctamente. Filas: {len(raw_data)}")
        except pd.errors.EmptyDataError:
            st.error("❌ El archivo está vacío. Por favor, sube un archivo con datos.")
            st.stop()
        except pd.errors.ParserError as e:
            st.error(f"❌ Error al parsear el archivo CSV: {str(e)}")
            st.stop()
        except Exception as e:
            st.error(f"❌ Error inesperado: {str(e)}")
            st.stop()
        
        # Show data preview
        st.subheader("📊 Vista previa de los datos")
        st.dataframe(raw_data.head(3))
        
        # Preprocess data with detailed error handling
        try:
            st.info("🔍 Procesando datos...")
            processed_data = preprocess_data(raw_data)
            
            if processed_data is None or processed_data.empty:
                st.error("❌ No se pudieron procesar los datos. Por favor verifica el formato del archivo.")
                st.stop()
                
            st.success(f"✅ Datos procesados. Productos únicos: {processed_data['unique_id'].nunique()}")
            
            products = processed_data['unique_id'].unique()
            
            # Generate forecast
            st.info("🔮 Generando pronóstico...")
            forecast = train_and_forecast(processed_data, None, forecast_days)
            
            if forecast is None or forecast.empty:
                st.error("❌ No se pudo generar el pronóstico. Verifica que tengas suficientes datos históricos.")
                st.stop()
                
            st.success("✅ Pronóstico generado exitosamente!")
            
            # Get current week and year
            current_date = datetime.now()
            current_week = current_date.isocalendar()[1]
            current_year = current_date.year
            
            # Tabs for each product
            tabs = st.tabs([f"📊 {product}" for product in products])
            
            # Container for production recommendations
            production_recommendations = []
            
            for i, product in enumerate(products):
                with tabs[i]:
                    # Filter data for current product
                    product_data = processed_data[processed_data['unique_id'] == product].copy()
                    product_forecast = forecast[forecast['unique_id'] == product].copy()
                    
                    # Convert dates to datetime if they're not already
                    if not pd.api.types.is_datetime64_any_dtype(product_data['ds']):
                        product_data['ds'] = pd.to_datetime(product_data['ds'])
                    if not pd.api.types.is_datetime64_any_dtype(product_forecast['ds']):
                        product_forecast['ds'] = pd.to_datetime(product_forecast['ds'])
                    
                    # Get last year's data for the same week
                    last_year_start = (current_date - pd.DateOffset(years=1) - pd.Timedelta(days=current_date.weekday())).date()
                    last_year_end = last_year_start + pd.Timedelta(days=6)
                    
                    # Filter historical data for the same week last year
                    last_year_data = product_data[
                        (product_data['ds'].dt.date >= last_year_start) & 
                        (product_data['ds'].dt.date <= last_year_end)
                    ].copy()
                    
                    # Create figure with two subplots
                    fig = make_subplots(
                        rows=2, cols=1,
                        subplot_titles=(
                            f'Pronóstico de ventas - {product}',
                            'Comparación con mismo período año anterior'
                        ),
                        vertical_spacing=0.2,
                        row_heights=[0.7, 0.3]
                    )
                    
                    # Add historical data (last 30 days)
                    last_30_days = product_data[product_data['ds'] >= (current_date - pd.Timedelta(days=30))]
                    fig.add_trace(
                        go.Scatter(
                            x=last_30_days['ds'],
                            y=last_30_days['y'],
                            mode='lines+markers',
                            name='Ventas históricas (últimos 30 días)',
                            line=dict(color='#1f77b4')
                        ),
                        row=1, col=1
                    )
                    
                    # Add forecast
                    fig.add_trace(
                        go.Scatter(
                            x=product_forecast['ds'],
                            y=product_forecast['yhat'],
                            mode='lines+markers',
                            name='Pronóstico',
                            line=dict(color='#2ca02c', dash='dash')
                        ),
                        row=1, col=1
                    )
                    
                    # Add confidence interval
                    fig.add_trace(
                        go.Scatter(
                            x=pd.concat([product_forecast['ds'], product_forecast['ds'][::-1]]),
                            y=pd.concat([product_forecast['yhat_upper'], product_forecast['yhat_lower'][::-1]]),
                            fill='toself',
                            fillcolor='rgba(46, 184, 46, 0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            showlegend=True,
                            name='Rango de confianza'
                        ),
                        row=1, col=1
                    )
                    
                    # Add last year's data for comparison
                    if not last_year_data.empty:
                        fig.add_trace(
                            go.Bar(
                                x=last_year_data['ds'].dt.strftime('%a'),
                                y=last_year_data['y'],
                                name=f'Semana {current_week-1} {current_year-1}',
                                marker_color='#ff7f0e',
                                opacity=0.7
                            ),
                            row=2, col=1
                        )
                    
                    # Add current forecast for comparison
                    forecast_week = product_forecast[
                        (product_forecast['ds'].dt.date >= current_date.date()) &
                        (product_forecast['ds'].dt.date <= (current_date + pd.Timedelta(days=6)).date())
                    ]
                    
                    if not forecast_week.empty:
                        fig.add_trace(
                            go.Bar(
                                x=forecast_week['ds'].dt.strftime('%a'),
                                y=forecast_week['yhat'],
                                name=f'Semana {current_week} {current_year} (Pronóstico)',
                                marker_color='#2ca02c',
                                opacity=0.7
                            ),
                            row=2, col=1
                        )
                    
                    # Update layout
                    fig.update_layout(
                        height=800,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=20, r=20, t=80, b=20)
                    )
                    
                    # Update y-axes titles
                    fig.update_yaxes(title_text="Unidades vendidas", row=1, col=1)
                    fig.update_yaxes(title_text="Unidades", row=2, col=1)
                    
                    # Show plot
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Calculate production recommendations
                    if not forecast_week.empty:
                        weekly_forecast = forecast_week['yhat'].sum()
                        weekly_min = forecast_week['yhat_lower'].sum()
                        weekly_max = forecast_week['yhat_upper'].sum()
                        
                        # Add to production recommendations
                        production_recommendations.append({
                            'Producto': product,
                            'Cantidad Recomendada': int(weekly_forecast),
                            'Mínimo Esperado': int(weekly_min),
                            'Máximo Esperado': int(weekly_max),
                            'Variación Semana Pasada': f"{((weekly_forecast - last_year_data['y'].sum()) / last_year_data['y'].sum() * 100):.1f}%" if not last_year_data.empty else "N/A"
                        })
                    
                    # Show detailed forecast table
                    with st.expander("Ver pronóstico detallado"):
                        forecast_display = product_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
                        forecast_display.columns = ['Fecha', 'Pronóstico', 'Mínimo', 'Máximo']
                        forecast_display['Fecha'] = forecast_display['Fecha'].dt.strftime('%Y-%m-%d %a')
                        st.dataframe(
                            forecast_display.style.format({
                                'Pronóstico': '{:.0f}',
                                'Mínimo': '{:.0f}',
                                'Máximo': '{:.0f}'
                            }),
                            use_container_width=True
                        )
                    
                    # Download button for this product's forecast
                    csv = forecast_week[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 Descargar pronóstico semanal - {product}",
                        data=csv,
                        file_name=f"pronostico_semanal_{product.lower().replace(' ', '_')}_{current_date.strftime('%Y%m%d')}.csv",
                        mime='text/csv',
                        key=f"dl_{product}"
                    )
            
            # Show production recommendations in a separate section
            if production_recommendations:
                st.markdown("---")
                st.markdown("## 📋 Recomendaciones de Producción para la Próxima Semana")
                st.markdown("Basado en el pronóstico y datos históricos, se recomienda preparar:")
                
                # Create columns for better layout
                cols = st.columns(len(production_recommendations))
                
                for idx, rec in enumerate(production_recommendations):
                    with cols[idx]:
                        st.metric(
                            label=rec['Producto'],
                            value=f"{rec['Cantidad Recomendada']} uds.",
                            delta=f"Rango: {rec['Mínimo Esperado']} - {rec['Máximo Esperado']} uds."
                        )
                
                # Add summary table
                st.markdown("### Resumen de Producción")
                df_rec = pd.DataFrame(production_recommendations)
                st.dataframe(
                    df_rec[['Producto', 'Cantidad Recomendada', 'Mínimo Esperado', 'Máximo Esperado', 'Variación Semana Pasada']],
                    column_config={
                        'Producto': 'Producto',
                        'Cantidad Recomendada': st.column_config.NumberColumn('Cantidad Recomendada', format='%d uds.'),
                        'Mínimo Esperado': st.column_config.NumberColumn('Mínimo Esperado', format='%d uds.'),
                        'Máximo Esperado': st.column_config.NumberColumn('Máximo Esperado', format='%d uds.'),
                        'Variación Semana Pasada': 'Variación vs. año pasado'
                    },
                    use_container_width=True
                )              
            # Add download button for full forecast (outside the product loop)
            full_forecast = forecast[['unique_id', 'ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
            full_forecast.columns = ['Producto', 'Fecha', 'Pronóstico', 'Límite inferior', 'Límite superior']
            full_forecast['Fecha'] = full_forecast['Fecha'].dt.strftime('%Y-%m-%d')
            
            st.download_button(
                label="📥 Descargar pronóstico completo (todos los productos)",
                data=full_forecast.to_csv(index=False, encoding='utf-8-sig'),
                file_name=f"pronostico_ventas_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
                
        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")
    else:
        # Show welcome message and instructions
        st.markdown("""
        ## Bienvenido al Panel de Pronóstico de Panadería
        
        Esta herramienta te ayuda a predecir las ventas futuras de tus productos de panadería.
        
        ### Cómo empezar:
        1. Sube un archivo CSV con tus datos históricos de ventas
        2. Configura el período de pronóstico y el nivel de confianza
        3. ¡Obtén tus pronósticos y visualizaciones!
        
        ### Requisitos del archivo CSV:
        - Debe contener columnas para fecha, producto y cantidad vendida
        - Formato de fecha recomendado: AAAA-MM-DD
        - Puedes descargar un archivo de ejemplo en el panel de la izquierda
        
        ### Consejos para mejores resultados:
        - Proporciona al menos 2-3 meses de datos históricos
        - Incluye todos los días, incluso si las ventas fueron cero
        - Si faltan datos, la herramienta intentará completarlos automáticamente
        """)
        
        # Add image or diagram
        st.image(
            "https://img.icons8.com/color/480/bakery.png",
            width=200,
            use_column_width=False
        )

if __name__ == "__main__":
    main()
