"""
forge.generators.terrain
========================
Procedural terrain generation for VoxelForge.

Generates voxel terrain using multi-octave Perlin-style noise with support
for biome blending (grassland, desert, snow, forest floor, ocean).

The output is a single VoxelModel ready to be written as a .vox file.

Example
-------
>>> from forge.generators import TerrainGenerator
>>> from forge.voxel import Palette
>>> gen = TerrainGenerator(Palette.natural(), seed=42)
>>> terrain = gen.generate(width=64, height=64, max_depth=16, biome="grassland")
>>> terrain.save("engine/Assets/Game/Models/terrain.vox")
"""

from __future__ import annotations

import math
import random
from typing import Tuple

import numpy as np

from ..voxel import VoxelModel, Palette


# ---------------------------------------------------------------------------
# Simple Perlin-like noise helpers (no external dependency)
# ---------------------------------------------------------------------------

def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _grad(h: int, x: float, y: float) -> float:
    h &= 3
    if h == 0: return  x + y
    if h == 1: return -x + y
    if h == 2: return  x - y
    return -x - y


class _Noise2D:
    """Minimal 2-D value noise implementation seeded deterministically."""

    def __init__(self, seed: int = 0):
        rng = random.Random(seed)
        p = list(range(256))
        rng.shuffle(p)
        self._perm = p * 2

    def noise(self, x: float, y: float) -> float:
        xi = int(math.floor(x)) & 0xFF
        yi = int(math.floor(y)) & 0xFF
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u, v = _fade(xf), _fade(yf)

        aa = self._perm[self._perm[xi]     + yi]
        ab = self._perm[self._perm[xi]     + yi + 1]
        ba = self._perm[self._perm[xi + 1] + yi]
        bb = self._perm[self._perm[xi + 1] + yi + 1]

        x1 = _lerp(_grad(aa, xf,     yf    ),
                   _grad(ba, xf - 1, yf    ), u)
        x2 = _lerp(_grad(ab, xf,     yf - 1),
                   _grad(bb, xf - 1, yf - 1), u)
        return (_lerp(x1, x2, v) + 1) * 0.5   # normalise to [0, 1]

    def fbm(self, x: float, y: float, octaves: int = 4,
            lacunarity: float = 2.0, gain: float = 0.5) -> float:
        """Fractional Brownian Motion — sums noise at multiple scales."""
        value, amp, freq = 0.0, 1.0, 1.0
        for _ in range(octaves):
            value += self.noise(x * freq, y * freq) * amp
            amp   *= gain
            freq  *= lacunarity
        # Normalise to [0, 1]
        max_val = sum(gain ** i for i in range(octaves))
        return value / max_val


# ---------------------------------------------------------------------------
# Biome definitions
# ---------------------------------------------------------------------------

_BIOMES: dict = {
    # (surface_lo, surface_hi, subsurface_lo, subsurface_hi, water_level_frac)
    "grassland": {
        "surface_colors":    [(20, 70),  (21, 71), (22, 72)],   # green
        "subsurface_colors": [(22, 28),  (23, 29), (24, 30)],   # brown
        "rock_colors":       [(41, 60)],
        "water_level":       0.30,
        "water_colors":      [(61, 70)],
        "snow_threshold":    0.90,
    },
    "desert": {
        "surface_colors":    [(101, 115), (102, 116)],
        "subsurface_colors": [(101, 112), (103, 114)],
        "rock_colors":       [(103, 110)],
        "water_level":       0.10,
        "water_colors":      [(101, 110)],
        "snow_threshold":    1.00,
    },
    "snow": {
        "surface_colors":    [(121, 130), (122, 130)],
        "subsurface_colors": [(41, 55)],
        "rock_colors":       [(41, 60)],
        "water_level":       0.20,
        "water_colors":      [(61, 70)],
        "snow_threshold":    0.50,
    },
    "ocean": {
        "surface_colors":    [(1, 20)],
        "subsurface_colors": [(22, 30)],
        "rock_colors":       [(41, 60)],
        "water_level":       0.70,
        "water_colors":      [(61, 80)],
        "snow_threshold":    1.00,
    },
    "forest": {
        "surface_colors":    [(1, 18)],
        "subsurface_colors": [(21, 30)],
        "rock_colors":       [(41, 60)],
        "water_level":       0.35,
        "water_colors":      [(61, 70)],
        "snow_threshold":    0.95,
    },
}


def _pick(rng: random.Random, ranges: list) -> int:
    lo, hi = rng.choice(ranges)
    return rng.randint(lo, hi)


# ---------------------------------------------------------------------------
# TerrainGenerator
# ---------------------------------------------------------------------------

class TerrainGenerator:
    """
    Generates terrain voxel models.

    Parameters
    ----------
    palette : Palette
        The colour palette to use.
    seed : int
        Deterministic seed for reproducible generation.
    """

    def __init__(self, palette: Palette, seed: int = 0):
        self.palette = palette
        self.seed    = seed
        self._rng    = random.Random(seed)
        self._noise  = _Noise2D(seed)

    # ------------------------------------------------------------------
    def generate(
        self,
        width:    int  = 32,
        height:   int  = 32,
        max_depth: int = 12,
        biome:    str  = "grassland",
        scale:    float = 0.08,
        octaves:  int  = 5,
    ) -> VoxelModel:
        """
        Generate a terrain VoxelModel.

        Parameters
        ----------
        width, height : int
            XY footprint of the terrain.
        max_depth : int
            Maximum height of the terrain column (Z axis).
        biome : str
            One of: grassland, desert, snow, ocean, forest.
        scale : float
            Noise frequency — higher values produce more varied terrain.
        octaves : int
            Number of FBM octaves — more octaves produce more detail.

        Returns
        -------
        VoxelModel
        """
        bdef = _BIOMES.get(biome, _BIOMES["grassland"])
        water_z = int(bdef["water_level"] * max_depth)

        model = VoxelModel.empty(width, height, max_depth, self.palette, name=f"terrain_{biome}")

        for x in range(width):
            for y in range(height):
                # Heightmap value 0..1
                h = self._noise.fbm(x * scale, y * scale, octaves=octaves)
                col_height = max(1, int(h * max_depth))

                for z in range(col_height):
                    frac = z / max(1, col_height - 1)
                    if z == col_height - 1:
                        # Top voxel
                        if frac >= bdef["snow_threshold"]:
                            c = _pick(self._rng, _BIOMES["snow"]["surface_colors"])
                        else:
                            c = _pick(self._rng, bdef["surface_colors"])
                    elif z >= col_height - 3:
                        c = _pick(self._rng, bdef["subsurface_colors"])
                    else:
                        # Deep rock
                        c = _pick(self._rng, bdef["rock_colors"])
                    model.set(x, y, z, c)

                # Fill water
                if col_height <= water_z:
                    for z in range(col_height, water_z + 1):
                        c = _pick(self._rng, bdef["water_colors"])
                        model.set(x, y, z, c)

        return model

    # ------------------------------------------------------------------
    def generate_heightmap(
        self,
        width:  int   = 64,
        height: int   = 64,
        scale:  float = 0.08,
        octaves: int  = 5,
    ) -> np.ndarray:
        """Return a (width, height) float array of noise values in [0, 1]."""
        arr = np.zeros((width, height), dtype=np.float32)
        for x in range(width):
            for y in range(height):
                arr[x, y] = self._noise.fbm(x * scale, y * scale, octaves=octaves)
        return arr
