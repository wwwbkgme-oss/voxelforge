#!/usr/bin/env bash
# VoxelForge Inference Server entrypoint
# Starts llama-server with environment-based configuration.
set -e

MODEL_DIR="${VFE_MODEL_PATH:-/models}"
HOST="${VFE_SERVER_HOST:-0.0.0.0}"
PORT="${VFE_SERVER_PORT:-8090}"
GPU_LAYERS="${VFE_N_GPU_LAYERS:-0}"
CTX="${VFE_CTX_SIZE:-4096}"
THREADS="${VFE_THREADS:-4}"
MODEL_FILE="${VFE_MODEL_FILE:-}"

# Auto-discover the first .gguf file if VFE_MODEL_FILE is not set
if [ -z "$MODEL_FILE" ]; then
    MODEL_FILE=$(find "$MODEL_DIR" -name "*.gguf" | head -1)
fi

if [ -z "$MODEL_FILE" ]; then
    echo "ERROR: No GGUF model found in $MODEL_DIR"
    echo "  Mount a directory containing a .gguf file to /models"
    echo "  or set VFE_MODEL_FILE to the full path."
    echo ""
    echo "  Example with Docker:"
    echo "    docker run -v \$HOME/.voxelforge/models:/models voxelforge-inference"
    echo ""
    echo "  Download a model first:"
    echo "    voxelforge model download llama3.2-3b"
    exit 1
fi

echo "====================================================="
echo "  VoxelForge Local Inference Server"
echo "====================================================="
echo "  Model   : $MODEL_FILE"
echo "  Host    : $HOST:$PORT"
echo "  GPU layers: $GPU_LAYERS"
echo "  Ctx size: $CTX"
echo "  Threads : $THREADS"
echo "====================================================="

ARGS=(
    --model        "$MODEL_FILE"
    --host         "$HOST"
    --port         "$PORT"
    --ctx-size     "$CTX"
    --threads      "$THREADS"
    --n-predict    -1
    --parallel     2
)

if [ "$GPU_LAYERS" -ne 0 ] 2>/dev/null; then
    ARGS+=(--n-gpu-layers "$GPU_LAYERS")
fi

exec llama-server "${ARGS[@]}"
