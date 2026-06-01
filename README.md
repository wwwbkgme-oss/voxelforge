# VoxelForge Studio

**The Complete AI-Powered Voxel Game Development Platform**

[![CI](https://github.com/wwwbkgme-oss/voxelforge/actions/workflows/ci.yml/badge.svg)](https://github.com/wwwbkgme-oss/voxelforge/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

![VoxelForge Demo Banner](docs/demo/banner.png)

VoxelForge Studio is a complete AI game development platform that goes from a text prompt all the way to a running voxel game — with zero cloud API keys required.  It ships two engines, a full Python automation layer, a REST API, a web dashboard, an MCP server for Claude Code, and a local LLM inference stack backed by llama.cpp.

---

## What's Inside

| Layer | Description |
|-------|-------------|
| **VoxelForge Engine (VFE)** | New original C99 engine — ECS, greedy mesh, shadow map renderer, Lua 5.4, Python IPC |
| **Legacy C Engine** | Rebranded Vopix: headless mode, `--screenshot`, SDL2+OpenGL+Lua 5.3 |
| **Procedural Generators** | Terrain (5 biomes), buildings (5 styles), characters (4 classes), 7 props, BSP dungeons, complete games |
| **AI Sprite Generator** | Text → sprite via OpenRouter/DALL-E; animated spritesheets; chroma-key BG removal |
| **Sprite Sheet Forge** | 11 game-art styles × 12 animation actions; grid batch generation (25 imgs/call) |
| **HTML5 Game Generator** | Text → complete single-file playable HTML5 game via free LLMs |
| **Narrative Engine** | Dual-model LLM RPG: story + mechanics plugins (combat/inventory/social); SQLite state |
| **12-Agent Pipeline** | Market → GDD → Build → QA; Go/No-Go before writing a line of code |
| **Asset Pipeline** | Storyline → NPCs → quests → dialogue trees → items → Lua scripts |
| **Project Manager** | Full lifecycle with engine-specific layouts: VoxelForge / Godot / Unity / Unreal |
| **Free LLM Router** | 10+ providers: Groq, Cerebras, NVIDIA NIM, Gemini free, OpenRouter free, Ollama, local |
| **Local GGUF Inference** | Download & run 12 free models offline via llama.cpp (CPU or GPU) |
| **REST API** | FastAPI with 40+ endpoints; auto-documented at `/docs` |
| **Web Dashboard** | Zero-dependency single-page UI at `/ui` with model browser, live inference chat |
| **MCP Server** | 22 tools for Claude Code, Cline, OpenCode, Cursor — `voxelforge mcp` |
| **Claude Code Studio** | CLAUDE.md + 6 agents + 9 slash commands + 5 ADRs + GDD templates |
| **29 Tests** | Full pytest suite; CI on Python 3.10/3.11/3.12 |

---

## Quick Start

### Option A — Cloud API keys (fastest, best quality)

```bash
pip install -e ".[ai]"
export OPENROUTER_API_KEY=sk-or-v1-...   # or GROQ_API_KEY, GEMINI_API_KEY, etc.
voxelforge api                            # http://localhost:8080/ui
```

### Option B — Fully local / offline (no API keys needed)

```bash
pip install -e ".[ai]"

# Build llama.cpp once (takes ~5 min)
voxelforge inference install

# Download a free model (~2 GB, runs on any CPU)
voxelforge model download llama3.2-3b

# Start the local inference server
voxelforge serve --model llama3.2-3b

# Everything now uses the local model automatically
voxelforge api
```

### Option C — Full Docker stack (API + inference server)

```bash
# Download a model first
voxelforge model download llama3.2-3b

# Start everything
docker compose -f docker/docker-compose.full.yml up -d
# API:       http://localhost:8080
# Dashboard: http://localhost:8080/ui
# Inference: http://localhost:8090/v1

# GPU (NVIDIA):
VFE_GPU_LAYERS=35 docker compose -f docker/docker-compose.full.yml --profile gpu up -d
```

---

## Repository Structure

```
voxelforge/
│
├── engine_vfe/                  # VoxelForge Engine — new original C99 engine
│   ├── src/
│   │   ├── core/                # ECS, window (SDL2+OpenGL), input, timer, log
│   │   ├── voxel/               # VoxelGrid, .vox loader, greedy mesher
│   │   ├── renderer/            # Shader, camera, render pipeline (shadow+geo+post)
│   │   ├── physics/             # AABB collision, ray-cast, dynamics
│   │   ├── scripting/           # Lua 5.4 VM + engine API bindings
│   │   ├── scene/               # JSON scene load/save (Python-compatible format)
│   │   ├── audio/               # SDL_mixer wrapper
│   │   ├── ipc/                 # JSON-RPC over stdin or Unix socket
│   │   └── main.c               # CLI: --headless --screenshot --scene --ipc-stdin
│   ├── CMakeLists.txt           # CMake 3.18+; FetchContent for cJSON; CUDA/Metal opt-in
│   └── Makefile                 # pkg-config fallback; auto-fetches cJSON
│
├── engine/                      # Legacy C engine (VoxelForge 1.x / Vopix rebranded)
│
├── forge/                       # Python platform layer
│   ├── voxel.py                 # VoxelModel, Palette — full .vox binary I/O
│   ├── scene.py                 # Scene builder (C-engine-compatible JSON)
│   ├── imagegen.py              # AI sprite + animated spritesheet generation
│   ├── spritesheet.py           # 11 styles × 12 actions; grid batch; rembg BG removal
│   ├── gamegen.py               # HTML5GameGenerator + AssetPipeline (quests/NPCs/dialogue)
│   ├── narrative.py             # LLM dual-model narrative engine + SQLite
│   ├── pipeline.py              # 12-agent game dev pipeline
│   ├── project.py               # Project lifecycle manager
│   ├── studio.py                # GDD, brainstorm, MDA, ADR, lore generators
│   ├── llm_router.py            # Free LLM router (10 providers, auto-fallback)
│   ├── local_llm.py             # GGUF model downloader + llama.cpp server manager
│   ├── mcp_server.py            # MCP JSON-RPC server (stdio + SSE)
│   ├── generators/              # terrain, buildings, characters, props, dungeon, game
│   ├── export/sprite_renderer.py  # Software isometric renderer → PNG
│   └── api/
│       ├── server.py            # FastAPI 40+ endpoints
│       ├── models.py            # Pydantic schemas
│       └── static/index.html   # Web dashboard (single file, zero dependencies)
│
├── cli/main.py                  # 25+ CLI commands
├── tests/test_voxel.py          # 29 pytest tests
├── examples/                    # 5 runnable examples
├── design/                      # 5 ADRs + GDD + sprint plan
├── docs/demo/                   # 31 AI-generated sprite demos + banner
├── .claude/                     # 6 agents, 9 skills, hooks, rules, templates
├── .mcp.json                    # Claude Code / Cline MCP config
├── .opencode.json               # OpenCode tool config
├── docker/
│   ├── Dockerfile               # API server image
│   ├── Dockerfile.inference     # llama.cpp inference image (CPU; --build-arg CUDA=1 for GPU)
│   ├── docker-compose.yml       # API only
│   └── docker-compose.full.yml  # API + inference + GPU profile
└── requirements.txt
```

---

## VoxelForge Engine (VFE) — Original C99 Engine

The `engine_vfe/` directory contains a **completely new voxel game engine** written from scratch:

### Build

```bash
# Dependencies (Ubuntu/Debian)
sudo apt-get install -y cmake build-essential \
    libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev libsdl2-mixer-dev \
    libglew-dev liblua5.4-dev pkg-config

cd engine_vfe
cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j$(nproc)
# Binary: build/bin/voxelforge

# Or use the Makefile fallback (auto-downloads cJSON):
make
```

### CLI flags

```bash
# Run a scene
./voxelforge --scene path/to/scene.scene

# Headless screenshot
./voxelforge --headless --screenshot /tmp/preview.png --scene my.scene

# Python automation via stdin IPC
./voxelforge --headless --ipc-stdin --scene my.scene

# Camera modes
./voxelforge --cam isometric    # default
./voxelforge --cam topdown
./voxelforge --cam perspective
```

### Python automation via IPC

```python
import subprocess, json

proc = subprocess.Popen(
    ["engine_vfe/build/bin/voxelforge", "--headless", "--ipc-stdin"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
)

def cmd(c, **args):
    proc.stdin.write(json.dumps({"cmd": c, "args": args}) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())

cmd("load_scene", path="generated_assets/scenes/my_world.scene")
cmd("screenshot", path="/tmp/frame.png")
cmd("exit")
```

### Engine features

| Subsystem | Implementation |
|-----------|---------------|
| **ECS** | Data-oriented SoA, 4096 entities, 32 component types, mask queries, parent-child hierarchy |
| **Voxel mesher** | Greedy mesh algorithm — coplanar same-colour faces merged into quads |
| **Renderer** | Shadow pass (PCF 3×3) → sky → geometry (Phong + AO) → post-process (chromatic aberration, vignette, Reinhard) |
| **Camera** | Isometric / top-down / perspective with correct orthographic + perspective projection |
| **Physics** | AABB dynamics, gravity, restitution, friction, sphere broad-phase query |
| **Lua 5.4** | Transform / RigidBody / Entity / Light / Log APIs; hot-reload; `DeltaTime` global |
| **Scene** | Loads/saves the same JSON format as the Python `forge.scene` module |
| **IPC** | JSON-RPC over stdin/stdout or Unix socket — spawn, set_pos, load_scene, screenshot, exec_lua |

---

## Local GGUF Inference (Offline, No API Key)

### Available models

| ID | Name | Size | RAM | Tags |
|----|------|------|-----|------|
| `smollm2-360m` | SmolLM2 360M | 0.4 GB | 1 GB | tiny, cpu |
| `smollm2-1.7b` | SmolLM2 1.7B | 1.1 GB | 2 GB | small, cpu |
| `llama3.2-1b` | Llama 3.2 1B | 0.8 GB | 2 GB | tiny, cpu |
| **`llama3.2-3b`** ★ | **Llama 3.2 3B** | **2.0 GB** | **4 GB** | **recommended, cpu** |
| `phi3-mini` | Phi-3 Mini 4K | 2.2 GB | 4 GB | small, coding |
| `qwen2.5-3b` | Qwen 2.5 3B | 2.0 GB | 4 GB | small, 32K ctx |
| `gemma2-2b` | Gemma 2 2B | 1.6 GB | 3 GB | small, google |
| `deepseek-r1-1.5b` | DeepSeek R1 1.5B | 1.0 GB | 2.5 GB | reasoning |
| `mistral-7b` | Mistral 7B | 4.4 GB | 8 GB | medium, gpu |
| `llama3.1-8b` | Llama 3.1 8B | 4.9 GB | 10 GB | medium, 128K |
| `qwen2.5-7b` | Qwen 2.5 7B | 4.7 GB | 8 GB | medium, coding |
| `deepseek-r1-7b` | DeepSeek R1 7B | 4.7 GB | 10 GB | reasoning, gpu |

### CLI workflow

```bash
# One-time setup: build llama.cpp (~5 min, auto-detects CUDA/Metal/Vulkan)
voxelforge inference install

# Download the recommended CPU model
voxelforge model download llama3.2-3b

# Start the server (port 8090, OpenAI-compatible API)
voxelforge serve --model llama3.2-3b

# GPU inference (auto-detects available VRAM)
voxelforge serve --model mistral-7b --gpu-layers -1

# List all models
voxelforge model list

# Recommend models for this machine
voxelforge model recommend
```

### Python API

```python
from forge.local_llm import ModelManager, InferenceServer

mgr = ModelManager()
mgr.download("llama3.2-3b")          # ~2 GB, resumes if interrupted

srv = InferenceServer(mgr)
srv.start("llama3.2-3b")             # starts llama-server subprocess

text = srv.chat("Write a dungeon game quest")
print(text)                           # works offline, no API key

srv.stop()
```

---

## All API Endpoints (40+)

### Voxel Assets
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/asset/terrain` | Terrain (5 biomes, FBM noise) |
| `POST` | `/asset/building` | Building (5 styles, 1–20 floors) |
| `POST` | `/asset/character` | Character (4 classes) |
| `POST` | `/asset/prop` | Prop (7 types) |
| `POST` | `/asset/dungeon` | BSP dungeon (4 styles) |
| `GET`  | `/assets` | List generated .vox files |

### Sprites
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sprite/generate` | AI sprite (OpenRouter/DALL-E/procedural) |
| `POST` | `/sprite/sheet` | Character sheet (11 styles × 12 actions) |
| `POST` | `/sprite/batch` | Basic batch sprites |
| `POST` | `/sprite/batch-sheet` | Grid batch (25 images/call, ~30× cheaper) |
| `POST` | `/sprite/remove-bg` | Chroma-key / rembg background removal |

### Scenes & Worlds
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scene/build` | Build scene from entity list |
| `GET`  | `/scenes` | List scene files |
| `POST` | `/world/build` | Complete world (terrain + buildings + chars + props) |

### Games
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/game/generate` | Complete mini-game (level + player + enemies + Lua scripts) |
| `POST` | `/html/generate` | HTML5 game from text prompt via free LLMs |

### Narrative Engine
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/narrative/session` | Start LLM narrative game session |
| `POST` | `/narrative/chat` | Send player message, get structured response |
| `GET`  | `/narrative/sessions` | List active sessions |
| `GET`  | `/narrative/status/{id}` | HP, score, inventory |

### AI Pipelines
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/pipeline/run` | 12-agent pipeline (market → GDD → build → QA) |
| `POST` | `/pipeline/assets` | Narrative asset pipeline (storyline → Lua scripts) |
| `POST` | `/agent/run` | Autonomous AI agent from text prompt |

### Project Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/project/init` | Initialize project with engine structure |
| `GET`  | `/project/list` | List projects |
| `GET`  | `/project/{slug}` | Project status + config |

### LLM & Free Models
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/llm/chat` | Route to best free LLM (10 providers) |
| `GET`  | `/llm/providers` | List providers + which have keys configured |
| `GET`  | `/model/catalog` | 12 GGUF models with download status |
| `GET`  | `/model/downloaded` | Locally available models |
| `POST` | `/model/download` | Download from HuggingFace (resume-capable) |
| `DELETE`| `/model/{id}` | Remove downloaded model |
| `GET`  | `/model/recommend` | Hardware-matched recommendations |
| `POST` | `/inference/start` | Start llama.cpp server with a model |
| `POST` | `/inference/stop` | Stop inference server |
| `GET`  | `/inference/status` | Running/offline + model + port |
| `POST` | `/inference/chat` | Chat local (cloud fallback if offline) |
| `GET`  | `/inference/install-status` | Check llama-server binary + GPU |

**Docs:** http://localhost:8080/docs · **Dashboard:** http://localhost:8080/ui

---

## All CLI Commands (25+)

```bash
# ── Core generation ───────────────────────────────────────────────
voxelforge api                             # start server + dashboard
voxelforge generate terrain/building/character/prop
voxelforge game --title "..." --genre dungeon --player-class mage
voxelforge world --name world --biome grassland

# ── AI sprites ────────────────────────────────────────────────────
voxelforge ai-sprite "pixel art warrior" --name warrior
voxelforge ai-sprite "walk cycle" --animated --frames 8
voxelforge sprite-sheet "ice mage" --style hollow_knight --actions idle,walk,attack
voxelforge sprite --input model.vox --output preview.png    # isometric render
voxelforge sprite --all                                      # render all assets

# ── Local GGUF inference (no API key) ─────────────────────────────
voxelforge inference install               # build llama.cpp (~5 min)
voxelforge inference status                # check GPU + binary
voxelforge model list                      # see all 12 free models
voxelforge model download llama3.2-3b     # recommended: 2 GB, runs on CPU
voxelforge model download mistral-7b      # better quality with GPU
voxelforge model info llama3.2-3b
voxelforge model recommend                # match to your hardware
voxelforge model remove llama3.2-3b
voxelforge serve --model llama3.2-3b      # start OpenAI-compatible server
voxelforge serve --model mistral-7b --gpu-layers -1   # full GPU

# ── Autonomous agent ──────────────────────────────────────────────
voxelforge agent "a medieval village with archer NPCs" --direct

# ── Narrative RPG in terminal ─────────────────────────────────────
voxelforge narrative --player "Hero" --genre dungeon

# ── HTML5 game generation ─────────────────────────────────────────
voxelforge html-game "a platform game with a knight" --genre platformer

# ── Narrative asset pipeline ──────────────────────────────────────
voxelforge asset-pipeline "dark ice dungeon" --genre dungeon

# ── 12-agent development pipeline ────────────────────────────────
voxelforge pipeline "dungeon crawler" --mode design --build
                    --competitors "Spelunky,Rogue Legacy"

# ── Project management ────────────────────────────────────────────
voxelforge project init "My Game" "concept" --engine voxelforge
voxelforge project init "Unity Game" "concept" --engine unity
voxelforge project list
voxelforge project status my-game

# ── Design studio ────────────────────────────────────────────────
voxelforge gdd "My Game" --genre dungeon --preview
voxelforge brainstorm "zombie survival" --preview
voxelforge mda manifest.json
voxelforge adr "use local inference as default LLM"
voxelforge lore "Crystal Keep" --genre dungeon

# ── Free LLM router ───────────────────────────────────────────────
voxelforge llm --providers                             # list all 10 providers
voxelforge llm "Write a dungeon quest" --task creative
voxelforge llm "Write a Lua script" --task code --provider groq

# ── MCP server (Claude Code / Cline / OpenCode / Cursor) ─────────
voxelforge mcp                             # stdio (Claude Code)
voxelforge mcp --transport sse --port 3100 # SSE (Cursor / web clients)
```

---

## Free LLM Providers (no API key needed for many)

| Priority | Provider | Free Tier | Best For |
|----------|----------|-----------|---------|
| 0 | **local** (llama.cpp) | Fully free, offline | Privacy, no limits |
| 1 | **Groq** | Free tier | Fastest cloud (~500 tok/s) |
| 2 | **Cerebras** | Free tier | Ultra-fast (~1800 tok/s) |
| 3 | **SambaNova** | Free, no card | Llama 70B, DeepSeek |
| 4 | **NVIDIA NIM** | 1000 req/month | Llama 4, Qwen 3 |
| 5 | **Gemini** | 1500 req/day free | gemini-2.5-flash |
| 6 | **OpenRouter** | 50+ free models | Variety |
| 7 | **LLM7** | 100 req/hr, no card | GPT-4o-equivalent |
| 8 | **Together AI** | $1 trial | 138 models |
| 9 | **Hugging Face** | Free inference API | Open models |
| 10 | **Ollama** | Local, free | Local models |

Set **any subset** of these keys — the router picks the first available:

```bash
# At least one of these is all you need:
export GROQ_API_KEY=...
export GEMINI_API_KEY=...
export OPENROUTER_API_KEY=...
export LLM7_API_KEY=...

# Or run fully offline:
voxelforge inference install && voxelforge model download llama3.2-3b && voxelforge serve
```

---

## Claude Code / OpenCode Integration (MCP)

```bash
# Start the MCP server
voxelforge mcp

# Or add to Claude Code's config (~/.claude/claude_desktop_config.json):
{
  "mcpServers": {
    "voxelforge": { "command": "voxelforge", "args": ["mcp"] }
  }
}
```

**22 MCP tools:** generate_terrain, generate_building, generate_character, generate_prop, generate_dungeon, generate_game, build_world, generate_sprite, generate_sprite_sheet, generate_batch_sprites, remove_background, generate_html5_game, run_asset_pipeline, generate_storyline, generate_dialogue_tree, run_pipeline, init_project, llm_chat, list_free_providers, list_assets, render_preview, export_spritesheet.

---

## Demo — AI-Generated Assets

All images below are **100% procedurally generated** — no manual art.

### Terrain Biomes
| Grassland | Desert | Snow | Ocean | Forest |
|-----------|--------|------|-------|--------|
| ![](docs/demo/terrain_grassland.png) | ![](docs/demo/terrain_desert.png) | ![](docs/demo/terrain_snow.png) | ![](docs/demo/terrain_ocean.png) | ![](docs/demo/terrain_forest.png) |

### Buildings (5 Styles)
| Medieval | Modern | Sci-Fi | Rustic | Fantasy |
|----------|--------|--------|--------|---------|
| ![](docs/demo/building_medieval.png) | ![](docs/demo/building_modern.png) | ![](docs/demo/building_sci_fi.png) | ![](docs/demo/building_rustic.png) | ![](docs/demo/building_fantasy.png) |

### Characters & Props
| Warrior | Mage | Archer | Rogue | Tree | Chest | Mushroom |
|---------|------|--------|-------|------|-------|---------|
| ![](docs/demo/char_warrior.png) | ![](docs/demo/char_mage.png) | ![](docs/demo/char_archer.png) | ![](docs/demo/char_rogue.png) | ![](docs/demo/prop_tree.png) | ![](docs/demo/prop_chest.png) | ![](docs/demo/prop_mushroom.png) |

### BSP Dungeons
| Stone | Dungeon | Cave | Ice |
|-------|---------|------|-----|
| ![](docs/demo/dungeon_stone.png) | ![](docs/demo/dungeon_dungeon.png) | ![](docs/demo/dungeon_cave.png) | ![](docs/demo/dungeon_ice.png) |

### Complete Game Levels
| Village | Dungeon | Space | Fantasy | Arctic |
|---------|---------|-------|---------|--------|
| ![](docs/demo/game_village_level.png) | ![](docs/demo/game_dungeon_level.png) | ![](docs/demo/game_space_level.png) | ![](docs/demo/game_fantasy_level.png) | ![](docs/demo/game_arctic_level.png) |

---

## Complete Example: Offline Game in 3 Steps

```bash
# Step 1 — download a free model (one time, ~2 GB)
voxelforge model download llama3.2-3b

# Step 2 — start local inference server
voxelforge serve --model llama3.2-3b &

# Step 3 — generate a complete playable game
voxelforge game --title "Crystal Ice Dungeon" --genre dungeon \
                --player-class mage --enemies 3
# Output:  generated_assets/games/crystal_ice_dungeon/
# Run:     cd engine_vfe && ./voxelforge --scene ../generated_assets/...
```

---

## Examples

| File | Description |
|------|-------------|
| `examples/01_generate_assets.py` | Terrain, buildings, characters, props — from Python |
| `examples/02_build_scene.py` | Full scene with 15 entities + lights |
| `examples/03_ai_agent.py` | Autonomous agent with text prompt |
| `examples/04_openai_function_calling.py` | GPT-4o tool-calling loop |
| `examples/05_generate_full_game.py` | 3 complete mini-games |

---

## Environment Variables

```bash
# ── Image generation ──────────────────────────────────────────────
OPENROUTER_API_KEY=sk-or-v1-...   # 300+ models; Grok Imagine, FLUX, DALL-E
OPENAI_API_KEY=sk-...             # DALL-E fallback

# ── Free LLM providers (use any one or more) ─────────────────────
GROQ_API_KEY=...
CEREBRAS_API_KEY=...
SAMBANOVA_API_KEY=...
NVIDIA_API_KEY=...
GEMINI_API_KEY=...
LLM7_API_KEY=...
TOGETHER_API_KEY=...
HF_API_KEY=...                    # Hugging Face
OLLAMA_BASE_URL=http://localhost:11434

# ── Local inference ───────────────────────────────────────────────
VFE_MODELS_DIR=~/.voxelforge/models   # where GGUF files are stored
VFE_LLAMA_SERVER=/path/to/llama-server  # override auto-detection
VFE_INFERENCE_PORT=8090               # local server port
VFE_N_GPU_LAYERS=0                    # 0=CPU, -1=all GPU, N=partial
VFE_THREADS=4                         # inference thread count

# ── LLM routing ───────────────────────────────────────────────────
LLM_PROVIDER=local                # force a specific provider
LLM_API_KEY=...                   # generic fallback key
LLM_MODEL=gpt-4o-mini             # model name override
LLM_API_BASE=http://localhost:8090/v1  # custom endpoint

# ── Assets ────────────────────────────────────────────────────────
VOXELFORGE_ASSETS_DIR=generated_assets
```

**No API keys required** — procedural and local-LLM fallbacks handle everything.

---

## Sources & Inspiration

| Repository | Pattern Integrated |
|------------|-------------------|
| [KellerMartins/PixelVoxels](https://github.com/KellerMartins/PixelVoxels) | Original legacy C engine (rebranded + headless) |
| [acatovic/ai-game-studio](https://github.com/acatovic/ai-game-studio) | OpenRouter sprite/video generation; chroma-key pipeline |
| [ackness/ai-gamestudio](https://github.com/ackness/ai-gamestudio) | Dual-model narrative engine; plugin system; SQLite state |
| [pamirtuna/gamestudio-subagents](https://github.com/pamirtuna/gamestudio-subagents) | 12-agent pipeline; market analysis; project init |
| [dada-x/pixelda](https://github.com/dada-x/pixelda) | rembg neural BG removal; frame splitter; sprite merger |
| [marcelontime/spriteforge](https://github.com/marcelontime/spriteforge) | 11 game-art styles; 12 animation actions; per-frame regen |
| [yashdew3/AI-Game-Generator](https://github.com/yashdew3/AI-Game-Generator) | Text → single-file HTML5 game via free Gemini tier |
| [tayles/ai-sprite-image-generator](https://github.com/tayles/ai-sprite-image-generator) | Grid batch generation (25 imgs/call, 30× cheaper) |
| [ifarangiis/ai-game-asset-generator](https://github.com/ifarangiis/ai-game-asset-generator) | 39 art styles; custom colour palettes |
| [jamesvovos/ai-game-asset-creator](https://github.com/jamesvovos/ai-game-asset-creator) | Chained LLM pipeline: storyline → quests → dialogue → items |
| [apmantza/pi-free](https://github.com/apmantza/pi-free) | Free LLM router; 10 providers; `isFreeModel()` heuristic |
| [Yuan-ManX/ai-game-devtools](https://github.com/Yuan-ManX/ai-game-devtools) | AI tool catalog reference |
| [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) | Agent hierarchy; slash commands; MDA framework |

---

## Tests

```bash
pytest tests/ -v   # 29 tests: .vox I/O, generators, scene format, studio tools
```

Key regression: `test_scene_format_matches_engine` verifies the JSON structure
against what `EngineScene.c` / `EngineECS.c` parse.

---

## License

MIT — original Vopix engine by [KellerMartins](https://github.com/KellerMartins/PixelVoxels).
VoxelForge Engine (VFE) and all Python additions are original work released under MIT.
