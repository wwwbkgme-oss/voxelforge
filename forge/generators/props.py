"""
forge.generators.props
=======================
Small prop / scenery generators for VoxelForge.

Available props:
    tree        - simple oak / pine tree
    crate       - wooden crate of any size
    barrel      - wooden barrel
    lamp_post   - street lamp
    rock        - natural rock cluster
    chest       - treasure chest
    mushroom    - giant mushroom

Example
-------
>>> from forge.generators import PropGenerator
>>> gen = PropGenerator(Palette.natural(), seed=99)
>>> tree = gen.generate("tree", variant="oak")
>>> tree.save("engine/Assets/Game/Models/oak_tree.vox")
"""

from __future__ import annotations

import random
from ..voxel import VoxelModel, Palette


class PropGenerator:
    """Generates small prop / scenery voxel models."""

    def __init__(self, palette: Palette, seed: int = 0):
        self.palette = palette
        self._rng = random.Random(seed)

    def _c(self, lo: int, hi: int) -> int:
        return self._rng.randint(lo, hi)

    # ------------------------------------------------------------------
    def generate(self, prop_type: str, variant: str = "", name: str = "",
                 **kwargs) -> VoxelModel:
        """
        Generate a prop.

        Parameters
        ----------
        prop_type : str
            tree | crate | barrel | lamp_post | rock | chest | mushroom
        variant : str
            Optional sub-variant (e.g. "oak", "pine" for trees).
        **kwargs
            Extra size/style arguments passed to the specific generator.

        Returns
        -------
        VoxelModel
        """
        fn = {
            "tree":      self._tree,
            "crate":     self._crate,
            "barrel":    self._barrel,
            "lamp_post": self._lamp_post,
            "rock":      self._rock,
            "chest":     self._chest,
            "mushroom":  self._mushroom,
        }.get(prop_type)
        if fn is None:
            raise ValueError(f"Unknown prop_type '{prop_type}'. "
                             f"Choose from: tree, crate, barrel, lamp_post, rock, chest, mushroom")
        model = fn(variant=variant, **kwargs)
        if name:
            model.name = name
        return model

    # ------------------------------------------------------------------
    def _tree(self, variant: str = "oak", **_) -> VoxelModel:
        """Generate an oak or pine tree."""
        trunk_c  = self._c(22, 28)
        leaves_c = self._c(1, 18)

        if variant == "pine":
            # Narrow pine tree 5×5×14
            m = VoxelModel.empty(5, 5, 14, self.palette, name="tree_pine")
            # Trunk
            for z in range(5):
                m.set(2, 2, z, trunk_c)
            # Layered triangle canopy
            layers = [(4, 0), (3, 2), (2, 4), (1, 6), (0, 9)]
            for r, z_start in layers:
                for z in range(z_start, min(z_start + 2, 14)):
                    for x in range(2-r, 3+r):
                        for y in range(2-r, 3+r):
                            m.set(x, y, z, leaves_c)
        else:
            # Rounded oak tree 7×7×12
            m = VoxelModel.empty(7, 7, 12, self.palette, name="tree_oak")
            cx, cy = 3, 3
            # Trunk
            for z in range(5):
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if abs(dx) + abs(dy) <= 1:
                            m.set(cx+dx, cy+dy, z, trunk_c)
            # Spherical canopy
            for x in range(7):
                for y in range(7):
                    for z in range(4, 12):
                        dx, dy, dz = x-cx, y-cy, z-8
                        if dx*dx + dy*dy + dz*dz*0.6 <= 9:
                            m.set(x, y, z, leaves_c)

        return m

    # ------------------------------------------------------------------
    def _crate(self, size: int = 4, **_) -> VoxelModel:
        wood_c  = self._c(22, 30)
        metal_c = self._c(42, 52)
        m = VoxelModel.empty(size, size, size, self.palette, name="crate")
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    edge = sum([
                        x in (0, size-1),
                        y in (0, size-1),
                        z in (0, size-1),
                    ])
                    if edge >= 2:
                        m.set(x, y, z, metal_c)
                    elif edge == 1:
                        m.set(x, y, z, wood_c)
        return m

    # ------------------------------------------------------------------
    def _barrel(self, **_) -> VoxelModel:
        wood_c  = self._c(22, 32)
        hoop_c  = self._c(42, 50)
        m = VoxelModel.empty(4, 4, 5, self.palette, name="barrel")
        for z in range(5):
            c = hoop_c if z in (0, 2, 4) else wood_c
            for x in range(4):
                for y in range(4):
                    if (x == 0 or x == 3 or y == 0 or y == 3):
                        m.set(x, y, z, c)
        return m

    # ------------------------------------------------------------------
    def _lamp_post(self, **_) -> VoxelModel:
        pole_c  = self._c(42, 52)
        light_c = self._c(101, 110)
        m = VoxelModel.empty(3, 3, 10, self.palette, name="lamp_post")
        # Pole
        for z in range(9):
            m.set(1, 1, z, pole_c)
        # Lamp head
        for x in range(3):
            for y in range(3):
                m.set(x, y, 9, light_c)
        return m

    # ------------------------------------------------------------------
    def _rock(self, size: int = 5, **_) -> VoxelModel:
        rock_c = self._c(41, 60)
        m = VoxelModel.empty(size, size, size//2+1, self.palette, name="rock")
        cx, cy = size//2, size//2
        for x in range(size):
            for y in range(size):
                for z in range(m.depth):
                    dx, dy = x-cx, y-cy
                    if dx*dx*1.5 + dy*dy*1.5 + z*z*2 <= (size//2)**2 * 1.3:
                        m.set(x, y, z, rock_c)
        return m

    # ------------------------------------------------------------------
    def _chest(self, **_) -> VoxelModel:
        wood_c  = self._c(22, 30)
        metal_c = self._c(101, 110)
        m = VoxelModel.empty(6, 4, 4, self.palette, name="chest")
        # Body
        for x in range(6):
            for y in range(4):
                for z in range(2):
                    is_border = (x in (0,5) or y in (0,3) or z == 0)
                    m.set(x, y, z, metal_c if is_border else wood_c)
        # Lid
        for x in range(6):
            for y in range(4):
                for z in range(2, 4):
                    is_border = (x in (0,5) or y in (0,3) or z == 3)
                    m.set(x, y, z, metal_c if is_border else wood_c)
        # Lock
        m.set(3, 0, 2, metal_c)
        m.set(2, 0, 2, metal_c)
        return m

    # ------------------------------------------------------------------
    def _mushroom(self, **_) -> VoxelModel:
        stem_c = self._c(121, 130)
        cap_c  = self._c(81, 95)
        m = VoxelModel.empty(7, 7, 8, self.palette, name="mushroom")
        cx, cy = 3, 3
        # Stem
        for z in range(4):
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    m.set(cx+dx, cy+dy, z, stem_c)
        # Cap dome
        for x in range(7):
            for y in range(7):
                for z in range(3, 8):
                    dx, dy, dz = x-cx, y-cy, z-5
                    if dx*dx + dy*dy + dz*dz*0.5 <= 9:
                        m.set(x, y, z, cap_c)
        return m
