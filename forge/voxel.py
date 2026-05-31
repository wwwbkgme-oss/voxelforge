"""
forge.voxel
===========
Voxel model data structures and MagicaVoxel .vox binary file I/O.

Format reference: https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt

Supports reading and writing both single-model and multi-model .vox files.
All operations are pure Python — no C engine required.
"""

from __future__ import annotations

import io
import os
import struct
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

# Default MagicaVoxel 256-colour palette (RGBA, index 0 = empty)
_DEFAULT_PALETTE: List[Tuple[int, int, int, int]] = [
    (0, 0, 0, 0),       # 0 — transparent / empty
] + [
    (
        ((i * 37) % 256),
        ((i * 83) % 256),
        ((i * 151) % 256),
        255,
    )
    for i in range(1, 256)
]


class Palette:
    """256-entry RGBA colour palette compatible with the .vox format."""

    def __init__(self, colors: Optional[List[Tuple[int, int, int, int]]] = None):
        if colors is None:
            self._colors: List[Tuple[int, int, int, int]] = list(_DEFAULT_PALETTE)
        else:
            if len(colors) != 256:
                raise ValueError(f"Palette requires exactly 256 entries, got {len(colors)}")
            self._colors = list(colors)

    # ------------------------------------------------------------------
    def __getitem__(self, index: int) -> Tuple[int, int, int, int]:
        return self._colors[index & 0xFF]

    def __setitem__(self, index: int, value: Tuple[int, int, int, int]) -> None:
        self._colors[index & 0xFF] = value

    def __len__(self) -> int:
        return 256

    # ------------------------------------------------------------------
    def closest(self, r: int, g: int, b: int) -> int:
        """Return the palette index whose colour is closest to (r, g, b).
        Index 0 (transparent) is never returned."""
        best_idx = 1
        best_dist = float("inf")
        for i in range(1, 256):
            pr, pg, pb, _ = self._colors[i]
            dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx

    # ------------------------------------------------------------------
    @classmethod
    def grayscale(cls) -> "Palette":
        """Build a simple grayscale palette (index 1 = darkest, 255 = brightest)."""
        colors: List[Tuple[int, int, int, int]] = [(0, 0, 0, 0)]
        for i in range(1, 256):
            v = i
            colors.append((v, v, v, 255))
        return cls(colors)

    @classmethod
    def natural(cls) -> "Palette":
        """A hand-tuned palette suitable for outdoor game scenes."""
        colors: List[Tuple[int, int, int, int]] = [(0, 0, 0, 0)]
        # greens (1-20)
        for i in range(20):
            g = 80 + i * 7
            colors.append((30 + i * 2, g, 20 + i * 2, 255))
        # browns / soil (21-40)
        for i in range(20):
            colors.append((100 + i * 5, 60 + i * 3, 20 + i * 2, 255))
        # greys / stone (41-60)
        for i in range(20):
            v = 80 + i * 8
            colors.append((v, v, v, 255))
        # blues / water (61-80)
        for i in range(20):
            colors.append((20 + i * 3, 60 + i * 4, 180 + i, 255))
        # warm reds / buildings (81-100)
        for i in range(20):
            colors.append((180 + i * 3, 60 + i * 3, 40 + i * 2, 255))
        # yellows / sand (101-120)
        for i in range(20):
            v = 200 + i
            colors.append((v, v - 20, 80 + i * 2, 255))
        # whites / snow (121-130)
        for i in range(10):
            v = 220 + i * 3
            colors.append((v, v, v + 5, 255))
        # fill remaining with generic varied colours
        idx = len(colors)
        while len(colors) < 256:
            colors.append(((idx * 37) % 256, (idx * 83) % 256, (idx * 151) % 256, 255))
            idx += 1
        return cls(colors)

    # ------------------------------------------------------------------
    def to_bytes(self) -> bytes:
        """Encode the palette as 256 × 4 bytes (RGBA)."""
        out = bytearray()
        for r, g, b, a in self._colors:
            out += struct.pack("BBBB", r, g, b, a)
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Palette":
        if len(data) < 256 * 4:
            raise ValueError("Palette data too short")
        colors = []
        for i in range(256):
            r, g, b, a = struct.unpack_from("BBBB", data, i * 4)
            colors.append((r, g, b, a))
        return cls(colors)


