FROM python:3.12-slim

WORKDIR /app

COPY libs/shared-core /shared-core
RUN pip install --default-timeout=1000 --no-cache-dir /shared-core

COPY services/ai-vision-service/pyproject.toml .
RUN pip install --default-timeout=1000 --no-cache-dir .

COPY services/ai-vision-service/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
