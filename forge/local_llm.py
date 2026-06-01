"""
forge.local_llm
===============
GGUF model downloader, manager, and local llama.cpp inference server.

Enables fully offline AI game generation — no cloud API keys needed.
Downloads free GGUF models from HuggingFace and runs inference locally
via llama.cpp's HTTP server (CPU or GPU).

Quick start
-----------
    voxelforge model download llama3.2-3b   # ~2 GB
    voxelforge serve --model llama3.2-3b    # start server on :8090
    voxelforge llm "Write a dungeon quest" --provider local

From Python:
    from forge.local_llm import ModelManager, InferenceServer
    mgr = ModelManager()
    mgr.download("llama3.2-3b")
    srv = InferenceServer(mgr)
    srv.start("llama3.2-3b")
    print(srv.chat("Write a dungeon game quest"))
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests


# ---------------------------------------------------------------------------
# Model catalog
# ---------------------------------------------------------------------------

@dataclass
class ModelSpec:
    id:           str
    name:         str
    hf_repo:      str
    hf_file:      str
    size_gb:      float
    ctx_len:      int
    ram_gb:       float
    gpu_vram_gb:  float
    quant:        str
    tags:         List[str] = field(default_factory=list)
    description:  str = ""


MODEL_CATALOG: Dict[str, ModelSpec] = {
    "smollm2-360m": ModelSpec(
        id="smollm2-360m", name="SmolLM2 360M (ultra-tiny CPU)",
        hf_repo="HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
        hf_file="smollm2-360m-instruct-q8_0.gguf",
        size_gb=0.4, ctx_len=8192, ram_gb=1.0, gpu_vram_gb=0.5,
        quant="Q8_0", tags=["tiny","cpu","fast"],
        description="Smallest usable model. Runs on any hardware.",
    ),
    "smollm2-1.7b": ModelSpec(
        id="smollm2-1.7b", name="SmolLM2 1.7B (small CPU)",
        hf_repo="HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
        hf_file="smollm2-1.7b-instruct-q4_k_m.gguf",
        size_gb=1.1, ctx_len=8192, ram_gb=2.0, gpu_vram_gb=1.5,
        quant="Q4_K_M", tags=["small","cpu","fast"],
        description="Good balance of speed and quality on CPU.",
    ),
    "llama3.2-1b": ModelSpec(
        id="llama3.2-1b", name="Llama 3.2 1B Instruct (tiny CPU)",
        hf_repo="bartowski/Llama-3.2-1B-Instruct-GGUF",
        hf_file="Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        size_gb=0.8, ctx_len=8192, ram_gb=2.0, gpu_vram_gb=1.0,
        quant="Q4_K_M", tags=["tiny","cpu","meta"],
        description="Meta Llama 3.2 1B — excellent for minimal-hardware CPU inference.",
    ),
    "llama3.2-3b": ModelSpec(
        id="llama3.2-3b", name="Llama 3.2 3B Instruct (small CPU) ★ recommended",
        hf_repo="bartowski/Llama-3.2-3B-Instruct-GGUF",
        hf_file="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        size_gb=2.0, ctx_len=8192, ram_gb=4.0, gpu_vram_gb=2.5,
        quant="Q4_K_M", tags=["small","cpu","meta","recommended"],
        description="Best CPU-only model for game asset generation. Recommended default.",
    ),
    "phi3-mini": ModelSpec(
        id="phi3-mini", name="Phi-3 Mini 4K (small CPU)",
        hf_repo="microsoft/Phi-3-mini-4k-instruct-gguf",
        hf_file="Phi-3-mini-4k-instruct-q4.gguf",
        size_gb=2.2, ctx_len=4096, ram_gb=4.0, gpu_vram_gb=3.0,
        quant="Q4", tags=["small","cpu","coding"],
        description="Microsoft Phi-3 — strong at code generation on CPU.",
    ),
    "qwen2.5-3b": ModelSpec(
        id="qwen2.5-3b", name="Qwen 2.5 3B Instruct (small, 32K ctx)",
        hf_repo="Qwen/Qwen2.5-3B-Instruct-GGUF",
        hf_file="qwen2.5-3b-instruct-q4_k_m.gguf",
        size_gb=2.0, ctx_len=32768, ram_gb=4.0, gpu_vram_gb=2.5,
        quant="Q4_K_M", tags=["small","cpu","long-context"],
        description="Qwen 2.5 3B — 32K context, great for long game scripts.",
    ),
    "gemma2-2b": ModelSpec(
        id="gemma2-2b", name="Gemma 2 2B Instruct (small CPU)",
        hf_repo="bartowski/gemma-2-2b-it-GGUF",
        hf_file="gemma-2-2b-it-Q4_K_M.gguf",
        size_gb=1.6, ctx_len=8192, ram_gb=3.0, gpu_vram_gb=2.0,
        quant="Q4_K_M", tags=["small","cpu","google"],
        description="Google Gemma 2 2B — compact and high quality on CPU.",
    ),
    "deepseek-r1-1.5b": ModelSpec(
        id="deepseek-r1-1.5b", name="DeepSeek R1 Distill 1.5B (reasoning CPU)",
        hf_repo="bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF",
        hf_file="DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        size_gb=1.0, ctx_len=32768, ram_gb=2.5, gpu_vram_gb=1.5,
        quant="Q4_K_M", tags=["tiny","cpu","reasoning"],
        description="DeepSeek R1 distilled — chain-of-thought reasoning in 1.5B.",
    ),
    "mistral-7b": ModelSpec(
        id="mistral-7b", name="Mistral 7B Instruct v0.3 (GPU recommended)",
        hf_repo="bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        hf_file="Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        size_gb=4.4, ctx_len=32768, ram_gb=8.0, gpu_vram_gb=5.0,
        quant="Q4_K_M", tags=["medium","gpu","creative"],
        description="Mistral 7B — excellent creative writing. Needs 8GB RAM or 5GB VRAM.",
    ),
    "llama3.1-8b": ModelSpec(
        id="llama3.1-8b", name="Llama 3.1 8B Instruct (GPU recommended, 128K ctx)",
        hf_repo="bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        hf_file="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        size_gb=4.9, ctx_len=131072, ram_gb=10.0, gpu_vram_gb=6.0,
        quant="Q4_K_M", tags=["medium","gpu","meta","long-context"],
        description="Llama 3.1 8B — 128K context, best quality for game generation with GPU.",
    ),
    "qwen2.5-7b": ModelSpec(
        id="qwen2.5-7b", name="Qwen 2.5 7B Instruct (GPU recommended)",
        hf_repo="Qwen/Qwen2.5-7B-Instruct-GGUF",
        hf_file="qwen2.5-7b-instruct-q4_k_m.gguf",
        size_gb=4.7, ctx_len=32768, ram_gb=8.0, gpu_vram_gb=5.5,
        quant="Q4_K_M", tags=["medium","gpu","coding"],
        description="Qwen 2.5 7B — top-tier coding and creative generation.",
    ),
    "deepseek-r1-7b": ModelSpec(
        id="deepseek-r1-7b", name="DeepSeek R1 Distill 7B (reasoning, GPU)",
        hf_repo="bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF",
        hf_file="DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        size_gb=4.7, ctx_len=32768, ram_gb=10.0, gpu_vram_gb=6.0,
        quant="Q4_K_M", tags=["medium","gpu","reasoning"],
        description="DeepSeek R1 7B distill — best reasoning for complex game logic.",
    ),
}


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def get_models_dir() -> Path:
    d = Path(os.environ.get("VFE_MODELS_DIR",
                             os.path.join(Path.home(), ".voxelforge", "models")))
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_llama_server() -> Optional[str]:
    """Locate the llama-server binary (llama.cpp HTTP server)."""
    env = os.environ.get("VFE_LLAMA_SERVER", "")
    if env and (shutil.which(env) or os.path.isfile(env)):
        return env

    candidates = [
        Path(__file__).parent.parent / "llama.cpp" / "build" / "bin" / "llama-server",
        Path(__file__).parent.parent / "llama.cpp" / "llama-server",
        Path("/usr/local/bin/llama-server"),
        Path("/usr/bin/llama-server"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)

    for name in ("llama-server", "llama-cpp-server", "llama.cpp"):
        found = shutil.which(name)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# ModelManager
# ---------------------------------------------------------------------------

class ModelManager:
    """Download and manage GGUF models on disk."""

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir) if models_dir else get_models_dir()
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def catalog(self) -> Dict[str, ModelSpec]:
        return MODEL_CATALOG

    def model_path(self, model_id: str) -> Optional[Path]:
        spec = MODEL_CATALOG.get(model_id)
        if not spec:
            return None
        p = self.models_dir / spec.hf_file
        return p if p.exists() else None

    def is_downloaded(self, model_id: str) -> bool:
        p = self.model_path(model_id)
        return p is not None and p.exists()

    def list_downloaded(self) -> List[Dict[str, Any]]:
        result = []
        for spec in MODEL_CATALOG.values():
            path = self.model_path(spec.id)
            if path and path.exists():
                result.append({
                    "id":          spec.id,
                    "name":        spec.name,
                    "path":        str(path),
                    "size_gb":     round(path.stat().st_size / 1e9, 2),
                    "quant":       spec.quant,
                    "tags":        spec.tags,
                    "description": spec.description,
                })
        return result

    def download(
        self,
        model_id:    str,
        progress_fn: Optional[Callable[[int, int, float], None]] = None,
        force:       bool = False,
        custom_url:  Optional[str] = None,
    ) -> Path:
        """Download a GGUF model from HuggingFace or a custom URL."""
        spec = MODEL_CATALOG.get(model_id)
        if spec:
            hf_repo   = spec.hf_repo
            hf_file   = spec.hf_file
        elif ":" in model_id:
            repo, hf_file = model_id.split(":", 1)
            hf_repo   = repo
        elif "/" in model_id:
            hf_repo = model_id
            hf_file = model_id.split("/")[-1] + ".gguf"
        else:
            valid = list(MODEL_CATALOG)
            raise ValueError(f"Unknown model: {model_id!r}. Valid IDs: {valid}")

        dest_path = self.models_dir / hf_file

        if dest_path.exists() and not force:
            print(f"[ModelManager] Already downloaded: {dest_path}")
            return dest_path

        url = custom_url or f"https://huggingface.co/{hf_repo}/resolve/main/{hf_file}"

        print(f"[ModelManager] Downloading {model_id}")
        print(f"  URL  : {url}")
        print(f"  Dest : {dest_path}")
        if spec:
            print(f"  Size : ~{spec.size_gb:.1f} GB ({spec.quant})")

        self._download_file(url, dest_path, progress_fn)
        print(f"\n[ModelManager] Download complete: {dest_path}")
        return dest_path

    def _download_file(
        self,
        url:         str,
        dest:        Path,
        progress_fn: Optional[Callable],
    ) -> None:
        tmp = dest.with_suffix(dest.suffix + ".part")
        headers: Dict[str, str] = {}
        start = 0
        if tmp.exists():
            start = tmp.stat().st_size
            if start > 0:
                headers["Range"] = f"bytes={start}-"
                print(f"  Resuming from {start:,} bytes")

        resp = requests.get(url, headers=headers, stream=True, timeout=60)
        if resp.status_code == 416:
            tmp.rename(dest)
            return
        if resp.status_code not in (200, 206):
            raise RuntimeError(f"HTTP {resp.status_code} for {url}")

        total_raw  = int(resp.headers.get("content-length", 0))
        total      = total_raw + start if start else total_raw
        downloaded = start
        t0         = time.time()
        last_print = t0

        with open(tmp, "ab" if start else "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_print >= 2.0:
                        elapsed    = max(0.001, now - t0)
                        speed_mbps = ((downloaded - start) / elapsed) / 1e6
                        pct        = (downloaded / total * 100) if total else 0.0
                        bar        = "█" * int(pct / 4) + "░" * (25 - int(pct / 4))
                        print(
                            f"\r  [{bar}] {pct:5.1f}%  "
                            f"{downloaded/1e9:.2f}/{total/1e9:.2f} GB  "
                            f"{speed_mbps:.1f} MB/s",
                            end="", flush=True,
                        )
                        last_print = now
                        if progress_fn:
                            progress_fn(downloaded, total, speed_mbps)
        tmp.rename(dest)

    def remove(self, model_id: str) -> bool:
        p = self.model_path(model_id)
        if p and p.exists():
            p.unlink()
            print(f"[ModelManager] Removed {p}")
            return True
        return False

    def info(self, model_id: str) -> Dict[str, Any]:
        spec = MODEL_CATALOG.get(model_id)
        if not spec:
            return {"error": f"Unknown model: {model_id}"}
        path = self.model_path(model_id)
        return {
            "id":            spec.id,
            "name":          spec.name,
            "hf_repo":       spec.hf_repo,
            "hf_file":       spec.hf_file,
            "size_gb":       spec.size_gb,
            "ctx_len":       spec.ctx_len,
            "ram_gb":        spec.ram_gb,
            "gpu_vram_gb":   spec.gpu_vram_gb,
            "quant":         spec.quant,
            "tags":          spec.tags,
            "description":   spec.description,
            "downloaded":    path is not None,
            "local_path":    str(path) if path else None,
            "local_size_gb": round(path.stat().st_size / 1e9, 2) if path else None,
        }

    def recommend_for_hardware(self) -> List[str]:
        """Return model IDs suited for the current machine's RAM."""
        try:
            import psutil
            ram_gb = psutil.virtual_memory().total / 1e9
        except ImportError:
            ram_gb = 8.0
        suitable = [s for s in MODEL_CATALOG.values() if s.ram_gb <= ram_gb * 0.75]
        suitable.sort(key=lambda s: (0 if not self.is_downloaded(s.id) else -1, s.size_gb))
        return [s.id for s in suitable]


