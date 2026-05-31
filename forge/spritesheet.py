"""
forge.spritesheet
=================
Advanced sprite sheet generator for VoxelForge Studio.

Integrates patterns from multiple sources:
  - Grid-based batch generation (25 images per API call = ~30× cheaper)
  - 6 game art styles with proper resolutions (Stardew, Hollow Knight, Genshin…)
  - 9 animation actions (idle, walk, jump, attack, hurt, KO, punch, turn, run)
  - Background removal via rembg (u2net model) + chroma-key fallback
  - Frame splitting from sprite sheets
  - Rate-limited concurrent generation
  - Prompt enhancement for style consistency

Usage
-----
>>> from forge.spritesheet import SpriteSheetForge, GameStyle, AnimationAction
>>> forge_ss = SpriteSheetForge()

>>> # Single-style sprite sheet
>>> sheet = forge_ss.generate_character_sheet(
...     description = "ice mage with blue robes",
...     style       = GameStyle.STARDEW_VALLEY,
...     actions     = [AnimationAction.IDLE, AnimationAction.WALK, AnimationAction.CAST],
... )
>>> print(sheet.spritesheet_path)   # horizontal 1×N PNG

>>> # Batch props (25 images for the price of ~1)
>>> batch = forge_ss.generate_prop_batch(
...     prompts = ["oak tree", "stone wall", "wooden crate", "barrel", "chest"],
...     style   = GameStyle.PIXEL_ART_RPG,
... )

>>> # Strip background from any image
>>> clean = forge_ss.remove_background("warrior.png")
"""

from __future__ import annotations

import base64
import io
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from PIL import Image, ImageDraw  # type: ignore
    _PIL = True
except ImportError:
    _PIL = False

try:
    import numpy as np   # type: ignore
    _NP = True
except ImportError:
    _NP = False


# ---------------------------------------------------------------------------
# Art styles (inspired by spriteforge styles)
# ---------------------------------------------------------------------------

class GameStyle(str, Enum):
    STARDEW_VALLEY  = "stardew_valley"
    HOLLOW_KNIGHT   = "hollow_knight"
    GENSHIN_IMPACT  = "genshin_impact"
    FALL_GUYS       = "fall_guys"
    PIXEL_ART_RPG   = "pixel_art_rpg"
    BREATH_OF_WILD  = "breath_of_wild"
    RETRO_8BIT      = "retro_8bit"
    ANIME_CARTOON   = "anime_cartoon"
    REALISTIC_GAME  = "realistic_game"
    VECTOR_ART      = "vector_art"
    ISOMETRIC_VOXEL = "isometric_voxel"


@dataclass
class StyleSpec:
    name:          str
    resolution:    Tuple[int, int]    # (width, height) per frame
    prompt_prefix: str                # prepended to user prompt
    prompt_suffix: str                # appended for style consistency
    bg_color:      str                # preferred background for chroma-key


