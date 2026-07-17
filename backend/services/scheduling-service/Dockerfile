FROM python:3.12-slim

WORKDIR /app

# Install shared-core first (path dependency, built from repo root context)
COPY libs/shared-core /shared-core
RUN pip install --no-cache-dir /shared-core

COPY services/scheduling-service/pyproject.toml .
RUN pip install --no-cache-dir .

COPY services/scheduling-service/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
