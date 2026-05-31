"""
Example 05 — Generate a complete, playable mini-game
=====================================================
The most powerful feature of VoxelForge: one call generates an entire
playable game with terrain/dungeon, player character, enemies with AI,
props, chest collectibles, and Lua game scripts — all wired into a
VoxelForge scene file.

No API server needed — this example uses the generators directly.

Run:
    python examples/05_generate_full_game.py

Then load the generated game in the engine:
    cd engine && make && ./voxelforge --scene ../<scene_path>
"""

import os
import json
from forge.voxel import Palette
from forge.generators.game import GameGenerator

palette = GameGenerator(Palette.natural(), seed=0, output_dir="examples/output")
# (Instantiation just to show it; we use it below)

GAMES = [
    {
        "title":        "Crystal Ice Dungeon",
        "genre":        "dungeon",
        "theme":        "ice",
        "player_class": "mage",
        "enemies":      3,
        "props":        5,
        "level_size":   32,
        "seed":         42,
    },
    {
        "title":        "Forest Village Adventure",
        "genre":        "village",
        "player_class": "warrior",
        "enemies":      2,
        "props":        6,
        "level_size":   40,
        "seed":         7,
    },
    {
        "title":        "Space Station Siege",
        "genre":        "space",
        "player_class": "archer",
        "enemies":      4,
        "props":        4,
        "level_size":   36,
        "seed":         99,
    },
]

for cfg in GAMES:
    cfg_copy = {k: v for k, v in cfg.items() if k != "seed"}
    gen = GameGenerator(Palette.natural(), seed=cfg.get("seed", 0),
                         output_dir="examples/output")
    print(f"\n=== Generating: {cfg['title']} ===")
    manifest = gen.generate(**cfg_copy)

    print(f"  Genre:    {manifest['genre']}")
    print(f"  Assets:   {len(manifest['assets'])}")
    print(f"  Scripts:  {len(manifest['scripts'])}")
    print(f"  Entities: {manifest['entity_count']}")
    print(f"  Scene:    {manifest['scene_path']}")
    print(f"  Run:      {manifest['run_command']}")

print("\n--- All games generated ---")
print("Each game is directly playable with the VoxelForge engine.")
print("Player controls: WASD to move, Space to jump, E to open chests.")
