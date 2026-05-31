# VoxelForge

**AI-Powered Voxel World & Game Builder**

[![CI](https://github.com/wwwbkgme-oss/voxelforge/actions/workflows/ci.yml/badge.svg)](https://github.com/wwwbkgme-oss/voxelforge/actions)

VoxelForge lets an AI autonomously create complete, playable game worlds and mini-games — terrain, dungeons, buildings, characters, enemies with AI scripts, props, and fully assembled scene files — entirely without human intervention.

Built on top of the [Vopix Engine](https://github.com/KellerMartins/PixelVoxels) (a C ECS voxel engine that renders MagicaVoxel `.vox` files as isometric pixel art), VoxelForge adds:

- **Headless engine mode** — run without a display (`--headless`, `--screenshot`)
- **Python `forge/` package** — pure-Python voxel data model + `.vox` binary read/write
- **6 procedural generators** — terrain (biomes), buildings (5 styles), characters (4 classes), props (7 types), dungeons (BSP, 4 styles), **complete mini-games**
- **FastAPI REST server** — all operations over HTTP, auto-documented at `/docs`
- **Web dashboard** — visual UI at `/ui` for one-click world/game generation
- **OpenAI function-calling tools** — 10 tools, every endpoint callable by any LLM
- **Autonomous agent** — give it a text prompt, it builds the whole game unattended
- **29-test suite** — fully validated, runs in CI on Python 3.10/3.11/3.12

---

## Quick Start

### 1. Install

```bash
pip install -e ".[ai]"
```

### 2. Start the API server + web dashboard

```bash
voxelforge api
# API:       http://localhost:8080
# Dashboard: http://localhost:8080/ui
# API docs:  http://localhost:8080/docs
```

### 3. Generate a complete game from one API call

```bash
curl -X POST http://localhost:8080/game/generate \
  -H "Content-Type: application/json" \
  -d '{"title": "Crystal Dungeon", "genre": "dungeon", "player_class": "mage", "enemies": 3}'
```

### 4. Build a world (terrain + buildings + characters + props + scene)

```bash
curl -X POST http://localhost:8080/world/build \
  -H "Content-Type: application/json" \
  -d '{"name": "my_village", "biome": "grassland", "buildings": 4, "building_style": "medieval"}'
```

### 5. Autonomous AI agent

```bash
# No API key needed (direct keyword mode):
voxelforge agent --direct "a haunted forest dungeon with ice caves and a rogue hero"

# LLM mode (GPT-4o):
export OPENAI_API_KEY=sk-...
voxelforge agent "a medieval village with a blacksmith, archer NPCs, and oak trees"
```

### 6. Play in the engine

```bash
cd engine && make
./voxelforge --scene ../generated_assets/games/crystal_dungeon/scenes/crystal_dungeon.scene
# Player: WASD = move, Space = jump, E = open chests
```

---

## Architecture

```
voxelforge/
├── engine/                  # C game engine (VoxelForge, rebranded from Vopix)
│   ├── Engine/              # ECS: rendering, physics, input
│   ├── Assets/              # Shaders, default scene, example .vox models
│   ├── Assets/Game/Scripts/templates/
│   │   ├── game_controller.lua   # Player movement + HUD template
│   │   └── world_populator.lua   # Runtime entity spawner template
│   └── Makefile             # Build: make → ./voxelforge binary
│
├── forge/                   # Python automation layer
│   ├── voxel.py             # VoxelModel + Palette: .vox binary I/O
│   ├── scene.py             # Scene builder → JSON scene files (engine-compatible)
│   ├── generators/
│   │   ├── terrain.py       # FBM noise terrain (5 biomes)
│   │   ├── buildings.py     # Multi-floor buildings (5 styles)
│   │   ├── characters.py    # Humanoid characters (4 classes)
│   │   ├── props.py         # 7 prop types
│   │   ├── dungeon.py       # BSP dungeon/cave (4 styles)
│   │   └── game.py          # Complete mini-game generator ← KEY FEATURE
│   ├── export/
│   │   └── sprite_renderer.py  # Software isometric renderer → PNG (no engine needed)
│   ├── api/
│   │   ├── server.py        # FastAPI REST server
│   │   ├── models.py        # Pydantic request/response schemas
│   │   └── static/index.html  # Web dashboard (zero dependencies)
│   └── ai/
│       ├── tools.py         # 10 OpenAI function-calling tool definitions
│       └── agent.py         # Autonomous game-creation agent
│
├── cli/main.py              # voxelforge CLI
├── tests/test_voxel.py      # 29 pytest tests
├── examples/                # 5 runnable examples
├── docker/                  # Docker + docker-compose
└── .github/workflows/ci.yml # CI (Python 3.10/3.11/3.12)
```

---

## REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/game/generate` | **Complete mini-game** (level + player + enemies + Lua scripts + scene) |
| `POST` | `/world/build` | Complete world (terrain + buildings + characters + props + scene) |
| `POST` | `/asset/terrain` | Terrain (5 biomes, FBM noise) |
| `POST` | `/asset/building` | Building (5 styles, configurable floors) |
| `POST` | `/asset/character` | Humanoid character (4 classes) |
| `POST` | `/asset/prop` | Prop (7 types: tree/crate/barrel/lamp/rock/chest/mushroom) |
| `POST` | `/asset/dungeon` | BSP dungeon/cave level (4 styles) |
| `GET`  | `/assets` | List all generated .vox assets |
| `POST` | `/scene/build` | Build a scene from entity placements |
| `GET`  | `/scenes` | List all generated scenes |
| `POST` | `/agent/run` | Run AI agent with a text prompt |
| `GET`  | `/asset/download?path=…` | Download a .vox or scene file |

Full interactive docs: **http://localhost:8080/docs**

Web dashboard: **http://localhost:8080/ui**

---

## Complete Game Generator

The `GameGenerator` and `/game/generate` endpoint produce a fully playable mini-game:

```python
from forge.generators.game import GameGenerator
from forge.voxel import Palette

gen = GameGenerator(Palette.natural(), seed=42, output_dir="games")
manifest = gen.generate(
    title        = "Crystal Ice Dungeon",
    genre        = "dungeon",     # village | dungeon | space | fantasy | horror | arctic
    theme        = "ice",
    player_class = "mage",        # warrior | mage | archer | rogue
    enemies      = 3,
    props        = 6,
    level_size   = 48,
)
print(manifest["run_command"])
# → cd engine && ./voxelforge --scene ../games/games/crystal_ice_dungeon/...
```

**What's generated (in < 0.5s):**
- `level.vox` — BSP dungeon or terrain depending on genre
- `player.vox` — class-matched character with armour + weapon
- `enemy_N.vox` × N — enemies appropriate for the genre
- `prop_N.vox` × N — props including chest collectibles
- `player.lua` — WASD movement, jump, camera follow, HUD
- `enemy_N.lua` × N — patrol / chase / attack AI per enemy
- `objective.lua` — collect all chests to win
- `<title>.scene` — everything wired together, directly loadable
- `manifest.json` — full asset + script index

---

## AI Tool Definitions (10 tools)

```python
from forge.ai.tools import TOOLS, call_tool

# Pass TOOLS to any OpenAI-compatible API:
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Build me a horror dungeon game with 4 enemies"}],
    tools=TOOLS,
)
# Execute tool calls:
for tc in response.choices[0].message.tool_calls:
    result = call_tool(tc.function.name, tc.function.arguments)
```

Available tools: `generate_terrain`, `generate_building`, `generate_character`,
`generate_prop`, `generate_dungeon`, `generate_game`, `build_scene`, `build_world`,
`list_assets`, `list_scenes`.

All tools fall back to direct Python execution when the API server is not running.

---

## Headless Engine

```bash
# Build (Linux/macOS — requires SDL2, GLEW, Lua5.3):
cd engine && make

# Headless screenshot:
./voxelforge --headless --screenshot /tmp/preview.png \
             --scene ../generated_assets/.../my_game.scene

# Headless run (one frame, no display):
./voxelforge --headless --scene ../generated_assets/.../my_game.scene
```

### Build dependencies (Ubuntu/Debian)

```bash
sudo apt-get install -y \
    libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev \
    libglew-dev liblua5.3-dev
cd engine && make
```

---

## Docker

```bash
docker compose -f docker/docker-compose.yml up -d
# API at http://localhost:8080
# Dashboard at http://localhost:8080/ui
# Assets persisted in ./docker/output/
```

---

## Sprite Renderer (no engine needed)

```python
from forge.export.sprite_renderer import render_vox_to_png

# Render any .vox to an isometric PNG sprite
render_vox_to_png("engine/Assets/Game/Models/char.vox", "char_preview.png")

# Generate thumbnails for all assets
from forge.export.sprite_renderer import render_all_assets
count = render_all_assets("generated_assets", "thumbnails")
```

Requires `pip install Pillow`. No OpenGL or C engine needed.

---

## Examples

| Script | Description |
|--------|-------------|
| `examples/01_generate_assets.py` | Terrain, building, character, props — directly from Python |
| `examples/02_build_scene.py` | Full scene with 15 entities, lights, correct engine format |
| `examples/03_ai_agent.py` | Autonomous agent with text prompt (direct or LLM mode) |
| `examples/04_openai_function_calling.py` | GPT-4o tool-calling loop |
| `examples/05_generate_full_game.py` | 3 complete mini-games in one script |

---

## Tests

```bash
pytest tests/ -v   # 29 tests covering voxel I/O, generators, scene format
```

Key test: `test_scene_format_matches_engine` verifies the JSON structure precisely
against what `EngineScene.c` / `EngineECS.c` parse.

---

## License

MIT — original Vopix engine by [KellerMartins](https://github.com/KellerMartins/PixelVoxels).
VoxelForge additions released under the same licence.
