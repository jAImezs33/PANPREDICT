FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY forecast_cli.py entrypoint.sh ./
COPY examples ./examples
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
CMD ["--demo"]
