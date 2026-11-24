# PANPREDICT 🥖

Previsión local de ventas para panaderías, con una demo sin cuentas ni claves.

**Estado: prototipo para pilotos.** Incluye datos sintéticos, validación de CSV,
una referencia semanal y AutoARIMA opcional. No hay resultados validados de ahorro,
reducción de desperdicio ni precisión en negocios reales.

English: local bakery sales forecasting with an account-free synthetic demo,
explicit missing-day handling and chronological holdout evaluation. Contributions
and bug reports in English or Spanish are welcome.

## Prueba rápida — Python 3.11

Desde la raíz del repositorio:

~~~bash
python -m venv .venv
~~~

Activa el entorno en Windows PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
~~~

En Linux o macOS:

~~~bash
source .venv/bin/activate
~~~

Instala y ejecuta la demo por terminal:

~~~bash
python -m pip install -r requirements.txt
python forecast_cli.py --demo --backtest
~~~

Se crea **output/pronostico.csv**. La demo no necesita servicios externos ni envía
datos a Google o Telegram.

Para usar la interfaz:

~~~bash
python -m pip install -r requirements_streamlit.txt
python -m streamlit run app.py --server.address 127.0.0.1
~~~

Abre la dirección local que indique Streamlit. La pantalla inicial muestra tres
productos de ejemplo; permite cambiar el horizonte, descargar la previsión y
evaluar los últimos siete días.

## Tus ventas

Usa UTF-8, separado por punto y coma, coma o tabulador:

~~~csv
fecha;articulo;unidades
2026-10-01;Barra;110
2026-10-02;Barra;0
2026-10-03;Barra;125
~~~

También se aceptan **producto/cantidad** o **date/product/quantity**.
Fechas: AAAA-MM-DD o DD/MM/AAAA. Con separador punto y coma se admite coma decimal.
Ejemplo completo: [examples/ventas_demo.csv](examples/ventas_demo.csv), siempre sintético.

~~~bash
python forecast_cli.py --csv ventas.csv --days 8 --output output/prevision.csv --backtest
~~~

Reglas:

- Se conservan los días con cero ventas.
- Varias filas del mismo producto y fecha se suman.
- Productos vacíos, cantidades negativas/no numéricas y fechas inválidas generan error.
- Los productos deben tener al menos dos días y finalizar en una fecha común.
- Los días ausentes **no se convierten automáticamente en cero**. Completa el
  histórico; si sabes que esos días no hubo ventas, utiliza **--missing-days zero**
  o la casilla equivalente en la interfaz.
- Las fechas previstas empiezan tras el último día del archivo, aunque sea antiguo.
- Horizontes: 1 a 90 días por terminal, 1 a 30 en la interfaz.
- Los nombres de producto que podrían ser fórmulas se escapan al exportar a CSV.

Incluye cierres con cero únicamente cuando corresponda. Una rotura de stock puede
ocultar demanda; no equivale a ausencia de demanda.

## Métodos y evaluación

**Referencia semanal (por defecto):** repite las ventas de los últimos siete días.
Con menos de siete días usa la media disponible. No inventa intervalos de confianza.

**AutoARIMA (opcional):**

~~~bash
python -m pip install -r requirements_models.txt
python forecast_cli.py --demo --model autoarima --backtest
~~~

Usa StatsForecast 2.x, con estacionalidad semanal si todos los productos tienen al
menos 14 días. Los intervalos del 90% son estimaciones del modelo, no garantías.
Un fallo se comunica; no se sustituye el modelo silenciosamente. Cada ejecución
ajusta el modelo de nuevo y no deserializa los antiguos archivos pickle.

**Evaluación:** reserva los últimos siete días y ajusta solo con fechas anteriores.
Informa MAE en unidades y WAPE en porcentaje por producto. WAPE queda sin definir
cuando las ventas de evaluación suman cero. Es una ventana, no una validación
exhaustiva. Los resultados sintéticos no acreditan rendimiento real.

No se usan festivos, clima ni Prophet en esta versión.

## Integraciones opcionales

El flujo local funciona sin ellas. La interfaz no realiza envíos externos.

Google Sheets:

~~~bash
python -m pip install -r requirements_integrations.txt
~~~

Copia **.env.example** como **.env** y configura **GOOGLE_SERVICE_ACC_JSON** con el
JSON completo de tu cuenta de servicio. Comparte la hoja con esa cuenta.
Esta orden reemplaza los datos de la pestaña **Pronóstico** de la hoja indicada:

~~~bash
python forecast_cli.py --csv ventas.csv --sheet-id ID_DE_TU_HOJA
~~~

Revisa el destino antes de ejecutarla. Se envían productos, fechas y previsiones.
Una variable **GOOGLE_SHEET_ID** heredada no inicia la publicación: se exige
**--sheet-id**.

Telegram requiere **TELEGRAM_TOKEN** y **CHAT_ID**:

~~~bash
python forecast_cli.py --csv ventas.csv --send
~~~

Solo se envía con **--send**: primera fecha prevista, con fecha exacta y texto plano.
No requiere Google Sheets. Las pruebas simulan Telegram; no envían mensajes.
No publiques tu **.env**, credenciales ni ventas reales.

## Docker — demo por terminal

~~~bash
docker build -t panpredict .
docker run --rm panpredict
~~~

Para conservar el resultado en Linux/macOS:

~~~bash
docker run --rm -v "$(pwd)/output:/app/output" panpredict --demo --backtest
~~~

En PowerShell:

~~~powershell
docker run --rm -v "${PWD}/output:/app/output" panpredict --demo --backtest
~~~

El contenedor base no incluye interfaz, AutoARIMA ni Google Sheets.
El entrypoint transmite los argumentos al CLI; no activa notificaciones.

## Desarrollo y pruebas

~~~bash
python -m pip install -r requirements_dev.txt
python -m pytest -q
~~~

Instala también **requirements_models.txt** para probar AutoARIMA real.
GitHub Actions configura la suite local en Linux/Windows y una comprobación
separada del modelo opcional. Revisa los resultados del commit correspondiente.

Los notebooks, scripts de depuración y el pickle anterior se conservan como
material histórico. Los puntos de entrada mantenidos son **app.py**,
**forecast_cli.py** y los módulos de **src/** utilizados por ambos.

- [Cómo contribuir](CONTRIBUTING.md)
- [Guía para un piloto](docs/PILOT.md)
- [Próximos pasos](docs/ROADMAP.md)
- [Cambios](CHANGELOG.md)

## Licencia

Código bajo [MIT](LICENSE). Las dependencias mantienen sus propias licencias.
Esto no convierte al proyecto en software validado para producción.
