# /generate — Generate VoxelForge Assets

**Usage**: `/generate <type> [options]`

**Description**: Generate voxel assets directly from a skill command.

## Commands

```bash
# Terrain
/generate terrain biome=grassland width=48 height=48
/generate terrain biome=dungeon style=ice

# Building
/generate building style=medieval floors=5 name=castle_tower

# Character
/generate character class=mage armour=plate weapon=staff

# Prop
/generate prop type=tree variant=pine

# Dungeon
/generate dungeon style=ice width=64 height=64 wall_height=4

# Complete game
/generate game title="Ice Dungeon" genre=dungeon player=mage enemies=4
```

## Equivalent Python

```python
from forge.voxel import Palette
from forge.generators import (
    TerrainGenerator, BuildingGenerator, CharacterGenerator,
    PropGenerator, DungeonGenerator
)
from forge.generators.game import GameGenerator

pal = Palette.natural()

# Terrain
terrain = TerrainGenerator(pal, seed=42).generate(
    width=48, height=48, max_depth=14, biome="grassland")
terrain.save("output/terrain.vox")

# Game
gen = GameGenerator(pal, seed=42, output_dir="output")
manifest = gen.generate(title="My Game", genre="dungeon",
                         player_class="mage", enemies=4)
print(manifest["run_command"])
```

## Sprite Preview

After generating, render a preview:
```python
from forge.export.sprite_renderer import render_vox_to_png
render_vox_to_png("output/terrain.vox", "output/terrain_preview.png")
```
