# Game Design Document: Crystal Ice Dungeon

**Version**: 1.0
**Date**: 2025-05-31
**Genre**: Dungeon Crawler
**Studio**: VoxelForge AI Game Studios

---

## 1. Executive Summary

Crystal Ice Dungeon is a single-player isometric voxel dungeon crawler where a lone **mage** explores a treacherous ice dungeon, defeating stone guardians and collecting frozen crystals to unseal the exit portal.

---

## 2. Target Audience

- **Primary Player Type**: Achiever + Explorer (Bartle)
- **Age Range**: 10+
- **Experience Level**: Casual to mid-core
- **Play Session**: 10–30 minutes

---

## 3. Core Loops

### 30-Second Loop
Move → Spot enemy → Decide: fight or route around → Spot chest → Collect

### 5-Minute Loop
Clear a dungeon section → Collect all chests → Advance to next room

### 30-Minute Loop
Progress through 3 dungeon levels of increasing enemy density

---

## 4. MDA Framework

### Mechanics
- WASD movement, Space jump
- E to collect chests (range 3 units)
- Enemies aggro at 15 units, chase at 6 speed, attack at 2.5 units
- Player HP: 100, Enemy HP: 30

### Dynamics
- Players path around enemy patrol zones to reach chests
- Multiple enemies can aggro simultaneously — crowd management emerges
- Chests behind enemy clusters create risk/reward decisions
- Fast players can sprint through aggro zones

### Aesthetics
- **Challenge**: Primary — overcoming enemies and navigating the dungeon
- **Discovery**: Strong — hidden chests and room exploration
- **Sensation**: Background — isometric ice voxel art, pixel crunch aesthetic

---

## 5. Level Design

| Level | Size | Enemies | Chests | Objective |
|-------|------|---------|--------|-----------|
| L1: Entry Chambers | 20×20 | 1 | 1 | Tutorial — one enemy, one chest |
| L2: Frozen Halls | 32×32 | 3 | 2 | Navigate patrolling guardians |
| L3: Crystal Vault | 48×48 | 5 | 3 | Final challenge, dense enemies |

---

## 6. Asset List

Generated with:
```python
from forge.generators.game import GameGenerator
from forge.voxel import Palette

gen = GameGenerator(Palette.natural(), seed=42, output_dir="output")
manifest = gen.generate(
    title        = "Crystal Ice Dungeon",
    genre        = "dungeon",
    theme        = "ice",
    player_class = "mage",
    enemies      = 3,
    props        = 5,
    level_size   = 32,
)
```

Assets produced:
- `level.vox` — BSP ice dungeon
- `player.vox` — mage with plate armour and staff
- `enemy_0.vox`, `enemy_1.vox`, `enemy_2.vox` — warrior guardians
- `prop_crate_0.vox` through `prop_crate_2.vox` — icy crates
- `prop_chest_3.vox`, `prop_chest_4.vox` — collectible chests
- `player.lua`, `enemy_0.lua`, `enemy_1.lua`, `enemy_2.lua`, `objective.lua`
- `crystal_ice_dungeon.scene`

---

## 7. Win / Loss Conditions

- **Win**: All chests collected (`opened_chests >= total_chests`)
- **Loss**: `health <= 0`
- **Retry**: Reload the same scene file

---

## 8. Technical Scope

Engine: VoxelForge C engine (SDL2 + OpenGL + Lua5.3)
Tools: Python forge package (all generators)
Run command output by `manifest["run_command"]`