# ---------------------------------------------------------------------------
# VoxelModel
# ---------------------------------------------------------------------------

@dataclass
class VoxelModel:
    """
    A 3-D voxel grid.

    ``data`` is a uint8 numpy array with shape ``(x, y, z)``.
    Value 0 = empty.  Values 1–255 are palette indices.
    """

    data: np.ndarray         # shape (x, y, z), dtype uint8
    palette: Palette = field(default_factory=Palette.natural)
    name: str = "model"

    # ------------------------------------------------------------------
    @classmethod
    def empty(cls, width: int, height: int, depth: int,
              palette: Optional[Palette] = None, name: str = "model") -> "VoxelModel":
        data = np.zeros((width, height, depth), dtype=np.uint8)
        return cls(data=data, palette=palette or Palette.natural(), name=name)

    # ------------------------------------------------------------------
    @property
    def width(self) -> int:   return self.data.shape[0]
    @property
    def height(self) -> int:  return self.data.shape[1]
    @property
    def depth(self) -> int:   return self.data.shape[2]

    def get(self, x: int, y: int, z: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.depth:
            return int(self.data[x, y, z])
        return 0

    def set(self, x: int, y: int, z: int, color_index: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height and 0 <= z < self.depth:
            self.data[x, y, z] = color_index & 0xFF

    def fill(self, x0: int, y0: int, z0: int,
             x1: int, y1: int, z1: int, color_index: int) -> None:
        """Fill a rectangular box with a colour."""
        x0, x1 = sorted((max(0, x0), min(self.width - 1,  x1)))
        y0, y1 = sorted((max(0, y0), min(self.height - 1, y1)))
        z0, z1 = sorted((max(0, z0), min(self.depth - 1,  z1)))
        self.data[x0:x1+1, y0:y1+1, z0:z1+1] = color_index & 0xFF

    # ------------------------------------------------------------------
    def voxels(self) -> Iterator[Tuple[int, int, int, int]]:
        """Yield (x, y, z, color) for every non-empty voxel."""
        xs, ys, zs = np.where(self.data != 0)
        for x, y, z in zip(xs, ys, zs):
            yield int(x), int(y), int(z), int(self.data[x, y, z])

    def voxel_count(self) -> int:
        return int(np.count_nonzero(self.data))

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Write a single-model MagicaVoxel .vox file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as f:
            f.write(self._encode())

    def _encode(self) -> bytes:
        buf = io.BytesIO()

        # --- Header ---
        buf.write(b"VOX ")
        buf.write(struct.pack("<i", 150))  # version

        # --- MAIN chunk (will be patched at end) ---
        main_start = buf.tell()
        buf.write(b"MAIN")
        buf.write(struct.pack("<ii", 0, 0))  # sizes — filled in later

        child_start = buf.tell()

        # --- SIZE chunk ---
        size_data = struct.pack("<iii", self.width, self.height, self.depth)
        buf.write(b"SIZE")
        buf.write(struct.pack("<ii", len(size_data), 0))
        buf.write(size_data)

        # --- XYZI chunk ---
        vox_list = list(self.voxels())
        xyzi_data = struct.pack("<i", len(vox_list))
        for x, y, z, c in vox_list:
            xyzi_data += struct.pack("BBBB", x, y, z, c)
        buf.write(b"XYZI")
        buf.write(struct.pack("<ii", len(xyzi_data), 0))
        buf.write(xyzi_data)

        # --- RGBA palette chunk ---
        rgba_data = self.palette.to_bytes()
        buf.write(b"RGBA")
        buf.write(struct.pack("<ii", len(rgba_data), 0))
        buf.write(rgba_data)

        child_end = buf.tell()

        # Patch MAIN chunk sizes
        buf.seek(main_start + 4)
        buf.write(struct.pack("<ii", 0, child_end - child_start))

        return buf.getvalue()

    @classmethod
    def load(cls, path: str) -> "VoxelModel":
        """Load a MagicaVoxel .vox file (single-model only)."""
        with open(path, "rb") as f:
            data = f.read()
        return cls._decode(data, name=os.path.splitext(os.path.basename(path))[0])

    @classmethod
    def _decode(cls, data: bytes, name: str = "model") -> "VoxelModel":
        buf = io.BytesIO(data)

        magic = buf.read(4)
        if magic != b"VOX ":
            raise ValueError(f"Not a .vox file (magic={magic!r})")
        _version = struct.unpack("<i", buf.read(4))[0]

        dims: Optional[Tuple[int, int, int]] = None
        voxels_raw: List[Tuple[int, int, int, int]] = []
        palette_raw: Optional[bytes] = None

        def read_chunk(buf: io.BytesIO):
            hdr = buf.read(4)
            if not hdr:
                return None, None, None
            chunk_id = hdr
            chunk_size, child_size = struct.unpack("<ii", buf.read(8))
            chunk_data = buf.read(chunk_size)
            # skip children (we'll recurse on the outer loop)
            return chunk_id, chunk_data, child_size

        while True:
            chunk_id, chunk_data, _ = read_chunk(buf)
            if chunk_id is None:
                break
            if chunk_id == b"SIZE":
                dims = struct.unpack_from("<iii", chunk_data)
            elif chunk_id == b"XYZI":
                n = struct.unpack_from("<i", chunk_data)[0]
                for i in range(n):
                    x, y, z, c = struct.unpack_from("BBBB", chunk_data, 4 + i * 4)
                    voxels_raw.append((x, y, z, c))
            elif chunk_id == b"RGBA":
                palette_raw = chunk_data
            elif chunk_id == b"MAIN":
                # MAIN has no own data; children are in the file stream
                pass

        if dims is None:
            raise ValueError("No SIZE chunk found in .vox file")

        w, h, d = dims
        arr = np.zeros((w, h, d), dtype=np.uint8)
        for x, y, z, c in voxels_raw:
            if 0 <= x < w and 0 <= y < h and 0 <= z < d:
                arr[x, y, z] = c

        pal = Palette.from_bytes(palette_raw) if palette_raw else Palette.natural()
        return cls(data=arr, palette=pal, name=name)


# ---------------------------------------------------------------------------
# Multi-object .vox bundle helper
# ---------------------------------------------------------------------------

def save_multi_vox(models: Dict[str, VoxelModel], path: str) -> None:
    """
    Write multiple named VoxelModel objects to a single .vox file.
    Uses the simplest representation: sequential SIZE/XYZI pairs.
    The first model's palette is used for all models.
    """
    if not models:
        raise ValueError("models dict is empty")

    buf = io.BytesIO()
    buf.write(b"VOX ")
    buf.write(struct.pack("<i", 150))

    main_start = buf.tell()
    buf.write(b"MAIN")
    buf.write(struct.pack("<ii", 0, 0))

    child_start = buf.tell()
    pal = next(iter(models.values())).palette

    for _name, model in models.items():
        size_data = struct.pack("<iii", model.width, model.height, model.depth)
        buf.write(b"SIZE")
        buf.write(struct.pack("<ii", len(size_data), 0))
        buf.write(size_data)

        vox_list = list(model.voxels())
        xyzi_data = struct.pack("<i", len(vox_list))
        for x, y, z, c in vox_list:
            xyzi_data += struct.pack("BBBB", x, y, z, c)
        buf.write(b"XYZI")
        buf.write(struct.pack("<ii", len(xyzi_data), 0))
        buf.write(xyzi_data)

    rgba_data = pal.to_bytes()
    buf.write(b"RGBA")
    buf.write(struct.pack("<ii", len(rgba_data), 0))
    buf.write(rgba_data)

    child_end = buf.tell()
    buf.seek(main_start + 4)
    buf.write(struct.pack("<ii", 0, child_end - child_start))

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(buf.getvalue())
