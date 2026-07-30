git FROM python:3.12-slim

# Face-matching libraries often need build tools + OpenCV system deps.
# Uncomment as needed once you pick a library:
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential cmake libgl1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs/shared-core /shared-core
RUN pip install --no-cache-dir /shared-core

COPY services/ai-vision-service/pyproject.toml .
RUN pip install --no-cache-dir .

COPY services/ai-vision-service/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
