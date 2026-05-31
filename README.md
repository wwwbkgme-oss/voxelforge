# VoxelForge

**AI-Powered Voxel World Builder**

VoxelForge lets an AI autonomously create complete, playable game worlds — terrain,
buildings, characters, props, and assembled scenes — entirely without human intervention.

Built on top of the [Vopix Engine](https://github.com/KellerMartins/PixelVoxels) (a C ECS
voxel engine that renders MagicaVoxel `.vox` files as isometric pixel art), VoxelForge adds:

- **Headless engine mode** — run without a display (`--headless`, `--screenshot`)
- **Python `forge/` package** — pure-Python voxel data model + `.vox` binary read/write
- **Procedural generators** — terrain, buildings, characters, props
- **FastAPI REST server** — all operations over HTTP, auto-documented at `/docs`
- **OpenAI function-calling tools** — every endpoint as an LLM-callable tool definition
- **Autonomous agent** — give it a text prompt, it builds the whole game unattended

---

## Quick Start

### 1. Install Python dependencies

```bash
pip install -e ".[ai]"
```

### 2. Start the REST API server

```bash
voxelforge api
# API running at http://localhost:8080
# Docs at     http://localhost:8080/docs
```

### 3. Build a complete world with one call

```bash
curl -X POST http://localhost:8080/world/build \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_village",
    "biome": "grassland",
    "buildings": 4,
    "building_style": "medieval",
    "characters": 2,
    "props": 6
  }'
```

### 4. Run the autonomous AI agent

```bash
# Direct mode (no OpenAI key needed):
voxelforge agent --direct "a haunted forest with 3 gothic towers and mushroom trees"

# LLM mode (GPT-4o):
export OPENAI_API_KEY=sk-...
voxelforge agent "a medieval village with a blacksmith, inn, and warrior heroes"
```

### 5. Play the generated world in the engine

```bash
cd engine
make
./voxelforge --scene ../generated_assets/scenes/my_village.scene
```

---

## Architecture

```
voxelforge/
├── engine/               # C game engine (VoxelForge, rebranded from Vopix)
│   ├── Source/           # ECS engine: rendering, physics, Lua scripting
│   ├── Assets/           # Shaders, default scene, example .vox models
│   └── Makefile          # Build with: make  (produces ./voxelforge binary)
│
├── forge/                # Python automation layer
│   ├── voxel.py          # VoxelModel + Palette: .vox binary read/write
│   ├── scene.py          # Scene builder → JSON scene files
│   ├── generators/
│   │   ├── terrain.py    # FBM noise terrain with biomes
│   │   ├── buildings.py  # Multi-floor buildings (5 styles)
│   │   ├── characters.py # Humanoid characters (4 classes)
│   │   └── props.py      # Trees, crates, barrels, lamps, rocks, chests
│   ├── api/
│   │   ├── server.py     # FastAPI REST server
│   │   └── models.py     # Pydantic request/response models
│   └── ai/
│       ├── tools.py      # OpenAI function-calling tool definitions
│       └── agent.py      # Autonomous game-creation agent
│
├── cli/
│   └── main.py           # voxelforge CLI
├── examples/             # Runnable example scripts
└── docker/               # Docker / docker-compose setup
```

---

## REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/asset/terrain` | Generate terrain from biome + size |
| `POST` | `/asset/building` | Generate a building (5 styles) |
| `POST` | `/asset/character` | Generate a humanoid character |
| `POST` | `/asset/prop` | Generate a prop (tree/crate/barrel/…) |
| `GET`  | `/assets` | List all generated .vox assets |
| `POST` | `/scene/build` | Build a scene from entity list |
| `GET`  | `/scenes` | List all generated scenes |
| `POST` | `/world/build` | **One-call complete world generation** |
| `GET`  | `/asset/download?path=…` | Download a .vox file |

Full interactive docs: **http://localhost:8080/docs**

---

## AI Tool Definitions

VoxelForge exports every API endpoint as an **OpenAI function-calling tool**,
compatible with GPT-4o, Claude (via OpenRouter), Gemini, and local Ollama models.

```python
from forge.ai.tools import TOOLS, call_tool

# Pass TOOLS directly to any OpenAI-compatible chat completion:
response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Build me a sci-fi space station"}],
    tools=TOOLS,
)

# Execute tool calls returned by the LLM:
for tc in response.choices[0].message.tool_calls:
    result = call_tool(tc.function.name, tc.function.arguments)
```

---

## Headless Engine Usage

```bash
# Build the C engine (Linux/macOS — requires SDL2, GLEW, Lua5.3):
cd engine && make

# Take a screenshot of any scene without a display:
./voxelforge --headless --screenshot /tmp/preview.png \
             --scene Assets/Game/Scenes/EvilCorpNight.scene

# Run a scene headlessly (e.g. for batch processing):
./voxelforge --headless --scene ../generated_assets/scenes/my_world.scene
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
# Build and start the API server:
docker compose -f docker/docker-compose.yml up -d

# Generated assets are persisted in ./docker/output/
```

---

## Examples

| Script | Description |
|--------|-------------|
| `examples/01_generate_assets.py` | Generate terrain, building, character, props directly from Python |
| `examples/02_build_scene.py` | Build a complete scene with all assets placed |
| `examples/03_ai_agent.py` | Run the autonomous agent with any text prompt |
| `examples/04_openai_function_calling.py` | Integrate VoxelForge tools into an OpenAI chat loop |

---

## Procedural Generator Details

### Terrain
- Multi-octave FBM noise (Perlin-style)
- Biomes: `grassland`, `desert`, `snow`, `ocean`, `forest`
- Automatic water filling, surface/subsurface/rock layers

### Buildings
- Styles: `modern`, `medieval`, `sci-fi`, `rustic`, `fantasy`
- Configurable footprint (4–32 voxels), floors (1–20)
- Automatic window placement, door, roof (flat/peaked/pyramid)

### Characters
- Classes: `warrior`, `mage`, `archer`, `rogue`
- Skin tones, hair colours, armour, weapons
- Approx 8×4×16 voxels — designed for the engine's pixel-art renderer

### Props
- `tree` (oak / pine)
- `crate`, `barrel`, `chest`
- `lamp_post`, `rock`
- `mushroom`

---

## License

MIT — original engine by [KellerMartins](https://github.com/KellerMartins/PixelVoxels).
VoxelForge additions released under the same licence.
