"""
forge.export.sprite_renderer
=============================
Pure-Python isometric voxel sprite renderer.

Renders a VoxelModel to a PIL Image (or saves a PNG) without needing
the C engine or OpenGL.  The output is a pixel-art isometric sprite —
the same visual style as the VoxelForge engine renders at runtime.

This is useful for:
  - Previewing generated assets before loading them in the engine
  - Generating thumbnails for the web dashboard
  - Building asset catalogues

Dependencies:
    pip install Pillow

Example
-------
>>> from forge.export.sprite_renderer import render_vox_to_png
>>> render_vox_to_png("engine/Assets/Game/Models/char.vox", "char_preview.png")

>>> from forge.voxel import VoxelModel
>>> from forge.export.sprite_renderer import VoxelSpriteRenderer
>>> m = VoxelModel.load("engine/Assets/Game/Models/City.vox")
>>> img = VoxelSpriteRenderer().render(m)
>>> img.save("city_preview.png")
"""

from __future__ import annotations

import os
from typing import Optional, Tuple


try:
    from PIL import Image, ImageDraw   # type: ignore
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

from ..voxel import VoxelModel


# ---------------------------------------------------------------------------
# Isometric projection helpers
# ---------------------------------------------------------------------------

def _iso_project(x: float, y: float, z: float,
                  tile_w: int = 8, tile_h: int = 4) -> Tuple[int, int]:
    """
    Convert a 3-D voxel position to 2-D isometric screen coordinates.

    The engine uses an isometric view with:
      - x increases right-and-down on screen
      - y increases left-and-down on screen
      - z increases upward on screen
    """
    sx = int((x - y) * tile_w // 2)
    sy = int((x + y) * tile_h // 2 - z * tile_h)
    return sx, sy


def _darken(r: int, g: int, b: int, factor: float) -> Tuple[int, int, int]:
    return (int(r * factor), int(g * factor), int(b * factor))


# ---------------------------------------------------------------------------
# VoxelSpriteRenderer
# ---------------------------------------------------------------------------

class VoxelSpriteRenderer:
    """
    Renders a VoxelModel to a PIL Image in isometric pixel-art style.

    Parameters
    ----------
    tile_w : int
        Width of one voxel tile in pixels (even number recommended).
    tile_h : int
        Half-height of one voxel tile in pixels.
    padding : int
        Padding around the sprite in pixels.
    bg_color : tuple or None
        Background RGBA.  ``None`` = transparent.
    """

    def __init__(
        self,
        tile_w: int = 8,
        tile_h: int = 4,
        padding: int = 4,
        bg_color: Optional[Tuple[int, int, int, int]] = None,
    ):
        if not _PIL_AVAILABLE:
            raise RuntimeError(
                "Pillow is required for sprite rendering. "
                "Install with: pip install Pillow"
            )
        self.tile_w  = tile_w
        self.tile_h  = tile_h
        self.padding = padding
        self.bg_color = bg_color

    # ------------------------------------------------------------------
    def render(self, model: VoxelModel) -> "Image.Image":
        """
        Render the model and return a PIL Image.

        Visible (surface) voxels are detected and drawn back-to-front
        (painter's algorithm) with simple top/left/right face shading.
        """
        # Collect surface voxels
        voxels = []
        w, h, d = model.width, model.height, model.depth

        for x in range(w):
            for y in range(h):
                for z in range(d):
                    if model.get(x, y, z) == 0:
                        continue
                    # Visible if at least one face is exposed
                    exposed = (
                        x + 1 >= w or model.get(x+1, y,   z  ) == 0 or
                        y + 1 >= h or model.get(x,   y+1, z  ) == 0 or
                        z + 1 >= d or model.get(x,   y,   z+1) == 0
                    )
                    if exposed:
                        voxels.append((x, y, z, model.get(x, y, z)))

        if not voxels:
            return Image.new("RGBA", (32, 32), (0, 0, 0, 0))

        # Determine canvas size
        tw, th = self.tile_w, self.tile_h
        xs, ys = zip(*[_iso_project(x, y, z, tw, th) for x, y, z, _ in voxels])
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        offset_x = -min_x + self.padding + tw
        offset_y = -min_y + self.padding + th * 2

        img_w = max_x - min_x + 2 * self.padding + tw * 2
        img_h = max_y - min_y + 2 * self.padding + th * 4

        img = Image.new("RGBA", (img_w, img_h),
                        self.bg_color or (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Sort painter's order: back-to-front (increasing x+y, then z)
        voxels_sorted = sorted(voxels, key=lambda v: (v[0] + v[1], v[2]))

        pal = model.palette

        for x, y, z, c in voxels_sorted:
            r, g, b, a = pal[c]
            if a == 0:
                continue

            sx, sy = _iso_project(x, y, z, tw, th)
            sx += offset_x
            sy += offset_y

            half_w = tw // 2
            half_h = th // 2

            # Top face (lightest)
            top_pts = [
                (sx,          sy         ),
                (sx + half_w, sy + half_h),
                (sx,          sy + th    ),
                (sx - half_w, sy + half_h),
            ]
            draw.polygon(top_pts, fill=(r, g, b, a))

            # Right face (medium)
            rm, gm, bm = _darken(r, g, b, 0.72)
            right_pts = [
                (sx,          sy + th    ),
                (sx + half_w, sy + half_h),
                (sx + half_w, sy + half_h + th),
                (sx,          sy + th * 2),
            ]
            draw.polygon(right_pts, fill=(rm, gm, bm, a))

            # Left face (darkest)
            rl, gl, bl = _darken(r, g, b, 0.55)
            left_pts = [
                (sx - half_w, sy + half_h),
                (sx,          sy + th    ),
                (sx,          sy + th * 2),
                (sx - half_w, sy + half_h + th),
            ]
            draw.polygon(left_pts, fill=(rl, gl, bl, a))

        return img

    # ------------------------------------------------------------------
    def render_to_file(self, model: VoxelModel, path: str) -> str:
        """Render the model and save to ``path`` as PNG.  Returns the path."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        img = self.render(model)
        img.save(path, "PNG")
        return path


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def render_vox_to_png(
    vox_path: str,
    out_path:  str,
    tile_w: int = 8,
    tile_h: int = 4,
) -> str:
    """
    Load a .vox file and render it as an isometric PNG sprite.

    Returns the output path.
    """
    model = VoxelModel.load(vox_path)
    renderer = VoxelSpriteRenderer(tile_w=tile_w, tile_h=tile_h)
    return renderer.render_to_file(model, out_path)


def render_all_assets(
    assets_dir: str = "generated_assets",
    thumbs_dir: str = "generated_assets/thumbnails",
) -> int:
    """
    Render all .vox files in ``assets_dir`` to PNG thumbnails.
    Returns the number of thumbnails generated.
    """
    import glob
    renderer = VoxelSpriteRenderer()
    count = 0
    for vox in glob.glob(os.path.join(assets_dir, "**", "*.vox"), recursive=True):
        name = os.path.splitext(os.path.basename(vox))[0]
        out  = os.path.join(thumbs_dir, f"{name}.png")
        try:
            model = VoxelModel.load(vox)
            renderer.render_to_file(model, out)
            count += 1
        except Exception:
            pass
    return count
