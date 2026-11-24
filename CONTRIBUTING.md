# Contribuir a PANPREDICT

Bienvenidas contribuciones en español o inglés. Buscamos mejoras útiles y
verificables; no dividir cambios artificialmente para contar PR.

## Preparación

1. Haz un fork y crea una rama desde main.
2. Usa Python 3.11 y un entorno virtual.
3. Instala requirements_dev.txt; añade requirements_models.txt para AutoARIMA.
4. Ejecuta python -m pytest -q y python forecast_cli.py --demo --backtest.

## Antes de proponer un cambio

- Busca incidencias y propuestas existentes para evitar duplicados.
- Para una funcionalidad nueva, describe el problema y un ejemplo.
- Para un error, aporta CSV sintético mínimo, comando, resultado esperado y
  obtenido. Indica sistema operativo y versiones.
- No adjuntes ventas reales, datos personales, tokens ni credenciales.
- Añade una prueba cuando corrijas procesamiento o modelos.
- Evita cambios de formato ajenos al problema.

## En la PR

Describe qué fallo resuelve, cómo cambia el comportamiento y cómo lo comprobaste.
Aclara si cambia el CSV, días ausentes o dependencias.
Las pruebas y revisión deben pasar antes de fusionar.

## Áreas útiles

- Ejemplos sintéticos de CSV de TPV.
- Pruebas y documentación de instalación.
- Evaluación temporal con más ventanas y comparación entre métodos.
- Accesibilidad y claridad de errores.

Una descarga, estrella o cuenta de prueba no equivale a uso recurrente.
No atribuyas ahorros o precisión sin una evaluación reproducible.