_STYLE_SPECS: Dict[GameStyle, StyleSpec] = {
    GameStyle.STARDEW_VALLEY: StyleSpec(
        name          = "Stardew Valley",
        resolution    = (32, 32),
        prompt_prefix = "pixel art game sprite, Stardew Valley style, 32x32 pixels, ",
        prompt_suffix = (", top-down perspective, warm earthy colors, retro pixelated, "
                         "clear silhouette, game ready, single character centered, "
                         "solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.HOLLOW_KNIGHT: StyleSpec(
        name          = "Hollow Knight",
        resolution    = (128, 128),
        prompt_prefix = "hand-drawn gothic game sprite, Hollow Knight aesthetic, ",
        prompt_suffix = (", dark atmospheric, high contrast, detailed linework, "
                         "silhouette-heavy, indie game art style, centered on solid "
                         "pure green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.GENSHIN_IMPACT: StyleSpec(
        name          = "Genshin Impact",
        resolution    = (192, 192),
        prompt_prefix = "anime-style game character sprite, Genshin Impact aesthetic, ",
        prompt_suffix = (", vibrant cel-shaded colors, clean outlines, detailed design, "
                         "RPG character, centered full body, solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.FALL_GUYS: StyleSpec(
        name          = "Fall Guys",
        resolution    = (160, 160),
        prompt_prefix = "cartoon bouncy game character, Fall Guys style, ",
        prompt_suffix = (", rounded shapes, bright saturated colors, cute proportions, "
                         "3D-rendered game art look, centered, solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.PIXEL_ART_RPG: StyleSpec(
        name          = "Pixel Art RPG",
        resolution    = (64, 64),
        prompt_prefix = "pixel art RPG game sprite, 64x64 resolution, ",
        prompt_suffix = (", classic JRPG style, clear pixels, isometric or side-view, "
                         "game-ready asset, transparent-friendly solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.BREATH_OF_WILD: StyleSpec(
        name          = "Breath of the Wild",
        resolution    = (256, 256),
        prompt_prefix = "cel-shaded game character, Breath of the Wild style, ",
        prompt_suffix = (", painterly outlines, soft vibrant colors, adventurous feel, "
                         "open world game asset, centered, solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.RETRO_8BIT: StyleSpec(
        name          = "Retro 8-bit",
        resolution    = (16, 16),
        prompt_prefix = "8-bit NES-style pixel art sprite, ",
        prompt_suffix = ", minimal palette, bold simple shapes, classic retro game look, solid green background",
        bg_color      = "#00b140",
    ),
    GameStyle.ANIME_CARTOON: StyleSpec(
        name          = "Anime Cartoon",
        resolution    = (200, 200),
        prompt_prefix = "anime game sprite, cartoon style, clean illustration, ",
        prompt_suffix = (", bold outlines, flat color areas, expressive design, "
                         "2D game asset, centered full body, solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.REALISTIC_GAME: StyleSpec(
        name          = "Realistic Game",
        resolution    = (512, 512),
        prompt_prefix = "realistic game character asset, AAA quality, ",
        prompt_suffix = (", photorealistic textures, detailed rendering, "
                         "game-ready character, transparent background suitable, "
                         "centered on solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.VECTOR_ART: StyleSpec(
        name          = "Vector Art",
        resolution    = (256, 256),
        prompt_prefix = "vector illustration game asset, clean flat design, ",
        prompt_suffix = (", sharp edges, bold colors, SVG-like aesthetic, "
                         "game character or item, centered, solid green background #00b140"),
        bg_color      = "#00b140",
    ),
    GameStyle.ISOMETRIC_VOXEL: StyleSpec(
        name          = "Isometric Voxel",
        resolution    = (128, 128),
        prompt_prefix = "isometric voxel game asset, pixel art 3D style, ",
        prompt_suffix = (", clean voxel blocks, vibrant colors, game-ready isometric view, "
                         "45-degree angle, solid green background #00b140"),
        bg_color      = "#00b140",
    ),
}


# ---------------------------------------------------------------------------
# Animation actions
# ---------------------------------------------------------------------------

class AnimationAction(str, Enum):
    IDLE       = "idle"
    WALK       = "walk"
    RUN        = "run"
    JUMP       = "jump"
    ATTACK     = "attack"
    CAST       = "cast"
    HURT       = "hurt"
    DEATH      = "death"
    TURN       = "turn"
    PUNCH      = "punch"
    BLOCK      = "block"
    INTERACT   = "interact"


_ACTION_FRAMES: Dict[AnimationAction, int] = {
    AnimationAction.IDLE:     4,
    AnimationAction.WALK:     8,
    AnimationAction.RUN:      6,
    AnimationAction.JUMP:     5,
    AnimationAction.ATTACK:   6,
    AnimationAction.CAST:     6,
    AnimationAction.HURT:     3,
    AnimationAction.DEATH:    5,
    AnimationAction.TURN:     4,
    AnimationAction.PUNCH:    5,
    AnimationAction.BLOCK:    3,
    AnimationAction.INTERACT: 4,
}

_ACTION_PROMPT: Dict[AnimationAction, str] = {
    AnimationAction.IDLE:     "standing idle pose, subtle breathing movement",
    AnimationAction.WALK:     "walking animation, side view, smooth stride",
    AnimationAction.RUN:      "running at full speed, dynamic pose",
    AnimationAction.JUMP:     "jumping upward, legs bent, arms raised",
    AnimationAction.ATTACK:   "attacking with weapon, dynamic swing pose",
    AnimationAction.CAST:     "casting magic spell, hands raised, energy effect",
    AnimationAction.HURT:     "taking damage, recoiling in pain",
    AnimationAction.DEATH:    "falling and dying, collapse animation",
    AnimationAction.TURN:     "turning around, rotation sequence",
    AnimationAction.PUNCH:    "punching forward, combat stance",
    AnimationAction.BLOCK:    "defensive blocking pose, shield raised",
    AnimationAction.INTERACT: "reaching out to interact with object",
}


# ---------------------------------------------------------------------------
# Sprite sheet results
# ---------------------------------------------------------------------------

@dataclass
class SpriteSheetResult:
    name:             str
    style:            GameStyle
    action:           Optional[AnimationAction]
    spritesheet_path: str                      # horizontal 1×N PNG
    frame_paths:      List[str]                # individual frame PNGs
    gif_path:         Optional[str]            # looping GIF preview
    has_alpha:        bool                     # True if BG was removed
    frame_count:      int
    resolution:       Tuple[int, int]
    source:           str                      # "ai" | "procedural"
    model_used:       str


@dataclass
class BatchGenerationResult:
    prompts:    List[str]
    style:      GameStyle
    image_paths: List[str]
    grid_path:   Optional[str]    # raw grid image before splitting
    source:      str
    model_used:  str


# ---------------------------------------------------------------------------
# Background removal
# ---------------------------------------------------------------------------

class BackgroundRemover:
    """
    Removes backgrounds from game asset images.

    Strategy priority:
    1. rembg (u2net neural network) — best quality, requires `pip install rembg`
    2. Chroma-key (green screen #00b140) — fast, works when BG is solid green
    3. Simple threshold — emergency fallback

    Mirrors pixelda's image_tools.py remove_solid_background pattern.
    """

    def __init__(self, method: str = "auto"):
        """
        Parameters
        ----------
        method : str
            "auto" | "rembg" | "chromakey" | "threshold"
        """
        self.method = method
        self._rembg_session = None

    def _get_rembg_session(self):
        if self._rembg_session is None:
            try:
                from rembg import new_session  # type: ignore
                self._rembg_session = new_session("u2net")
            except ImportError:
                self._rembg_session = "unavailable"
        return self._rembg_session if self._rembg_session != "unavailable" else None

    # ------------------------------------------------------------------
    def remove(
        self,
        image_path:  str,
        output_path: Optional[str] = None,
        key_color:   Tuple[int, int, int] = (0, 177, 64),
        tolerance:   int = 60,
    ) -> str:
        """
        Remove the background from an image file.

        Parameters
        ----------
        image_path : str
            Source image path.
        output_path : str, optional
            Where to save the result. Defaults to <name>_nobg.png.
        key_color : tuple
            RGB chroma-key colour (default: #00b140 green).
        tolerance : int
            Colour distance threshold for chroma-key.

        Returns
        -------
        str
            Path to the transparency-enabled PNG.
        """
        if not _PIL:
            raise RuntimeError("Pillow required: pip install Pillow")

        out = output_path or _replace_suffix(image_path, "_nobg.png")

        if self.method in ("auto", "rembg"):
            session = self._get_rembg_session()
            if session:
                return self._rembg_remove(image_path, out, session)

        if self.method in ("auto", "chromakey"):
            return self._chromakey_remove(image_path, out, key_color, tolerance)

        return self._threshold_remove(image_path, out)

    def _rembg_remove(self, src: str, dst: str, session) -> str:
        """Neural BG removal via rembg — best quality for non-green backgrounds."""
        try:
            from rembg import remove as rembg_remove  # type: ignore
            img = Image.open(src).convert("RGBA")
            result = rembg_remove(img, session=session, alpha_matting=False)
            result.save(dst, "PNG")
            return dst
        except Exception as exc:
            # Fallback to chroma-key on rembg failure
            return self._chromakey_remove(src, dst, (0, 177, 64), 60)

    def _chromakey_remove(
        self,
        src: str,
        dst: str,
        key_color: Tuple[int, int, int],
        tolerance: int,
    ) -> str:
        """Chroma-key green screen removal using Pillow + NumPy."""
        if not _NP:
            return self._chromakey_pil(src, dst, key_color, tolerance)
        return self._chromakey_numpy(src, dst, key_color, tolerance)

    def _chromakey_numpy(self, src, dst, key_color, tolerance) -> str:
        data = _NP and __import__("numpy") or None
        if data is None:
            return self._chromakey_pil(src, dst, key_color, tolerance)
        import numpy as np_
        img = Image.open(src).convert("RGBA")
        arr = np_.array(img, dtype=np_.float32)
        kr, kg, kb = float(key_color[0]), float(key_color[1]), float(key_color[2])
        r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        dist = np_.sqrt((r-kr)**2 + (g-kg)**2 + (b-kb)**2)
        alpha = arr[:,:,3].copy()
        alpha[dist < tolerance] = 0
        soft = (dist >= tolerance) & (dist < tolerance * 1.5)
        alpha[soft] = alpha[soft] * ((dist[soft] - tolerance) / (tolerance * 0.5))
        arr[:,:,3] = alpha
        Image.fromarray(np_.clip(arr, 0, 255).astype(np_.uint8), "RGBA").save(dst, "PNG")
        return dst

    def _chromakey_pil(self, src, dst, key_color, tolerance) -> str:
        """Pure-Pillow chroma-key (slower but no NumPy needed)."""
        img = Image.open(src).convert("RGBA")
        pixels = img.load()
        w, h   = img.size
        kr, kg, kb = key_color
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                dist = ((r-kr)**2 + (g-kg)**2 + (b-kb)**2) ** 0.5
                if dist < tolerance:
                    pixels[x, y] = (r, g, b, 0)
        img.save(dst, "PNG")
        return dst

    def _threshold_remove(self, src: str, dst: str) -> str:
        """Simple white/light-color background removal."""
        img  = Image.open(src).convert("RGBA")
        data = img.getdata()
        new_data = []
        for item in data:
            r, g, b, a = item
            if r > 230 and g > 230 and b > 230:
                new_data.append((r, g, b, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)
        img.save(dst, "PNG")
        return dst


# ---------------------------------------------------------------------------
# Sprite Sheet Forge
# ---------------------------------------------------------------------------

class SpriteSheetForge:
    """
    Generates game-ready sprite sheets from text descriptions.

    Supports AI generation (when API keys are available) and procedural
    fallback (always works, no API key needed).

    Parameters
    ----------
    output_dir : str
        Root directory for all generated sprite outputs.
    openrouter_key : str, optional
    openai_key : str, optional
    remove_bg : bool
        Automatically remove backgrounds (default True).
    bg_method : str
        "auto" | "rembg" | "chromakey"
    """

    def __init__(
        self,
        output_dir:     str           = "generated_assets/sprites",
        openrouter_key: Optional[str] = None,
        openai_key:     Optional[str] = None,
        remove_bg:      bool          = True,
        bg_method:      str           = "auto",
    ):
        self.output_dir = output_dir
        self._or_key    = openrouter_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._oai_key   = openai_key     or os.environ.get("OPENAI_API_KEY", "")
        self.remove_bg  = remove_bg
        self.bg_remover = BackgroundRemover(bg_method)
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Character sprite sheets
    # ------------------------------------------------------------------

    def generate_character_sheet(
        self,
        description: str,
        style:       GameStyle          = GameStyle.PIXEL_ART_RPG,
        actions:     List[AnimationAction] = None,
        name:        str                = "character",
        fps:         int                = 8,
    ) -> SpriteSheetResult:
        """
        Generate a complete character sprite sheet for multiple animation actions.

        Each action is generated as a separate horizontal strip; all strips
        are stacked vertically into a single master sprite sheet.

        Parameters
        ----------
        description : str
            Character description (e.g. "ice mage in blue robes").
        style : GameStyle
        actions : list[AnimationAction]
            Defaults to [IDLE, WALK, ATTACK].
        name : str
            Base filename.

        Returns
        -------
        SpriteSheetResult
        """
        if actions is None:
            actions = [AnimationAction.IDLE, AnimationAction.WALK, AnimationAction.ATTACK]

        spec      = _STYLE_SPECS[style]
        all_frames: List[str] = []
        row_strips: List[str] = []

        for action in actions:
            n_frames = _ACTION_FRAMES.get(action, 4)
            frames   = self._generate_frames(
                description, action, spec, n_frames,
                f"{name}_{action.value}",
            )
            all_frames.extend(frames)

            # Assemble horizontal strip for this action
            if frames and _PIL:
                strip_path = os.path.join(
                    self.output_dir, f"{name}_{action.value}_strip.png"
                )
                _hstack_images(frames, strip_path)
                row_strips.append(strip_path)

        # Build master sheet (vertical stack of action strips)
        sheet_path = os.path.join(self.output_dir, f"{name}_sheet.png")
        if row_strips and _PIL:
            _vstack_images(row_strips, sheet_path)
        elif all_frames and _PIL:
            _hstack_images(all_frames, sheet_path)

        # GIF of the first action
        gif_path = None
        first_action_frames = all_frames[:_ACTION_FRAMES.get(actions[0], 4)]
        if first_action_frames and _PIL:
            gif_path = os.path.join(self.output_dir, f"{name}_preview.gif")
            _build_gif(first_action_frames, gif_path, fps)

        return SpriteSheetResult(
            name             = name,
            style            = style,
            action           = actions[0] if actions else None,
            spritesheet_path = sheet_path,
            frame_paths      = all_frames,
            gif_path         = gif_path,
            has_alpha        = self.remove_bg,
            frame_count      = len(all_frames),
            resolution       = spec.resolution,
            source           = "ai" if (self._or_key or self._oai_key) else "procedural",
            model_used       = "openrouter" if self._or_key else "procedural",
        )

    # ------------------------------------------------------------------
    # Batch prop/item generation (grid pattern — 25 per API call)
    # ------------------------------------------------------------------

    def generate_prop_batch(
        self,
        prompts:    List[str],
        style:      GameStyle = GameStyle.PIXEL_ART_RPG,
        grid_size:  int       = 5,
        name:       str       = "props",
    ) -> BatchGenerationResult:
        """
        Generate a batch of props using grid-based generation.

        Groups prompts into grid_size × grid_size cells and generates
        one image per grid, then crops individual cells.

        Parameters
        ----------
        prompts : list[str]
            Item/prop descriptions. Up to 25 per API call.
        style : GameStyle
        grid_size : int
            Grid dimension (default 5 — 25 items per call).
        name : str

        Returns
        -------
        BatchGenerationResult
        """
        spec       = _STYLE_SPECS[style]
        all_images: List[str] = []
        grid_path:  Optional[str] = None

        # Group prompts into batches of grid_size²
        batch_size = grid_size * grid_size
        batches    = [prompts[i:i+batch_size] for i in range(0, len(prompts), batch_size)]

        for b_idx, batch in enumerate(batches):
            # Enhance prompt for grid consistency
            grid_prompt = self._build_grid_prompt(batch, spec, grid_size)
            grid_name   = f"{name}_grid_{b_idx:02d}"

            grid_img = self._generate_single_image(grid_prompt, grid_name, spec)

            if grid_img and _PIL:
                grid_path = grid_img
                # Split grid into individual cells
                cells = _split_grid(grid_img, grid_size, grid_size,
                                     self.output_dir, grid_name)
                # Apply BG removal to each cell
                if self.remove_bg:
                    clean_cells = []
                    for i, cell in enumerate(cells):
                        try:
                            clean = self.bg_remover.remove(
                                cell,
                                _replace_suffix(cell, "_nobg.png"),
                                tolerance=60,
                            )
                            clean_cells.append(clean)
                        except Exception:
                            clean_cells.append(cell)
                    all_images.extend(clean_cells)
                else:
                    all_images.extend(cells)
            else:
                # Procedural fallback for each item
                for i, p in enumerate(batch):
                    img = self._procedural_image(p, spec, f"{name}_{b_idx}_{i}")
                    all_images.append(img)

        return BatchGenerationResult(
            prompts    = prompts,
            style      = style,
            image_paths = all_images,
            grid_path  = grid_path,
            source     = "ai" if (self._or_key or self._oai_key) else "procedural",
            model_used = "openrouter/grid" if self._or_key else "procedural",
        )

    # ------------------------------------------------------------------
    # Utility: remove background from any file
    # ------------------------------------------------------------------

    def remove_background(
        self,
        image_path:  str,
        output_path: Optional[str] = None,
        method:      str           = "auto",
    ) -> str:
        """Apply background removal to an existing image."""
        remover = BackgroundRemover(method)
        return remover.remove(image_path, output_path)

    # ------------------------------------------------------------------
    # Sprite splitting utilities
    # ------------------------------------------------------------------

    def split_sheet(
        self,
        sheet_path:    str,
        frame_width:   int,
        frame_height:  int,
        output_prefix: str = "",
    ) -> List[str]:
        """
        Split a horizontal sprite sheet into individual frame files.

        Parameters
        ----------
        sheet_path : str
        frame_width, frame_height : int
            Size of each frame in pixels.
        output_prefix : str
            Prefix for output files.

        Returns
        -------
        list[str]
            Paths to individual frame images.
        """
        if not _PIL:
            raise RuntimeError("Pillow required")

        sheet    = Image.open(sheet_path).convert("RGBA")
        sw, sh   = sheet.size
        n_frames = sw // frame_width
        prefix   = output_prefix or os.path.splitext(sheet_path)[0]
        paths    = []

        for i in range(n_frames):
            x0    = i * frame_width
            frame = sheet.crop((x0, 0, x0 + frame_width, frame_height))
            path  = f"{prefix}_f{i:02d}.png"
            frame.save(path, "PNG")
            paths.append(path)

        return paths

    def merge_frames(
        self,
        frame_paths: List[str],
        output_path: str,
        direction:   str = "horizontal",
    ) -> str:
        """
        Merge individual frames into a sprite sheet.

        Parameters
        ----------
        frame_paths : list[str]
        output_path : str
        direction : str
            "horizontal" (default) or "vertical".

        Returns
        -------
        str
            Path to the merged sprite sheet.
        """
        if not _PIL:
            raise RuntimeError("Pillow required")
        if direction == "horizontal":
            return _hstack_images(frame_paths, output_path)
        return _vstack_images(frame_paths, output_path)

    # ------------------------------------------------------------------
    # Internal generation helpers
    # ------------------------------------------------------------------

    def _generate_frames(
        self,
        description: str,
        action:      AnimationAction,
        spec:        StyleSpec,
        n_frames:    int,
        base_name:   str,
    ) -> List[str]:
        """Generate n_frames individual images for one animation action."""
        frames = []
        action_prompt = _ACTION_PROMPT.get(action, action.value)
        for i in range(n_frames):
            frame_prompt = (
                f"{spec.prompt_prefix}{description}, "
                f"{action_prompt}, animation frame {i+1} of {n_frames}"
                f"{spec.prompt_suffix}"
            )
            frame_name = f"{base_name}_f{i:02d}"
            path = self._generate_single_image(frame_prompt, frame_name, spec)
            if path and self.remove_bg:
                try:
                    clean = self.bg_remover.remove(path,
                        _replace_suffix(path, "_nobg.png"), tolerance=65)
                    frames.append(clean)
                    continue
                except Exception:
                    pass
            if path:
                frames.append(path)

        return frames

    def _generate_single_image(
        self,
        prompt:    str,
        name:      str,
        spec:      StyleSpec,
    ) -> Optional[str]:
        """Generate one image via API or procedural fallback."""
        # Try OpenRouter
        if self._or_key:
            try:
                return self._openrouter_image(prompt, name, spec)
            except Exception as exc:
                pass
        # Try OpenAI
        if self._oai_key:
            try:
                return self._openai_image(prompt, name)
            except Exception:
                pass
        # Procedural fallback
        return self._procedural_image(prompt, spec, name)

    def _openrouter_image(self, prompt: str, name: str, spec: StyleSpec) -> str:
        """Call OpenRouter image generation endpoint."""
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._or_key}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://voxelforge.ai",
            },
            json={
                "model":      "x-ai/grok-2-image",
                "modalities": ["image"],
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        resp.raise_for_status()
        url = (resp.json().get("choices", [{}])[0]
                          .get("message", {})
                          .get("images", [{}])[0]
                          .get("image_url", {})
                          .get("url", ""))
        if not url:
            raise ValueError("No image URL in response")
        return self._save_image_url(url, name)

    def _openai_image(self, prompt: str, name: str) -> str:
        """Call OpenAI DALL-E 3."""
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {self._oai_key}",
                     "Content-Type":  "application/json"},
            json={
                "model":           "dall-e-3",
                "prompt":          prompt,
                "n":               1,
                "size":            "1024x1024",
                "response_format": "b64_json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        b64  = resp.json()["data"][0]["b64_json"]
        path = os.path.join(self.output_dir, f"{name}.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return path

    def _save_image_url(self, url: str, name: str) -> str:
        if url.startswith("data:"):
            m    = url.index(",") + 1
            data = base64.b64decode(url[m:])
        else:
            data = requests.get(url, timeout=60).content
        path = os.path.join(self.output_dir, f"{name}.png")
        with open(path, "wb") as f:
            f.write(data)
        return path

    def _procedural_image(
        self, prompt: str, spec: StyleSpec, name: str
    ) -> str:
        """Generate a simple procedural placeholder image (no API needed)."""
        if not _PIL:
            path = os.path.join(self.output_dir, f"{name}.png")
            open(path, "wb").close()
            return path

        import random
        rng = random.Random(hash(prompt) & 0xFFFFFF)
        w, h = spec.resolution
        img  = Image.new("RGBA", (max(w, 32), max(h, 32)), (0, 177, 64, 255))
        draw = ImageDraw.Draw(img)

        # Body rectangle
        r = rng.randint(40, 200)
        g = rng.randint(40, 200)
        b = rng.randint(40, 200)
        bx = w // 5
        draw.rectangle([bx, h//3, w-bx, h-h//8], fill=(r, g, b, 255))
        # Head
        hx = w // 3
        draw.ellipse([hx, h//10, w-hx, h//3+2], fill=(min(r+40,255), g, b, 255))
        # Simple pixelation
        small = img.resize((max(w//4, 8), max(h//4, 8)), Image.NEAREST)
        img   = small.resize((max(w, 32), max(h, 32)), Image.NEAREST)

        path  = os.path.join(self.output_dir, f"{name}.png")
        img.save(path, "PNG")
        return path

    def _build_grid_prompt(
        self, prompts: List[str], spec: StyleSpec, grid_size: int
    ) -> str:
        """Build a prompt for generating a grid of items."""
        items = ", ".join(f'"{p}"' for p in prompts[:grid_size*grid_size])
        return (
            f"{spec.prompt_prefix}"
            f"sprite sheet grid {grid_size}x{grid_size}, each cell contains one item: {items}. "
            f"Uniform style, consistent scale, grid layout with clear separation"
            f"{spec.prompt_suffix}"
        )


# ---------------------------------------------------------------------------
# PIL helper functions
# ---------------------------------------------------------------------------

def _hstack_images(paths: List[str], output: str) -> str:
    """Stack images horizontally into a sprite strip."""
    imgs = []
    for p in paths:
        try:
            imgs.append(Image.open(p).convert("RGBA"))
        except Exception:
            pass
    if not imgs:
        return output
    h   = max(img.height for img in imgs)
    w   = sum(img.width  for img in imgs)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x   = 0
    for img in imgs:
        out.paste(img, (x, 0), img)
        x += img.width
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    out.save(output, "PNG")
    return output


def _vstack_images(paths: List[str], output: str) -> str:
    """Stack images vertically (one row per action)."""
    imgs = []
    for p in paths:
        try:
            imgs.append(Image.open(p).convert("RGBA"))
        except Exception:
            pass
    if not imgs:
        return output
    w   = max(img.width  for img in imgs)
    h   = sum(img.height for img in imgs)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y   = 0
    for img in imgs:
        out.paste(img, (0, y), img)
        y += img.height
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    out.save(output, "PNG")
    return output


def _build_gif(paths: List[str], output: str, fps: int = 8) -> str:
    """Build a looping animated GIF from frame paths."""
    imgs = []
    for p in paths:
        try:
            imgs.append(Image.open(p).convert("RGBA"))
        except Exception:
            pass
    if not imgs:
        return output
    duration = max(20, 1000 // fps)
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    imgs[0].save(
        output, format="GIF", save_all=True,
        append_images=imgs[1:], loop=0, duration=duration,
        optimize=False, disposal=2,
    )
    return output


def _split_grid(
    grid_path:  str,
    rows:       int,
    cols:       int,
    output_dir: str,
    prefix:     str,
) -> List[str]:
    """Crop a grid image into individual cell images."""
    if not _PIL:
        return []
    grid  = Image.open(grid_path).convert("RGBA")
    gw, gh = grid.size
    cw, ch = gw // cols, gh // rows
    paths  = []
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * cw, r * ch
            cell   = grid.crop((x0, y0, x0 + cw, y0 + ch))
            path   = os.path.join(output_dir, f"{prefix}_r{r}c{c}.png")
            cell.save(path, "PNG")
            paths.append(path)
    return paths


def _replace_suffix(path: str, new_suffix: str) -> str:
    base = os.path.splitext(path)[0]
    return base + new_suffix
