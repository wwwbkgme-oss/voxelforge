# Art Director Agent

**Role**: Visual identity, voxel aesthetics, palette curation, and asset design direction for VoxelForge.

## Palette Philosophy

VoxelForge uses a 256-colour isometric pixel-art aesthetic.
The `Palette.natural()` provides biome-appropriate colours:

| Index Range | Colour Group | Use |
|------------|-------------|-----|
| 1–20       | Greens      | Foliage, grass, forest |
| 21–40      | Browns      | Wood, soil, bark |
| 41–60      | Greys       | Stone, metal, concrete |
| 61–80      | Blues       | Water, sky, ice |
| 81–100     | Reds/warm   | Brick, flesh, fire |
| 101–120    | Yellows     | Sand, gold, light |
| 121–130    | Whites      | Snow, clouds, marble |

## Per-Genre Visual Identity

| Genre | Primary Palette | Secondary | Atmosphere |
|-------|----------------|-----------|-----------|
| village | greens 1-20 + browns 21-30 | yellows 101-110 | warm, welcoming |
| dungeon | greys 41-55 + blacks | blues 61-65 | cold, oppressive |
| space | greys 41-50 + blues 61-70 | yellows (lights) | alien, vast |
| fantasy | blues 61-79 + reds 81-95 | whites 121+ | magical, vibrant |
| horror | dark browns + blacks | pale 41-44 | desaturated, eerie |
| arctic | whites 121-130 + blues 61-70 | greys 41-55 | stark, frozen |

## Building Style Visual Guide

- **modern**: clean grey panels, full windows, flat roof
- **medieval**: warm brick (81–95), narrow windows, peaked roof
- **sci-fi**: metallic panels (41–50), glowing windows (65), flat
- **rustic**: wood browns (21–35), earthy windows (62), pyramid roof
- **fantasy**: blue-purple walls (61–79), bright windows (121), peaked

## Sprite Rendering Settings

```python
# For thumbnails (fast, crisp pixel art):
VoxelSpriteRenderer(tile_w=8, tile_h=4, padding=4)

# For hero shots (larger, more detail):
VoxelSpriteRenderer(tile_w=12, tile_h=6, padding=8)

# For icons (tiny, embedded in UI):
VoxelSpriteRenderer(tile_w=4, tile_h=2, padding=2)
```

## Asset Naming Convention

```
<category>_<descriptor>_<variant>.vox
Examples:
  terrain_grassland_v01.vox
  building_medieval_tavern.vox
  char_warrior_heavy.vox
  prop_tree_oak.vox
  dungeon_ice_level01.vox
```
