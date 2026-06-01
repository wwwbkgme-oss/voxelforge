"""
forge.imagegen
==============
AI image and animation generation for VoxelForge.

Generates real AI sprites and animated spritesheets from text prompts using:
  - OpenRouter (300+ models: Grok Imagine, Seedance, DALL-E, Stable Diffusion, etc.)
  - OpenAI DALL-E (direct, as primary alternative)
  - Pixel art generator (pure Pillow, no API key — always available)

Flow (from acatovic/ai-game-studio):
  1. Text prompt → reference sprite (image model)
  2. Sprite + motion prompt → animated video frames (video model, optional)
  3. Chroma-key (#00b140) → transparent PNGs
  4. Frame selection → spritesheet (1×N PNG) + GIF preview

Requirements
------------
    pip install Pillow requests
    # Optional (for video frame extraction):
    # ffmpeg on PATH

Environment
-----------
    OPENROUTER_API_KEY=sk-or-v1-...   # Primary — gives access to 300+ models
    OPENAI_API_KEY=sk-...             # Fallback for DALL-E image generation

Usage
-----
>>> from forge.imagegen import SpriteGenerator
>>> gen = SpriteGenerator()
>>> result = gen.generate("pixel art medieval warrior, isometric view, 64x64")
>>> print(result.image_path)   # saved PNG sprite
>>> result.save_spritesheet("warrior_sheet.png")

>>> # Animated spritesheet
>>> anim = gen.generate_animated("warrior idle animation", frames=8)
>>> anim.save_gif("warrior_idle.gif")
"""

from __future__ import annotations

import base64
import io
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import requests

try:
    from PIL import Image, ImageDraw  # type: ignore
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENROUTER_BASE   = "https://openrouter.ai/api/v1"
OPENAI_BASE       = "https://api.openai.com/v1"

# Models in priority order
IMAGE_MODELS = [
    "x-ai/grok-2-image",                 # Grok 2 image generation
    "x-ai/grok-imagine-image-quality",   # Grok Imagine (high quality)
    "openai/dall-e-3",                    # DALL-E 3 via OpenRouter
    "stability-ai/stable-diffusion-3",   # SD3 via OpenRouter
    "black-forest-labs/flux-1.1-pro",    # FLUX 1.1 Pro via OpenRouter
]

VIDEO_MODELS = [
    {"id": "x-ai/grok-imagine-video",   "label": "Grok Imagine Video",  "duration": 2},
    {"id": "bytedance/seedance-2.0",     "label": "Seedance 2.0",        "duration": 4},
]

# Chroma-key green screen colour used in prompts
CHROMA_GREEN_HEX = "#00b140"
CHROMA_GREEN_RGB = (0, 177, 64)

CHROMA_IMAGE_DIRECTIVE = (
    "Place the subject on a perfectly flat solid pure chroma green background, "
    "hex #00b140 (RGB 0, 177, 64). The background must be one uniform color "
    "with no gradients, no shadows, no lighting variation, and no texture. "
    "The subject itself must contain no green elements that could conflict "
    "with chroma keying. Centered, full subject visible."
)

CHROMA_VIDEO_DIRECTIVE = (
    "Maintain the exact same flat solid pure chroma green background, "
    "hex #00b140, throughout the entire clip. No background changes, no "
    "environmental elements, no shadows on the background, no camera movement. "
    "The subject animates against the uniform green backdrop."
)

