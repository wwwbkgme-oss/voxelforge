"""
forge.generators.dungeon
=========================
Procedural dungeon / cave generator for VoxelForge.

Generates underground dungeon levels as single-layer VoxelModel objects.
Uses BSP (Binary Space Partitioning) room generation + corridor carving.

Output is a top-down dungeon "floor" where:
  - 0   = empty (air / out-of-bounds)
  - 1–x = wall voxels
  - y   = floor voxels (walkable)

The dungeon is one voxel deep (Z = 0 floor, Z = 1..height = walls).

Example
-------
>>> from forge.generators.dungeon import DungeonGenerator
>>> from forge.voxel import Palette
>>> gen = DungeonGenerator(Palette.natural(), seed=7)
>>> dungeon = gen.generate(width=48, height=48, wall_height=4, rooms=8)
>>> dungeon.save("engine/Assets/Game/Models/dungeon_01.vox")
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..voxel import VoxelModel, Palette


# ---------------------------------------------------------------------------
# BSP helpers
# ---------------------------------------------------------------------------

@dataclass
class Room:
    x:  int
    y:  int
    w:  int
    h:  int

    @property
    def cx(self) -> int: return self.x + self.w // 2
    @property
    def cy(self) -> int: return self.y + self.h // 2
    @property
    def x2(self) -> int: return self.x + self.w - 1
    @property
    def y2(self) -> int: return self.y + self.h - 1


@dataclass
class BSPNode:
    x:  int; y: int; w: int; h: int
    left:  Optional["BSPNode"] = None
    right: Optional["BSPNode"] = None
    room:  Optional[Room]      = None

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def get_room(self) -> Optional[Room]:
        if self.room:
            return self.room
        if self.left:
            lr = self.left.get_room()
            if lr: return lr
        if self.right:
            rr = self.right.get_room()
            if rr: return rr
        return None


def _split(node: BSPNode, rng: random.Random,
           min_size: int = 6, depth: int = 0, max_depth: int = 6) -> None:
    if depth >= max_depth or node.w < min_size * 2 or node.h < min_size * 2:
        return

    # Decide split direction
    horizontal = node.h > node.w * 1.25 if node.w != node.h else rng.random() > 0.5

    if horizontal:
        split_at = rng.randint(min_size, node.h - min_size)
        node.left  = BSPNode(node.x, node.y,        node.w, split_at)
        node.right = BSPNode(node.x, node.y + split_at, node.w, node.h - split_at)
    else:
        split_at = rng.randint(min_size, node.w - min_size)
        node.left  = BSPNode(node.x,           node.y, split_at,           node.h)
        node.right = BSPNode(node.x + split_at, node.y, node.w - split_at, node.h)

    _split(node.left,  rng, min_size, depth + 1, max_depth)
    _split(node.right, rng, min_size, depth + 1, max_depth)


def _place_rooms(node: BSPNode, rng: random.Random,
                  rooms: List[Room], min_pad: int = 1) -> None:
    """Recursively place one room in each BSP leaf."""
    if node.is_leaf():
        max_w = max(4, node.w - min_pad * 2)
        max_h = max(4, node.h - min_pad * 2)
        rw = rng.randint(4, max_w)
        rh = rng.randint(4, max_h)
        rx = node.x + rng.randint(min_pad, max(min_pad, node.w - rw - min_pad))
        ry = node.y + rng.randint(min_pad, max(min_pad, node.h - rh - min_pad))
        node.room = Room(rx, ry, rw, rh)
        rooms.append(node.room)
    else:
        if node.left:  _place_rooms(node.left,  rng, rooms, min_pad)
        if node.right: _place_rooms(node.right, rng, rooms, min_pad)


def _connect_rooms(node: BSPNode, corridors: List[Tuple]) -> None:
    """Connect sibling rooms with L-shaped corridors."""
    if not node.is_leaf():
        if node.left and node.right:
            lr = node.left.get_room()
            rr = node.right.get_room()
            if lr and rr:
                corridors.append((lr, rr))
        if node.left:  _connect_rooms(node.left,  corridors)
        if node.right: _connect_rooms(node.right, corridors)


# ---------------------------------------------------------------------------
# DungeonGenerator
# ---------------------------------------------------------------------------

class DungeonGenerator:
    """Generates a voxel dungeon level using BSP partitioning."""

    def __init__(self, palette: Palette, seed: int = 0):
        self.palette = palette
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    def generate(
        self,
        width:       int = 48,
        height:      int = 48,
        wall_height: int = 3,
        style:       str = "stone",
    ) -> VoxelModel:
        """
        Generate a dungeon level.

        Parameters
        ----------
        width, height : int
            Floor plan dimensions in voxels.
        wall_height : int
            Height of walls in voxels (Z axis).
        style : str
            Colour palette style: stone | dungeon | cave | ice

        Returns
        -------
        VoxelModel
            A 3-D voxel model of the dungeon.
        """
        total_depth = wall_height + 1   # floor + walls

        model = VoxelModel.empty(width, height, total_depth, self.palette,
                                  name=f"dungeon_{style}")

        # ---- Colour scheme ----
        colors = _STYLE_COLORS.get(style, _STYLE_COLORS["stone"])
        floor_c = self._rng.randint(*colors["floor"])
        wall_c  = self._rng.randint(*colors["wall"])
        ceil_c  = self._rng.randint(*colors["ceiling"])

        # ---- Fill entire area with solid rock ----
        for x in range(width):
            for y in range(height):
                for z in range(total_depth):
                    model.set(x, y, z, wall_c)

        # ---- BSP room generation ----
        root = BSPNode(1, 1, width - 2, height - 2)
        _split(root, self._rng, min_size=6, max_depth=5)

        rooms: List[Room] = []
        _place_rooms(root, self._rng, rooms)

        corridors: List[Tuple] = []
        _connect_rooms(root, corridors)

        # ---- Carve rooms ----
        for room in rooms:
            self._carve_room(model, room, floor_c, 0, wall_height)

        # ---- Carve corridors ----
        for room_a, room_b in corridors:
            self._carve_corridor(model, room_a, room_b, floor_c, wall_height)

        # ---- Optional: ceiling ----
        # Leave open by default; uncomment to add a ceiling layer
        # for x in range(width):
        #     for y in range(height):
        #         if model.get(x, y, 1) != 0:   # not air
        #             model.set(x, y, wall_height, ceil_c)

        return model

    # ------------------------------------------------------------------
    def _carve_room(self, model: VoxelModel, room: Room,
                     floor_c: int, floor_z: int, wall_h: int) -> None:
        for x in range(room.x, room.x2 + 1):
            for y in range(room.y, room.y2 + 1):
                # Floor tile
                model.set(x, y, floor_z, floor_c)
                # Clear air above floor
                for z in range(1, wall_h):
                    model.set(x, y, z, 0)

    def _carve_corridor(self, model: VoxelModel,
                         ra: Room, rb: Room,
                         floor_c: int, wall_h: int) -> None:
        """L-shaped corridor from ra.center to rb.center."""
        x1, y1 = ra.cx, ra.cy
        x2, y2 = rb.cx, rb.cy

        # Horizontal segment
        for x in range(min(x1, x2), max(x1, x2) + 1):
            model.set(x, y1, 0, floor_c)
            for z in range(1, wall_h): model.set(x, y1, z, 0)
            # 1-wide corridor
            if 0 < y1 + 1 < model.height:
                model.set(x, y1 + 1, 0, floor_c)
                for z in range(1, wall_h): model.set(x, y1 + 1, z, 0)

        # Vertical segment
        for y in range(min(y1, y2), max(y1, y2) + 1):
            model.set(x2, y, 0, floor_c)
            for z in range(1, wall_h): model.set(x2, y, z, 0)
            if 0 < x2 + 1 < model.width:
                model.set(x2 + 1, y, 0, floor_c)
                for z in range(1, wall_h): model.set(x2 + 1, y, z, 0)


# ---------------------------------------------------------------------------
# Style definitions
# ---------------------------------------------------------------------------

_STYLE_COLORS: dict = {
    "stone": {
        "floor":   (41, 50),
        "wall":    (44, 55),
        "ceiling": (42, 50),
    },
    "dungeon": {
        "floor":   (22, 30),
        "wall":    (41, 52),
        "ceiling": (41, 48),
    },
    "cave": {
        "floor":   (22, 28),
        "wall":    (22, 35),
        "ceiling": (23, 30),
    },
    "ice": {
        "floor":   (121, 128),
        "wall":    (61, 72),
        "ceiling": (62, 70),
    },
}
