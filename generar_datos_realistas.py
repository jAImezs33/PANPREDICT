import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Configuración
np.random.seed(42)
productos = ['Pan Blanco', 'Pan Integral', 'Medialunas', 'Facturas', 'Tortas']
base_ventas = {
    'Pan Blanco': 100,
    'Pan Integral': 70,
    'Medialunas': 200,
    'Facturas': 150,
    'Tortas': 30
}

# Coeficientes de variación por día de la semana (0=Lunes, 6=Domingo)
coef_dia_semana = {
    0: 0.9,  # Lunes
    1: 0.95, # Martes
    2: 1.0,  # Miércoles
    3: 1.05, # Jueves
    4: 1.1,  # Viernes
    5: 1.4,  # Sábado
    6: 1.5   # Domingo
}

# Festivos en 2025 (mes-01 para el primer día del mes)
festivos = [
    '2025-01-01', '2025-01-06',  # Año Nuevo, Reyes
    '2025-04-17', '2025-04-18',  # Jueves y Viernes Santo
    '2025-05-01',                # Día del Trabajo
    '2025-08-15',                # Asunción
    '2025-10-12',                # Día de la Hispanidad
    '2025-11-01',                # Todos los Santos
    '2025-12-06', '2025-12-08', '2025-12-25'  # Constitución, Inmaculada, Navidad
]

# Generar fechas
fecha_inicio = '2025-01-01'
fecha_fin = '2025-03-31'
dates = pd.date_range(fecha_inicio, fecha_fin)

# Función para generar datos
generar_datos = []
for fecha in dates:
    dia_semana = fecha.weekday()
    es_festivo = fecha.strftime('%Y-%m-%d') in festivos
    
    for producto in productos:
        # Base de ventas para este producto
        venta_base = base_ventas[producto]
        
        # Ajuste por día de la semana
        venta_ajustada = venta_base * coef_dia_semana[dia_semana]
        
        # Ajuste por festivo (aumento del 30% en festivos)
        if es_festivo:
            venta_ajustada *= 1.3
        
        # Ajuste por quincena (segunda quincena suele tener menos ventas)
        if fecha.day > 15:
            venta_ajustada *= 0.9
        
        # Variabilidad aleatoria (±15%)
        variacion = np.random.uniform(0.85, 1.15)
        venta_ajustada *= variacion
        
        # Redondear a entero
        cantidad = max(1, round(venta_ajustada))
        
        # Añadir a los datos
        generar_datos.append({
            'fecha': fecha.strftime('%Y-%m-%d'),
            'producto': producto,
            'cantidad': cantidad
        })

# Crear DataFrame y guardar
df = pd.DataFrame(generar_datos)
df.to_csv('ventas_panaderia_realista.csv', index=False)
print("Archivo 'ventas_panaderia_realista.csv' generado con éxito.")

# Mostrar un resumen
print("\nResumen de ventas por producto:")
print(df.groupby('producto')['cantidad'].sum())
