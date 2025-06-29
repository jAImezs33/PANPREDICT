# Pan-Predict 90 🥖

**Predicción exprés de producción para panaderías y pastelerías artesanas.**

Este proyecto es un micro-servicio diseñado para tomar un CSV de ventas diarias de un TPV, entrenar un modelo de serie temporal y generar un pronóstico de producción a 8 días vista. Los resultados se guardan en una hoja de Google Sheets y se envía una notificación diaria a Telegram con la producción recomendada.

## ✨ Características

- **Ingesta de Datos**: Lee archivos CSV de ventas con formato `fecha;articulo;unidades`.
- **Preprocesamiento Automático**: Limpia datos, rellena fechas faltantes y elimina outliers.
- **Enriquecimiento de Datos (Opcional)**: Añade festivos nacionales de España y datos de temperatura máxima como características externas.
- **Modelado Inteligente**: Utiliza `statsforecast` (AutoARIMA) para series de datos robustas y `prophet` como fallback para series más cortas.
- **Persistencia de Modelos**: Guarda el modelo entrenado para acelerar los pronósticos diarios, con opción de reentrenamiento.
- **Salida a Google Sheets**: Escribe el pronóstico en una hoja de Google Sheets para fácil acceso y visualización.
- **Notificaciones a Telegram**: Envía un resumen diario del pronóstico a un chat de Telegram.
- **Contenerización**: Incluye un `Dockerfile` para un despliegue fácil y reproducible.

## 🛠️ Pila Tecnológica

- Python 3.11
- Pandas
- StatsForecast / Prophet
- GSpread para Google Sheets API
- python-telegram-bot
- Docker

---

## 🚀 Cómo Empezar

### 1. Prerrequisitos

- Python 3.11 o superior
- Docker (recomendado para un despliegue sencillo)
- Credenciales para Google Cloud (cuenta de servicio) y Telegram (token de bot).

### 2. Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd pan-predict-90
    ```

2.  **Instala las dependencias:**
    Se recomienda crear un entorno virtual.
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

### 3. Configuración del Entorno

1.  **Crea un archivo `.env`** a partir de la plantilla:
    ```bash
    cp config_template.env .env
    ```

2.  **Edita el archivo `.env`** y añade tus credenciales:

    - `GOOGLE_SERVICE_ACC_JSON`: El contenido completo del archivo JSON de tu cuenta de servicio de Google. Debe ser una sola línea. Puedes usar una herramienta para convertir el JSON a una sola línea.
    - `TELEGRAM_TOKEN`: El token de tu bot de Telegram.
    - `CHAT_ID`: El ID del chat de Telegram donde se enviarán las notificaciones.
    - `GOOGLE_SHEET_ID`: El ID de la hoja de cálculo de Google Sheets donde se guardará el pronóstico.

### 4. Prepara tus Datos

- Coloca tu archivo de ventas en el directorio `data/`. El archivo debe llamarse `ventas.csv` (o el nombre que prefieras, lo pasarás como argumento).
- El CSV debe estar separado por punto y coma (`;`) y tener las columnas: `fecha`, `articulo`, `unidades`.

---

## 🏃‍♂️ Cómo Ejecutar

### Usando el Script CLI

Puedes ejecutar el pipeline completo desde la línea de comandos. Es la forma más flexible de probar y depurar.

```bash
python forecast_cli.py --csv data/ventas.csv --send
```

**Argumentos disponibles:**

- `--csv` (requerido): Ruta al archivo CSV de ventas.
- `--sheet-id` (opcional): ID de la hoja de Google Sheets. Si no se especifica, se usará el valor del archivo `.env`.
- `--retrain` (opcional): Forza el reentrenamiento del modelo, ignorando cualquier versión guardada.
- `--send` (opcional): Envía una notificación a Telegram después de generar el pronóstico.

### Usando Docker (Recomendado)

Docker simplifica la ejecución, ya que empaqueta la aplicación y todas sus dependencias.

1.  **Construye la imagen de Docker:**
    ```bash
    docker build -t pan-predict .
    ```

2.  **Ejecuta el contenedor:**
    Asegúrate de que tu archivo `.env` está completo. El siguiente comando monta el directorio `data` y pasa las variables de entorno al contenedor.

    ```bash
    docker run --rm --env-file .env -v "$(pwd)/data":/app/data pan-predict
    ```

    Este comando ejecutará el `entrypoint.sh`, que a su vez llama a `src/main.py` y `src/send_telegram.py`.

    *Nota: El `entrypoint.sh` por defecto no usa los argumentos del CLI. Para una ejecución parametrizada dentro de Docker, deberás modificar el `entrypoint.sh` o pasar los argumentos al final del comando `docker run`.*

---

##  validating

El proyecto incluye un notebook `validate.ipynb` que te permite ejecutar y visualizar los pasos clave del proceso de pronóstico de forma interactiva. Es una excelente herramienta para entender cómo funcionan el preprocesamiento, el modelado y la generación de características.
