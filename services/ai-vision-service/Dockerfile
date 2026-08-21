FROM python:3.12-slim

# Face-matching libraries often need build tools + OpenCV system deps.
# Uncomment as needed once you pick a library:
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential cmake libgl1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install system dependencies required for OpenCV and face processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Install shared-core first
COPY libs/shared-core /shared-core
RUN --mount=type=cache,target=/root/.cache/pip pip install --default-timeout=1000 /shared-core

# Install service dependencies
COPY services/ai-vision-service/pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/pip pip install --default-timeout=1000 .

COPY services/ai-vision-service/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]