# ---------------------------------------------------------------------------
# InferenceServer — wraps llama.cpp llama-server process
# ---------------------------------------------------------------------------

class InferenceServer:
    """
    Manages a local llama.cpp HTTP inference server.

    The server exposes an OpenAI-compatible API at:
        http://localhost:{port}/v1/chat/completions

    Supports CPU inference (AVX2/AVX512) and GPU offloading
    via CUDA, Metal (Apple Silicon), or Vulkan.

    Parameters
    ----------
    manager : ModelManager
        Used to resolve model paths.
    host : str
        Bind address (default 0.0.0.0 for Docker compatibility).
    port : int
        HTTP port (default 8090 to avoid conflict with VoxelForge API on 8080).
    n_gpu_layers : int
        Layers to offload to GPU. -1 = all layers (full GPU), 0 = CPU only.
    context_size : int
        Context window size (0 = use model default).
    threads : int
        CPU threads (0 = auto-detect).
    """

    DEFAULT_PORT = 8090

    def __init__(
        self,
        manager:      Optional[ModelManager] = None,
        host:         str = "0.0.0.0",
        port:         int = DEFAULT_PORT,
        n_gpu_layers: int = 0,
        context_size: int = 0,
        threads:      int = 0,
    ):
        self.manager      = manager or ModelManager()
        self.host         = host
        self.port         = port
        self.n_gpu_layers = n_gpu_layers
        self.context_size = context_size
        self.threads      = threads
        self._proc:   Optional[subprocess.Popen] = None
        self._model_id:    str = ""
        self._model_path:  str = ""

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.port}"

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ------------------------------------------------------------------
    def start(
        self,
        model_id:     str,
        wait_secs:    int = 30,
        extra_args:   Optional[List[str]] = None,
    ) -> bool:
        """
        Start the llama-server with a downloaded model.

        Parameters
        ----------
        model_id : str
            Catalog ID or absolute path to a .gguf file.
        wait_secs : int
            Seconds to wait for the server to become ready.
        extra_args : list[str], optional
            Additional llama-server CLI flags.

        Returns
        -------
        bool
            True if the server started successfully.
        """
        if self.running:
            print(f"[InferenceServer] Already running (model={self._model_id})")
            return True

        # Resolve model path
        if os.path.isfile(model_id):
            model_path = model_id
        else:
            p = self.manager.model_path(model_id)
            if p is None:
                print(f"[InferenceServer] Model not downloaded: {model_id}")
                print(f"  Run: voxelforge model download {model_id}")
                return False
            model_path = str(p)

        # Find llama-server binary
        server_bin = find_llama_server()
        if not server_bin:
            print("[InferenceServer] llama-server not found.")
            print("  Install llama.cpp: voxelforge inference install")
            return False

        # Build command
        cmd = [
            server_bin,
            "--model",  model_path,
            "--host",   self.host,
            "--port",   str(self.port),
            "--n-predict", "-1",
        ]
        if self.n_gpu_layers != 0:
            cmd += ["--n-gpu-layers", str(self.n_gpu_layers)]
        if self.context_size > 0:
            cmd += ["--ctx-size", str(self.context_size)]
        if self.threads > 0:
            cmd += ["--threads", str(self.threads)]
        if extra_args:
            cmd.extend(extra_args)

        print(f"[InferenceServer] Starting: {' '.join(cmd[:6])} ...")
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._model_id   = model_id
        self._model_path = model_path

        # Wait for readiness
        deadline = time.time() + wait_secs
        while time.time() < deadline:
            if not self.running:
                out = ""
                if self._proc and self._proc.stdout:
                    out = self._proc.stdout.read(2000)
                print(f"[InferenceServer] Process exited unexpectedly.\n{out}")
                return False
            try:
                resp = requests.get(f"{self.base_url}/health", timeout=2)
                if resp.status_code == 200:
                    print(f"[InferenceServer] Ready at {self.base_url}")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1.0)

        print(f"[InferenceServer] Timeout after {wait_secs}s — server did not respond")
        self.stop()
        return False

    def stop(self) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
            print("[InferenceServer] Stopped")

    # ------------------------------------------------------------------
    def chat(
        self,
        prompt:      str,
        system:      Optional[str] = None,
        max_tokens:  int   = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat prompt to the local server and return the response."""
        if not self.running:
            return ""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model":       self._model_id,
                    "messages":    messages,
                    "temperature": temperature,
                    "max_tokens":  max_tokens,
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            print(f"[InferenceServer] chat error: {exc}")
            return ""

    def health(self) -> Dict[str, Any]:
        try:
            requests.get(f"{self.base_url}/health", timeout=3)
            return {"status": "ok", "model": self._model_id, "port": self.port}
        except Exception:
            return {"status": "offline", "model": "", "port": self.port}

    def models(self) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return resp.json().get("data", [])
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Hardware detection helpers
# ---------------------------------------------------------------------------

def detect_gpu_backend() -> str:
    """
    Detect available GPU acceleration backend.
    Returns one of: "cuda", "metal", "vulkan", "cpu"
    """
    system = sys.platform

    # CUDA (NVIDIA)
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return "cuda"
        except Exception:
            pass

    # Metal (Apple Silicon / macOS)
    if system == "darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5,
            )
            if "Apple" in result.stdout or "Metal" in result.stdout:
                return "metal"
        except Exception:
            pass

    # Vulkan (Linux/Windows with a GPU)
    if shutil.which("vulkaninfo"):
        return "vulkan"

    return "cpu"


def detect_optimal_threads() -> int:
    """Return a reasonable thread count for CPU inference."""
    try:
        import os as _os
        count = _os.cpu_count() or 4
        # Use at most physical cores - 1
        return max(1, count - 1)
    except Exception:
        return 4


def detect_optimal_gpu_layers(model_id: str) -> int:
    """
    Estimate how many layers to offload to GPU based on available VRAM
    and the model's GPU VRAM requirement.
    """
    spec = MODEL_CATALOG.get(model_id)
    if not spec:
        return 0

    backend = detect_gpu_backend()
    if backend == "cpu":
        return 0

    # Try to detect available VRAM (CUDA)
    vram_gb = 0.0
    if backend == "cuda" and shutil.which("nvidia-smi"):
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                vram_mb = float(r.stdout.strip().split("\n")[0].strip())
                vram_gb = vram_mb / 1024
        except Exception:
            pass

    if vram_gb <= 0:
        # Assume enough VRAM if we have a GPU but can't measure
        return -1 if spec.gpu_vram_gb <= 8 else 32

    if vram_gb >= spec.gpu_vram_gb:
        return -1  # all layers
    # Partial offload
    fraction = vram_gb / spec.gpu_vram_gb
    return max(1, int(fraction * 32))  # rough estimate


# ---------------------------------------------------------------------------
# Build llama.cpp from source (one-time setup)
# ---------------------------------------------------------------------------

def install_llama_cpp(
    target_dir: Optional[str] = None,
    enable_cuda: bool = True,
    enable_metal: bool = True,
) -> bool:
    """
    Clone and build llama.cpp from source.

    Parameters
    ----------
    target_dir : str, optional
        Where to clone llama.cpp (default: alongside voxelforge).
    enable_cuda : bool
        Compile with CUDA support if nvcc is available.
    enable_metal : bool
        Compile with Metal support on macOS.

    Returns
    -------
    bool
        True if build succeeded.
    """
    if target_dir is None:
        target_dir = str(Path(__file__).parent.parent / "llama.cpp")

    target = Path(target_dir)

    # Check if already installed
    existing = find_llama_server()
    if existing:
        print(f"[install_llama_cpp] Already installed: {existing}")
        return True

    # Clone
    if not target.exists():
        print(f"[install_llama_cpp] Cloning llama.cpp to {target} ...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1",
             "https://github.com/ggerganov/llama.cpp.git", str(target)],
            check=False,
        )
        if result.returncode != 0:
            print("[install_llama_cpp] git clone failed")
            return False

    # Build with CMake
    build_dir = target / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake_flags = [
        "-DLLAMA_BUILD_SERVER=ON",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DCMAKE_BUILD_TYPE=Release",
    ]

    backend = detect_gpu_backend()
    if backend == "cuda" and enable_cuda and shutil.which("nvcc"):
        cmake_flags.append("-DGGML_CUDA=ON")
        print("[install_llama_cpp] Enabling CUDA support")
    elif backend == "metal" and enable_metal and sys.platform == "darwin":
        cmake_flags.append("-DGGML_METAL=ON")
        print("[install_llama_cpp] Enabling Metal support")
    elif backend == "vulkan":
        cmake_flags.append("-DGGML_VULKAN=ON")
        print("[install_llama_cpp] Enabling Vulkan support")
    else:
        print("[install_llama_cpp] Building CPU-only (AVX2)")

    print("[install_llama_cpp] Running cmake configure ...")
    r = subprocess.run(
        ["cmake", str(target), *cmake_flags],
        cwd=str(build_dir),
    )
    if r.returncode != 0:
        return False

    cpu_count = max(1, (os.cpu_count() or 2))
    print("[install_llama_cpp] Building (this may take several minutes) ...")
    r = subprocess.run(
        ["cmake", "--build", ".", "--config", "Release",
         "--target", "llama-server", "-j", str(cpu_count)],
        cwd=str(build_dir),
    )
    ok = r.returncode == 0
    if ok:
        server_bin = build_dir / "bin" / "llama-server"
        if not server_bin.exists():
            server_bin = build_dir / "llama-server"
        print(f"[install_llama_cpp] Built: {server_bin}")
    else:
        print("[install_llama_cpp] Build failed")
    return ok
