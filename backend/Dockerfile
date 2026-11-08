# Backend image for any container host (Hugging Face Docker Space, Cloud Run, Oracle VM, your own machine).
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hf YOLO_CONFIG_DIR=/tmp/ultralytics
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# CPU-only torch keeps the image small (~1 GB smaller than the CUDA build)
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt
COPY app ./app
COPY scripts ./scripts
ENV ENVIRONMENT=production UPLOAD_DIR=/tmp/uploads
# most hosts inject $PORT; Hugging Face Spaces expects 7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers"]
