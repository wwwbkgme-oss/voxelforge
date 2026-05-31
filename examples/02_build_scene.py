"""
Example 02 — Build a complete scene from generated assets
==========================================================
Generates assets and wires them into a scene JSON file that
the VoxelForge engine can load directly.

Run:
    python examples/02_build_scene.py
    # Then in the engine directory:
    # ./voxelforge --scene ../examples/output/village.scene
"""

import os
from forge.voxel import Palette
from forge.generators import (
    TerrainGenerator, BuildingGenerator, CharacterGenerator, PropGenerator
)
from forge.scene import Scene

OUT = "examples/output"
os.makedirs(OUT, exist_ok=True)

palette = Palette.natural()
scene   = Scene(
    background_color = (0.05, 0.15, 0.30),
    sun_color        = (0.93, 0.92, 0.92),
    sun_direction    = (0.46, 0.13, -0.98),
)

# --- Terrain ---
terrain = TerrainGenerator(palette, seed=10).generate(
    width=48, height=48, max_depth=14, biome="grassland"
)
terrain.save(f"{OUT}/village_terrain.vox")
scene.add_voxel_model(
    "terrain", f"{OUT}/village_terrain.vox",
    position=(0, 0, 0), is_static=True,
)

surface_z = 14.0

# --- Three buildings ---
bgen = BuildingGenerator(palette, seed=20)
buildings_data = [
    ("inn",       8,  8, 4, "medieval",  (5,  5,  surface_z)),
    ("blacksmith",6,  6, 2, "rustic",    (20, 5,  surface_z)),
    ("tower",     6,  6, 6, "medieval",  (5,  20, surface_z)),
]
for name, w, d, floors, style, pos in buildings_data:
    model = bgen.generate(w, d, floors, style=style, name=name)
    path  = f"{OUT}/{name}.vox"
    model.save(path)
    scene.add_voxel_model(name, path, position=pos, is_static=True)

# --- Two characters ---
cgen = CharacterGenerator(palette, seed=30)
for i, (cls, pos) in enumerate([
    ("warrior", (12, 12, surface_z)),
    ("mage",    (15, 12, surface_z)),
]):
    char_name = f"char_{cls}_{i}"
    model = cgen.generate(class_type=cls, name=char_name)
    path  = f"{OUT}/{char_name}.vox"
    model.save(path)
    scene.add_voxel_model(char_name, path, position=pos, is_static=False,
                           add_rigidbody=True)

# --- Props scattered around ---
pgen = PropGenerator(palette, seed=40)
prop_placements = [
    ("tree",     "oak",  (30, 10, surface_z)),
    ("tree",     "pine", (32, 10, surface_z)),
    ("barrel",   "",     (12, 8,  surface_z)),
    ("chest",    "",     (14, 8,  surface_z)),
    ("mushroom", "",     (35, 35, surface_z)),
    ("rock",     "",     (8,  35, surface_z)),
    ("lamp_post","",     (10, 15, surface_z)),
]
for ptype, variant, pos in prop_placements:
    prop_name = f"prop_{ptype}_{pos[0]}_{pos[1]}"
    model = pgen.generate(ptype, variant=variant, name=prop_name)
    path  = f"{OUT}/{prop_name}.vox"
    model.save(path)
    scene.add_voxel_model(prop_name, path, position=pos, is_static=True)

# --- Ambient light (top-level entity) ---
scene.add_point_light(
    "sun",
    position  = (24.0, 24.0, 50.0),
    color     = (1.0, 0.95, 0.85),
    intensity = 2.0,
    range_    = 200.0,
)
scene.add_point_light(
    "lamp",
    position  = (10.0, 15.0, surface_z + 10),
    color     = (1.0, 0.8, 0.4),
    intensity = 0.8,
    range_    = 20.0,
)

# --- Save scene ---
scene_path = f"{OUT}/village.scene"
scene.save(scene_path)

print(f"Scene saved → {scene_path}")
print(f"Entities:    {scene.entity_count}")
print()
print("To play the scene in the VoxelForge engine:")
print(f"  cd engine && ./voxelforge --scene ../{scene_path}")
print()
print("To take a headless screenshot:")
print(f"  cd engine && ./voxelforge --headless --screenshot ../examples/output/village_preview "
      f"--scene ../{scene_path}")
