# VoxelForge — AI API Server
# ===========================
# Runs the FastAPI REST server that exposes all VoxelForge generation endpoints.
# The C game engine is NOT included here — this image is for headless asset generation only.
#
# Build:   docker build -t voxelforge-api -f docker/Dockerfile .
# Run:     docker run -p 8080:8080 -v $(pwd)/output:/app/generated_assets voxelforge-api

FROM python:3.11-slim

LABEL org.opencontainers.image.title="VoxelForge API"
LABEL org.opencontainers.image.description="AI-Powered Voxel World Builder REST API"
LABEL org.opencontainers.image.source="https://github.com/wwwbkgme-oss/voxelforge"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy Python package
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY forge/ ./forge/
COPY cli/    ./cli/
COPY setup.py .

RUN pip install --no-cache-dir -e .

# Assets output directory
RUN mkdir -p /app/generated_assets
ENV VOXELFORGE_ASSETS_DIR=/app/generated_assets

EXPOSE 8080

CMD ["uvicorn", "forge.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
