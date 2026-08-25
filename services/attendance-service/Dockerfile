FROM python:3.12-slim

WORKDIR /app

COPY libs/shared-core /shared-core
RUN --mount=type=cache,target=/root/.cache/pip pip install --default-timeout=1000 /shared-core

COPY services/attendance-service/pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/pip pip install --default-timeout=1000 .

COPY services/attendance-service/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
