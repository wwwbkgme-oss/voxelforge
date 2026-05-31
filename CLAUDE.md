# VoxelForge — Claude Code Game Studios Configuration

VoxelForge is an **AI-powered voxel world and game builder** built on the Vopix C engine.
Claude Code acts as a multi-role game development studio for this project.

## Project Overview

```
voxelforge/
├── engine/          # C ECS voxel engine (SDL2 + OpenGL + Lua5.3)
├── forge/           # Python automation layer
│   ├── voxel.py     # VoxelModel, Palette, .vox I/O
│   ├── scene.py     # Scene builder (exact engine JSON format)
│   ├── generators/  # terrain, buildings, characters, props, dungeon, game
│   ├── api/         # FastAPI REST server + web dashboard
│   └── ai/          # 10 OpenAI-compatible tools + autonomous agent
├── tests/           # 29 pytest tests
├── design/          # GDDs, ADRs, sprint plans
└── docs/demo/       # Generated asset sprites
```

## Available Agents

Load an agent with: `/agent <name>`

| Agent | Role |
|-------|------|
| `creative-director` | Game vision, narrative, high-level design |
| `game-designer`     | GDD, MDA framework, level/system design |
| `voxelforge-dev`    | Python forge code, API endpoints, tools |
| `level-designer`    | World layout, dungeon construction, scene assembly |
| `art-director`      | Voxel aesthetics, palette, visual consistency |
| `qa-lead`           | Test plans, smoke checks, regression suites |

## Available Skills (Slash Commands)

```
/gdd           Generate a Game Design Document
/brainstorm    Creative brainstorming session (MDA-guided)
/mda           Analyze a game using Mechanics-Dynamics-Aesthetics framework
/design-system Design a game system using player motivation theory
/sprint        Generate a sprint plan for a feature set
/adr           Create an Architecture Decision Record
/generate      Generate voxel assets (terrain/building/character/prop/dungeon/game)
/qa-plan       Generate a QA test plan
/smoke-check   Run smoke tests on the Python forge package
/patch-notes   Generate changelog / patch notes
/lore          Generate narrative lore for a game world
/balance       Analyze and suggest game balance improvements
```

## Technology Stack

- **Engine**: C, SDL2, OpenGL 3.2, Lua 5.3, GLEW
- **Automation**: Python 3.10+, FastAPI, Pydantic v2, NumPy
- **Testing**: pytest (29 tests), GitHub Actions CI
- **AI Integration**: OpenAI function-calling (10 tools), autonomous agent
- **Rendering**: Software isometric sprite renderer (Pillow)

## Scene Format

Scenes are JSON files that the engine loads via `EngineScene.c / EngineECS.c`:

```json
{
  "data":     { "backgroundColor": [r,g,b], "sunColor": [r,g,b], "sunDirection": [x,y,z] },
  "entities": [
    { "Transform": {"position":[x,y,z], "rotation":[x,y,z]},
      "VoxelModel": {"modelPath":"...", "modelName":"...", "smallScale":false, "center":[x,y,z]},
      "RigidBody": {"mass":1, "bounciness":0.2, "velocity":[0,0,0], "acceleration":[0,0,0], "useGravity":true, "isStatic":true},
      "childs": [ { "Transform":..., "PointLight":{"color":[r,g,b],"intensity":1,"range":100,"hueShift":0} } ]
    }
  ]
}
```

## Quick Commands

```bash
# Run tests
pytest tests/ -v

# Start API + dashboard
voxelforge api

# Generate a complete game (no server needed)
python3 -c "
from forge.generators.game import GameGenerator
from forge.voxel import Palette
m = GameGenerator(Palette.natural(), seed=42).generate(
    title='My Game', genre='dungeon', player_class='warrior')
print(m['run_command'])
"

# Render asset preview sprites
python3 -c "
from forge.export.sprite_renderer import render_vox_to_png
render_vox_to_png('engine/Assets/Game/Models/char.vox', 'preview.png')
"
```

## Design Principles

Following **Claude Code Game Studios** methodology:

1. **MDA Framework** — design through Mechanics → Dynamics → Aesthetics
2. **Player Motivation** — Self-Determination Theory (autonomy, mastery, relatedness)
3. **Flow State Design** — balance challenge vs. skill for optimal engagement
4. **Bartle Player Types** — Achievers, Explorers, Socializers, Killers
5. **Iterative ADRs** — document every significant design/architecture decision

## Coding Standards

- Python: pyright type-checking, black formatting, ruff linting
- Scene JSON: must pass `test_scene_format_matches_engine` test
- All new generators must include at least one pytest test
- .vox files: always use `Palette.natural()` unless custom palette needed
- Commit format: `type: description (Co-Authored-By: ey sho <eysho.it@gmail.com>)`
