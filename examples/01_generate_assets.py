"""
Example 01 — Generate individual assets directly from Python
============================================================
No API server needed.  This script uses the forge generators directly
to create terrain, a building, a character, and some props.

Run:
    pip install -e .
    python examples/01_generate_assets.py
"""

import os
from forge.voxel import Palette, VoxelModel
from forge.generators import (
    TerrainGenerator,
    BuildingGenerator,
    CharacterGenerator,
    PropGenerator,
)

OUT = "examples/output"
os.makedirs(OUT, exist_ok=True)

palette = Palette.natural()

# --- Terrain ---
print("Generating terrain…")
terrain = TerrainGenerator(palette, seed=42).generate(
    width=32, height=32, max_depth=14, biome="grassland"
)
terrain.save(f"{OUT}/terrain.vox")
print(f"  → {OUT}/terrain.vox  ({terrain.voxel_count()} voxels)")

# --- Building ---
print("Generating building…")
building = BuildingGenerator(palette, seed=7).generate(
    width=10, depth=10, floors=4, style="medieval", name="tavern"
)
building.save(f"{OUT}/tavern.vox")
print(f"  → {OUT}/tavern.vox  ({building.voxel_count()} voxels)")

# --- Character ---
print("Generating character…")
hero = CharacterGenerator(palette, seed=1).generate(
    class_type="warrior", skin_tone="tan", hair_color="brown",
    armour="plate", weapon="sword", name="hero"
)
hero.save(f"{OUT}/hero.vox")
print(f"  → {OUT}/hero.vox  ({hero.voxel_count()} voxels)")

# --- Props ---
print("Generating props…")
gen = PropGenerator(palette, seed=99)
for ptype in ["tree", "barrel", "chest", "mushroom"]:
    prop = gen.generate(ptype, name=ptype)
    prop.save(f"{OUT}/{ptype}.vox")
    print(f"  → {OUT}/{ptype}.vox  ({prop.voxel_count()} voxels)")

print("\nAll assets generated in:", OUT)
print("You can load these .vox files into MagicaVoxel or the VoxelForge engine.")
