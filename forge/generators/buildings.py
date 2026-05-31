"""
forge.generators.buildings
===========================
Procedural building generator for VoxelForge.

Generates multi-floor buildings with configurable style, window placement,
roof type, and facade material — all as VoxelModel objects.

Example
-------
>>> from forge.generators import BuildingGenerator
>>> gen = BuildingGenerator(Palette.natural(), seed=7)
>>> tower = gen.generate(width=10, depth=10, floors=5, style="medieval")
>>> tower.save("engine/Assets/Game/Models/tower.vox")
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Tuple

from ..voxel import VoxelModel, Palette


# ---------------------------------------------------------------------------
# Style presets
# ---------------------------------------------------------------------------

@dataclass
class BuildingStyle:
    wall_colors:   list   # palette index ranges [(lo,hi),…]
    window_color:  int    # palette index
    door_color:    int
    roof_colors:   list
    roof_type:     str    # flat | peaked | pyramid
    floor_height:  int    # voxels per floor
    window_every:  int    # gap between windows
    window_w:      int
    window_h:      int


_STYLES: dict[str, BuildingStyle] = {
    "modern": BuildingStyle(
        wall_colors=  [(41, 55)],
        window_color= 62,
        door_color=   42,
        roof_colors=  [(50, 59)],
        roof_type=    "flat",
        floor_height= 4,
        window_every= 3,
        window_w=     2,
        window_h=     2,
    ),
    "medieval": BuildingStyle(
        wall_colors=  [(81, 95)],
        window_color= 63,
        door_color=   83,
        roof_colors=  [(81, 90)],
        roof_type=    "peaked",
        floor_height= 5,
        window_every= 4,
        window_w=     1,
        window_h=     2,
    ),
    "sci-fi": BuildingStyle(
        wall_colors=  [(41, 50)],
        window_color= 65,
        door_color=   65,
        roof_colors=  [(41, 48)],
        roof_type=    "flat",
        floor_height= 4,
        window_every= 2,
        window_w=     1,
        window_h=     3,
    ),
    "rustic": BuildingStyle(
        wall_colors=  [(21, 35)],
        window_color= 62,
        door_color=   24,
        roof_colors=  [(82, 92)],
        roof_type=    "pyramid",
        floor_height= 4,
        window_every= 4,
        window_w=     1,
        window_h=     2,
    ),
    "fantasy": BuildingStyle(
        wall_colors=  [(61, 79)],
        window_color= 121,
        door_color=   66,
        roof_colors=  [(81, 100)],
        roof_type=    "peaked",
        floor_height= 5,
        window_every= 3,
        window_w=     2,
        window_h=     2,
    ),
}


# ---------------------------------------------------------------------------
# BuildingGenerator
# ---------------------------------------------------------------------------

class BuildingGenerator:
    """Generates voxel building models procedurally."""

    def __init__(self, palette: Palette, seed: int = 0):
        self.palette = palette
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    def generate(
        self,
        width:  int = 8,
        depth:  int = 8,
        floors: int = 3,
        style:  str = "modern",
        name:   str = "",
    ) -> VoxelModel:
        """
        Generate a building.

        Parameters
        ----------
        width, depth : int
            Footprint dimensions (X and Y axes).
        floors : int
            Number of floors.
        style : str
            One of: modern, medieval, sci-fi, rustic, fantasy.

        Returns
        -------
        VoxelModel
        """
        s = _STYLES.get(style, _STYLES["modern"])
        roof_extra = 5 if s.roof_type == "peaked" else (4 if s.roof_type == "pyramid" else 1)
        total_h = floors * s.floor_height + roof_extra
        model = VoxelModel.empty(width, depth, total_h, self.palette,
                                  name=name or f"building_{style}")

        # --- Walls ---
        for floor in range(floors):
            z_base = floor * s.floor_height
            for z in range(s.floor_height):
                zz = z_base + z
                wall_c = self._rng.randint(*self._rng.choice(s.wall_colors))
                for x in range(width):
                    for y in range(depth):
                        is_border = (x == 0 or x == width-1 or y == 0 or y == depth-1)
                        if is_border:
                            model.set(x, y, zz, wall_c)

            # --- Windows on this floor ---
            win_z = z_base + 1
            if z + 1 < s.floor_height - 1:
                pass  # window fits
            self._place_windows(model, floor, z_base, s, width, depth)

        # --- Door (ground floor, front face) ---
        door_x = width // 2 - 1
        for z in range(min(3, s.floor_height - 1)):
            model.set(door_x,     0, z, s.door_color)
            model.set(door_x + 1, 0, z, s.door_color)

        # --- Roof ---
        z_roof = floors * s.floor_height
        self._build_roof(model, width, depth, z_roof, s)

        return model

    # ------------------------------------------------------------------
    def _place_windows(
        self, model: VoxelModel, floor: int, z_base: int,
        s: BuildingStyle, width: int, depth: int
    ) -> None:
        win_z_lo = z_base + 1
        win_z_hi = z_base + 1 + s.window_h - 1

        # Front and back faces (y=0 and y=depth-1)
        for face_y in (0, depth - 1):
            x = 2
            while x + s.window_w <= width - 2:
                for wz in range(win_z_lo, min(win_z_hi + 1, model.depth)):
                    for wx in range(s.window_w):
                        model.set(x + wx, face_y, wz, s.window_color)
                x += s.window_w + s.window_every

        # Left and right faces (x=0 and x=width-1)
        for face_x in (0, width - 1):
            y = 2
            while y + s.window_w <= depth - 2:
                for wz in range(win_z_lo, min(win_z_hi + 1, model.depth)):
                    for wy in range(s.window_w):
                        model.set(face_x, y + wy, wz, s.window_color)
                y += s.window_w + s.window_every

    # ------------------------------------------------------------------
    def _build_roof(
        self, model: VoxelModel, width: int, depth: int,
        z_roof: int, s: BuildingStyle
    ) -> None:
        roof_c = self._rng.randint(*self._rng.choice(s.roof_colors))

        if s.roof_type == "flat":
            for x in range(width):
                for y in range(depth):
                    model.set(x, y, z_roof, roof_c)

        elif s.roof_type == "peaked":
            layers = min(width, depth) // 2
            for layer in range(layers):
                z = z_roof + layer
                if z >= model.depth:
                    break
                for x in range(layer, width - layer):
                    model.set(x, layer,         z, roof_c)
                    model.set(x, depth-1-layer, z, roof_c)
                for y in range(layer, depth - layer):
                    model.set(layer,         y, z, roof_c)
                    model.set(width-1-layer, y, z, roof_c)

        elif s.roof_type == "pyramid":
            cx, cy = width // 2, depth // 2
            layers = min(cx, cy)
            for layer in range(layers):
                z = z_roof + layer
                if z >= model.depth:
                    break
                for x in range(layer, width - layer):
                    for y in range(layer, depth - layer):
                        if (x == layer or x == width-1-layer or
                                y == layer or y == depth-1-layer):
                            model.set(x, y, z, roof_c)
            # cap
            if z_roof + layers < model.depth:
                model.set(cx, cy, z_roof + layers, roof_c)