POLL_INTERVAL  = 3.0     # seconds between video job polls
POLL_MAX_TRIES = 100     # ~5 min cap


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SpriteResult:
    """Result of a sprite generation call."""
    image_path:   str              # absolute path to the generated PNG
    image_b64:    str              # base64-encoded PNG data
    prompt:       str
    model_used:   str
    width:        int
    height:       int
    frames:       List[str] = field(default_factory=list)   # additional frame paths
    has_alpha:    bool = False
    source:       str = "ai"  # "ai" | "pixel_art" | "cached"

    def to_pil(self) -> "Image.Image":
        """Load the generated image as a PIL Image."""
        if not _PIL_AVAILABLE:
            raise RuntimeError("Pillow required: pip install Pillow")
        data = base64.b64decode(self.image_b64)
        return Image.open(io.BytesIO(data)).convert("RGBA")

    def save_spritesheet(self, output_path: str,
                          frame_paths: Optional[List[str]] = None) -> str:
        """Assemble this sprite + optional extra frames into a 1×N spritesheet."""
        return build_spritesheet(
            [self.image_path] + (frame_paths or self.frames),
            output_path,
        )

    def save_gif(self, output_path: str,
                  frame_paths: Optional[List[str]] = None,
                  fps: int = 8) -> str:
        """Build a looping GIF from this sprite + extra frames."""
        return build_gif(
            [self.image_path] + (frame_paths or self.frames),
            output_path,
            fps=fps,
        )


@dataclass
class AnimationResult:
    """Result of an animation generation call (image → video → frames)."""
    frames:       List[str]        # paths to individual frame PNGs (transparent)
    spritesheet:  str              # path to assembled 1×N PNG spritesheet
    gif_path:     str              # path to looping GIF preview
    prompt:       str
    model_used:   str
    frame_count:  int
    fps:          int = 8


# ---------------------------------------------------------------------------
# Core generators
# ---------------------------------------------------------------------------

