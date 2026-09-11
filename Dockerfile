# Production Multi-Stage Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Production Image
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies for OpenCV & ONNX
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Limit ONNX Runtime / BLAS thread pools. Default behavior spawns a
# thread per CPU core, each with its own buffers - unnecessary memory
# overhead for single-request OCR inference on a small instance.
# NOTE: this Dockerfile is not currently what Render runs (render.yaml
# specifies runtime: python, so Render builds/runs natively). These are
# set here for parity if deployment ever switches to this image; the
# values that actually take effect today are the ones in render.yaml.
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV ORT_NUM_THREADS=1
ENV OCR_MAX_DIMENSION=1200

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]