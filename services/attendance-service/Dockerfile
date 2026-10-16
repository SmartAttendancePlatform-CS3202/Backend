FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY libs/shared-core /shared-core
RUN uv pip install --system --no-cache /shared-core

COPY services/attendance-service/pyproject.toml .
RUN uv pip install --system --no-cache .

COPY services/attendance-service/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