class SpriteGenerator:
    """
    Generate AI sprites and animated spritesheets from text prompts.

    Parameters
    ----------
    openrouter_key : str, optional
        OpenRouter API key.  Falls back to OPENROUTER_API_KEY env var.
    openai_key : str, optional
        OpenAI API key for DALL-E fallback.  Falls back to OPENAI_API_KEY.
    output_dir : str
        Directory where generated images are saved.
    """

    def __init__(
        self,
        openrouter_key: Optional[str] = None,
        openai_key:     Optional[str] = None,
        output_dir:     str = "generated_assets/sprites",
    ):
        self._or_key  = openrouter_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._oai_key = openai_key     or os.environ.get("OPENAI_API_KEY", "")
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt:         str,
        name:           str = "sprite",
        size:           int = 512,
        remove_bg:      bool = True,
        style_hint:     str = "pixel art isometric game sprite",
    ) -> SpriteResult:
        """
        Generate a single sprite from a text prompt.

        Tries OpenRouter image models, falls back to OpenAI DALL-E,
        then falls back to a procedural pixel-art generator.

        Parameters
        ----------
        prompt : str
            Description of the sprite to generate.
        name : str
            Base filename for saving (no extension).
        size : int
            Target output size in pixels (square).
        remove_bg : bool
            Apply chroma-key to remove green screen background.
        style_hint : str
            Prepended style guidance.

        Returns
        -------
        SpriteResult
        """
        full_prompt = f"{style_hint}, {prompt}"

        b64_data, model_used = self._generate_image_b64(full_prompt, size)

        # Save raw image
        raw_path  = os.path.join(self.output_dir, f"{name}_raw.png")
        img_data  = base64.b64decode(b64_data)
        with open(raw_path, "wb") as f:
            f.write(img_data)

        # Optionally remove green screen background
        if remove_bg and _PIL_AVAILABLE:
            img = Image.open(io.BytesIO(img_data)).convert("RGBA")
            img = _chroma_key(img, CHROMA_GREEN_RGB, tolerance=60)
            out_path = os.path.join(self.output_dir, f"{name}.png")
            img.save(out_path, "PNG")
            buf = io.BytesIO()
            img.save(buf, "PNG")
            b64_data = base64.b64encode(buf.getvalue()).decode()
            has_alpha = True
        else:
            out_path  = raw_path
            has_alpha = False

        img_open = Image.open(out_path) if _PIL_AVAILABLE else None
        w = img_open.width  if img_open else size
        h = img_open.height if img_open else size

        return SpriteResult(
            image_path = out_path,
            image_b64  = b64_data,
            prompt     = prompt,
            model_used = model_used,
            width      = w,
            height     = h,
            has_alpha  = has_alpha,
            source     = "ai" if "fallback" not in model_used else "pixel_art",
        )

    # ------------------------------------------------------------------
    def generate_animated(
        self,
        prompt:         str,
        name:           str = "sprite_anim",
        style_hint:     str = "pixel art isometric game sprite",
        frame_count:    int = 8,
        fps:            int = 8,
        video_model:    str = "x-ai/grok-imagine-video",
    ) -> AnimationResult:
        """
        Generate an animated spritesheet: text → reference sprite →
        animated video → extracted frames → spritesheet + GIF.

        Requires OPENROUTER_API_KEY and ffmpeg on PATH.

        Parameters
        ----------
        prompt : str
            Motion/action description (e.g. "warrior idle breathing animation").
        name : str
            Base filename for all outputs.
        frame_count : int
            Target number of frames in the spritesheet.
        fps : int
            Frames per second for the GIF preview.
        video_model : str
            OpenRouter video model ID.

        Returns
        -------
        AnimationResult
        """
        # Step 1: Generate reference sprite
        ref_result = self.generate(
            prompt     = prompt,
            name       = f"{name}_ref",
            style_hint = style_hint,
            remove_bg  = False,  # keep green BG for video reference
        )

        # Step 2: Submit to video model
        frame_paths: List[str] = []
        model_used  = "pixel_art_fallback"

        if self._or_key:
            try:
                frame_paths, model_used = self._generate_video_frames(
                    image_b64   = ref_result.image_b64,
                    motion_prompt = f"{style_hint}, {prompt}",
                    name        = name,
                    video_model = video_model,
                    frame_count = frame_count,
                )
            except Exception as exc:
                print(f"[imagegen] Video generation failed ({exc}), using single-frame fallback")

        # Fallback: use single frame duplicated + slight variations
        if not frame_paths:
            frame_paths = _make_procedural_frames(
                ref_result.image_path, name, self.output_dir, frame_count
            )
            model_used = "procedural_fallback"

        # Step 3: Apply chroma key to all frames
        if _PIL_AVAILABLE:
            clean_frames = []
            for i, fp in enumerate(frame_paths):
                img = Image.open(fp).convert("RGBA")
                img = _chroma_key(img, CHROMA_GREEN_RGB, tolerance=60)
                clean_path = os.path.join(self.output_dir, f"{name}_frame_{i:02d}.png")
                img.save(clean_path, "PNG")
                clean_frames.append(clean_path)
            frame_paths = clean_frames

        # Step 4: Build spritesheet and GIF
        sheet_path = os.path.join(self.output_dir, f"{name}_sheet.png")
        gif_path   = os.path.join(self.output_dir, f"{name}_anim.gif")
        build_spritesheet(frame_paths, sheet_path)
        build_gif(frame_paths, gif_path, fps=fps)

        return AnimationResult(
            frames      = frame_paths,
            spritesheet = sheet_path,
            gif_path    = gif_path,
            prompt      = prompt,
            model_used  = model_used,
            frame_count = len(frame_paths),
            fps         = fps,
        )

    # ------------------------------------------------------------------
    def generate_batch(
        self,
        prompts: List[str],
        names:   Optional[List[str]] = None,
        **kwargs,
    ) -> List[SpriteResult]:
        """Generate multiple sprites in sequence."""
        results = []
        for i, prompt in enumerate(prompts):
            name = (names[i] if names and i < len(names) else f"sprite_{i:02d}")
            results.append(self.generate(prompt, name=name, **kwargs))
        return results

    # ------------------------------------------------------------------
    # Internal image generation
    # ------------------------------------------------------------------

    def _generate_image_b64(self, prompt: str, size: int) -> Tuple[str, str]:
        """
        Try every image source in order and return (base64_png, model_id).
        Always succeeds — falls back to procedural pixel art if all APIs fail.
        """
        # 1. OpenRouter
        if self._or_key:
            for model in IMAGE_MODELS:
                try:
                    b64 = self._openrouter_image(prompt, model, size)
                    return b64, model
                except Exception as exc:
                    print(f"[imagegen] OpenRouter {model} failed: {exc}")

        # 2. OpenAI DALL-E
        if self._oai_key:
            try:
                b64 = self._openai_dalle(prompt, size)
                return b64, "openai/dall-e-3"
            except Exception as exc:
                print(f"[imagegen] DALL-E failed: {exc}")

        # 3. Procedural pixel art fallback (always works)
        b64 = _procedural_pixel_art(prompt, size)
        return b64, "procedural_fallback"

    def _openrouter_image(self, prompt: str, model: str, size: int) -> str:
        """Call OpenRouter chat completions with modalities=['image']."""
        full_prompt = f"{prompt}\n\n{CHROMA_IMAGE_DIRECTIVE}"
        resp = requests.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._or_key}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://voxelforge.ai",
                "X-Title":       "VoxelForge",
            },
            json={
                "model":      model,
                "modalities": ["image"],
                "messages":   [{"role": "user", "content": full_prompt}],
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        url  = (data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("images", [{}])[0]
                    .get("image_url", {})
                    .get("url", ""))
        if not url:
            # Some models return content as base64 directly
            content = (data.get("choices", [{}])[0]
                           .get("message", {})
                           .get("content", ""))
            if content.startswith("data:image"):
                url = content
            else:
                raise ValueError(f"No image in OpenRouter response for {model}")

        return _url_to_b64(url, self._or_key)

    def _openai_dalle(self, prompt: str, size: int) -> str:
        """Call OpenAI DALL-E 3."""
        dall_size = "1024x1024"
        if size <= 512:
            dall_size = "512x512"
        full_prompt = f"{prompt}\n\n{CHROMA_IMAGE_DIRECTIVE}"
        resp = requests.post(
            f"{OPENAI_BASE}/images/generations",
            headers={
                "Authorization": f"Bearer {self._oai_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":           "dall-e-3",
                "prompt":          full_prompt,
                "n":               1,
                "size":            dall_size,
                "response_format": "b64_json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        b64 = resp.json()["data"][0]["b64_json"]
        return b64

    # ------------------------------------------------------------------
    # Video frame extraction
    # ------------------------------------------------------------------

    def _generate_video_frames(
        self,
        image_b64:      str,
        motion_prompt:  str,
        name:           str,
        video_model:    str,
        frame_count:    int,
    ) -> Tuple[List[str], str]:
        """Submit to OpenRouter video endpoint, poll, extract frames via ffmpeg."""
        import subprocess
        import shutil
        import tempfile

        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not on PATH — video frame extraction unavailable")

        full_prompt = f"{motion_prompt}\n\n{CHROMA_VIDEO_DIRECTIVE}"
        image_data_url = f"data:image/png;base64,{image_b64}"

        # Submit
        model_info = next(
            (m for m in VIDEO_MODELS if m["id"] == video_model),
            VIDEO_MODELS[0],
        )
        submit = requests.post(
            f"{OPENROUTER_BASE}/videos",
            headers={
                "Authorization": f"Bearer {self._or_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":    model_info["id"],
                "prompt":   full_prompt,
                "duration": model_info["duration"],
                "input_references": [
                    {"type": "image_url", "image_url": {"url": image_data_url}}
                ],
            },
            timeout=60,
        )
        submit.raise_for_status()
        job = submit.json()
        job_id = job.get("id")
        if not job_id:
            raise ValueError("OpenRouter video submit returned no job id")

        # Poll
        for _ in range(POLL_MAX_TRIES):
            status = job.get("status", "")
            if status == "completed":
                break
            if status in ("failed", "cancelled", "expired"):
                raise RuntimeError(f"OpenRouter video job {status}")
            time.sleep(POLL_INTERVAL)
            poll_url = job.get("polling_url") or f"{OPENROUTER_BASE}/videos/{job_id}"
            job = requests.get(
                poll_url,
                headers={"Authorization": f"Bearer {self._or_key}"},
                timeout=30,
            ).json()

        if job.get("status") != "completed":
            raise RuntimeError("Video job timed out")

        # Download video
        video_url = (job.get("unsigned_urls") or [None])[0]
        auth_headers: dict = {}
        if not video_url:
            video_url = f"{OPENROUTER_BASE}/videos/{job_id}/content?index=0"
            auth_headers = {"Authorization": f"Bearer {self._or_key}"}

        video_resp = requests.get(video_url, headers=auth_headers, timeout=120)
        video_resp.raise_for_status()

        tmpdir   = tempfile.mkdtemp()
        vid_path = os.path.join(tmpdir, "video.mp4")
        with open(vid_path, "wb") as f:
            f.write(video_resp.content)

        # Extract frames with ffmpeg
        frames_pattern = os.path.join(self.output_dir, f"{name}_raw_frame_%02d.png")
        fps_extract     = max(1, frame_count // model_info["duration"])
        subprocess.run(
            ["ffmpeg", "-y", "-i", vid_path, "-vf", f"fps={fps_extract}",
             "-frames:v", str(frame_count), frames_pattern],
            capture_output=True, check=True,
        )

        frames = sorted([
            os.path.join(self.output_dir, f)
            for f in os.listdir(self.output_dir)
            if f.startswith(f"{name}_raw_frame_") and f.endswith(".png")
        ])[:frame_count]

        return frames, model_info["id"]


# ---------------------------------------------------------------------------
# Spritesheet + GIF builders
# ---------------------------------------------------------------------------

def build_spritesheet(frame_paths: List[str], output_path: str) -> str:
    """
    Assemble a list of frames into a horizontal 1×N PNG spritesheet.

    Parameters
    ----------
    frame_paths : list[str]
        Ordered list of PNG file paths.
    output_path : str
        Where to save the spritesheet.

    Returns
    -------
    str
        Absolute path to the saved spritesheet.
    """
    if not frame_paths:
        raise ValueError("frame_paths is empty")
    if not _PIL_AVAILABLE:
        raise RuntimeError("Pillow required: pip install Pillow")

    images = [Image.open(p).convert("RGBA") for p in frame_paths]
    w = max(img.width  for img in images)
    h = max(img.height for img in images)

    sheet = Image.new("RGBA", (w * len(images), h), (0, 0, 0, 0))
    for i, img in enumerate(images):
        # Resize to max dims if needed
        if img.width != w or img.height != h:
            img = img.resize((w, h), Image.NEAREST)
        sheet.paste(img, (i * w, 0), img)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    sheet.save(output_path, "PNG")
    return os.path.abspath(output_path)


def build_gif(
    frame_paths: List[str],
    output_path: str,
    fps:         int = 8,
    loop:        int = 0,
) -> str:
    """
    Build a looping animated GIF from a list of PNG frames.

    Parameters
    ----------
    frame_paths : list[str]
        Ordered list of PNG file paths.
    output_path : str
        Where to save the GIF.
    fps : int
        Frames per second.
    loop : int
        0 = loop forever.

    Returns
    -------
    str
        Absolute path to the saved GIF.
    """
    if not frame_paths:
        raise ValueError("frame_paths is empty")
    if not _PIL_AVAILABLE:
        raise RuntimeError("Pillow required: pip install Pillow")

    images = [Image.open(p).convert("RGBA") for p in frame_paths]
    duration_ms = max(20, 1000 // fps)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    images[0].save(
        output_path,
        format   = "GIF",
        save_all = True,
        append_images = images[1:],
        loop     = loop,
        duration = duration_ms,
        optimize = False,
        disposal = 2,
    )
    return os.path.abspath(output_path)


# ---------------------------------------------------------------------------
# Chroma-key background removal
# ---------------------------------------------------------------------------

def _chroma_key(
    img:        "Image.Image",
    key_color:  Tuple[int, int, int] = CHROMA_GREEN_RGB,
    tolerance:  int = 60,
) -> "Image.Image":
    """
    Remove a chroma-key (green screen) background from an RGBA PIL Image.

    Pixels whose color is within ``tolerance`` (Euclidean distance in RGB
    space) of ``key_color`` are made fully transparent.  Edge pixels are
    feathered for a softer cut.

    Parameters
    ----------
    img : PIL.Image.Image
        Input image in RGBA mode.
    key_color : tuple[int, int, int]
        The key color to remove (default: #00b140 chroma green).
    tolerance : int
        Maximum distance from key_color to consider a pixel "green screen".

    Returns
    -------
    PIL.Image.Image
        Image with removed background (RGBA).
    """
    import numpy as np

    data = np.array(img, dtype=np.float32)  # H×W×4
    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    kr, kg, kb = float(key_color[0]), float(key_color[1]), float(key_color[2])

    dist = np.sqrt((r - kr)**2 + (g - kg)**2 + (b - kb)**2)

    # Hard mask
    mask_hard = dist < tolerance
    # Soft feather zone
    mask_soft = (dist >= tolerance) & (dist < tolerance * 1.5)

    # Alpha channel adjustments
    alpha = data[:, :, 3].copy()
    alpha[mask_hard] = 0
    alpha[mask_soft] = alpha[mask_soft] * ((dist[mask_soft] - tolerance) / (tolerance * 0.5))

    data[:, :, 3] = alpha
    return Image.fromarray(np.clip(data, 0, 255).astype(np.uint8), "RGBA")


def remove_background(image_path: str, output_path: Optional[str] = None,
                       key_color: Tuple[int, int, int] = CHROMA_GREEN_RGB,
                       tolerance: int = 60) -> str:
    """
    Apply chroma-key background removal to an image file.

    Parameters
    ----------
    image_path : str
        Path to the source image.
    output_path : str, optional
        Save path.  Defaults to overwriting input.
    key_color : tuple[int, int, int]
        Background color to remove.
    tolerance : int
        Distance threshold.

    Returns
    -------
    str
        Path to the output image.
    """
    if not _PIL_AVAILABLE:
        raise RuntimeError("Pillow required: pip install Pillow")
    img  = Image.open(image_path).convert("RGBA")
    img  = _chroma_key(img, key_color, tolerance)
    out  = output_path or image_path
    img.save(out, "PNG")
    return out


# ---------------------------------------------------------------------------
# Procedural pixel art fallback (no API key needed)
# ---------------------------------------------------------------------------

def _procedural_pixel_art(prompt: str, size: int = 64) -> str:
    """
    Generate a simple procedural pixel-art sprite when no API key is available.

    Uses the prompt to seed a deterministic color palette and pixel pattern.
    Returns base64-encoded PNG bytes.
    """
    if not _PIL_AVAILABLE:
        return _minimal_png_b64(size)

    import random
    rng    = random.Random(hash(prompt) & 0xFFFFFF)
    canvas = size if size <= 128 else 64

    img    = Image.new("RGBA", (canvas, canvas), (0, 177, 64, 255))  # green BG
    draw   = ImageDraw.Draw(img)

    # Body
    r = rng.randint(50, 200)
    g = rng.randint(50, 200)
    b = rng.randint(50, 200)
    bx = canvas // 4
    body_rect = [bx, canvas // 3, canvas - bx, canvas - canvas // 6]
    draw.rectangle(body_rect, fill=(r, g, b, 255))

    # Head
    hx = canvas // 3
    head_rect = [hx, canvas // 8, canvas - hx, canvas // 3 + 2]
    draw.ellipse(head_rect, fill=(r + 30, g + 10, b, 255))

    # Eyes
    ex = canvas // 3 + canvas // 8
    draw.ellipse([ex, canvas // 5, ex + 4, canvas // 5 + 4], fill=(20, 20, 20, 255))
    draw.ellipse([canvas - ex - 4, canvas // 5, canvas - ex, canvas // 5 + 4], fill=(20, 20, 20, 255))

    # Pixelate
    small = img.resize((canvas // 4, canvas // 4), Image.NEAREST)
    img   = small.resize((canvas, canvas), Image.NEAREST)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _make_procedural_frames(
    ref_path:   str,
    name:       str,
    output_dir: str,
    n:          int,
) -> List[str]:
    """
    Create ``n`` animation frames by applying small offset/color variations
    to the reference image.  Used as fallback when video generation fails.
    """
    if not _PIL_AVAILABLE or not os.path.isfile(ref_path):
        return [ref_path] * n

    import numpy as np

    ref   = Image.open(ref_path).convert("RGBA")
    arr   = np.array(ref, dtype=np.float32)
    paths: List[str] = []

    for i in range(n):
        # Subtle bounce: shift Y by ±2 pixels for an idle animation feel
        offset_y = int(2 * (i % 4 < 2 and 1 or -1))
        shifted  = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        # Small vertical nudge
        if abs(offset_y) > 0:
            shifted = Image.fromarray(
                np.roll(np.array(shifted), offset_y, axis=0), "RGBA"
            )
        frame_path = os.path.join(output_dir, f"{name}_raw_frame_{i:02d}.png")
        shifted.save(frame_path, "PNG")
        paths.append(frame_path)

    return paths


def _url_to_b64(url: str, api_key: str = "") -> str:
    """
    Convert an image URL (data: or https:) to base64-encoded PNG bytes.
    """
    if url.startswith("data:"):
        m = url.find(",")
        if m == -1:
            raise ValueError("malformed data URL")
        return url[m + 1:]
    if url.startswith("http"):
        headers = {}
        if "openrouter.ai" in url and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode()
    raise ValueError(f"unsupported URL: {url[:60]}")


def _minimal_png_b64(size: int = 64) -> str:
    """Return a minimal valid PNG (solid green) when Pillow is not available."""
    # 1×1 green pixel PNG, base64 encoded
    return (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def generate_sprite(
    prompt:        str,
    name:          str = "sprite",
    output_dir:    str = "generated_assets/sprites",
    remove_bg:     bool = True,
    openrouter_key: Optional[str] = None,
    openai_key:    Optional[str] = None,
) -> SpriteResult:
    """
    Top-level convenience function — generates one sprite.

    Works with no API keys (procedural fallback) or with
    OPENROUTER_API_KEY / OPENAI_API_KEY set.
    """
    gen = SpriteGenerator(
        openrouter_key = openrouter_key,
        openai_key     = openai_key,
        output_dir     = output_dir,
    )
    return gen.generate(prompt, name=name, remove_bg=remove_bg)


def generate_character_sprites(
    name:          str,
    class_type:    str = "warrior",
    output_dir:    str = "generated_assets/sprites",
    animated:      bool = False,
    **gen_kwargs,
) -> dict:
    """
    Generate a full character sprite set (idle, walk, attack).

    Returns dict mapping action → SpriteResult.
    """
    gen     = SpriteGenerator(output_dir=output_dir, **gen_kwargs)
    actions = ["idle", "walk", "attack"] if animated else ["idle"]
    results = {}

    for action in actions:
        prompt = (
            f"pixel art isometric game character, {class_type}, "
            f"{action} animation, fantasy RPG style, single character, "
            f"clean design, game sprite"
        )
        results[action] = gen.generate(
            prompt, name=f"{name}_{action}", remove_bg=True
        )

    return results
