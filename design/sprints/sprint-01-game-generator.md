# Sprint Plan: Complete Mini-Game Generator

**Duration**: 5 days
**Goal**: Deliver `GameGenerator` — one call produces a fully playable VoxelForge game
**Velocity Target**: 21 story points
**Status**: ✅ Completed

---

## Stories

### Story 1: GameGenerator class (5 pts) ✅
**As a** developer  
**I want** `GameGenerator.generate()` to produce terrain/dungeon, player, enemies, props, and Lua scripts  
**So that** a complete game is built in one Python call

**Acceptance Criteria**:
- [x] Generates level asset (terrain or dungeon based on genre)
- [x] Generates player character with class-matched armour/weapon
- [x] Generates N enemy characters with Lua AI scripts
- [x] Generates M prop assets (including chests)
- [x] Outputs `manifest.json` with all paths and `run_command`
- [x] Scene entity count matches `manifest["entity_count"]`
- [x] `python3 examples/05_generate_full_game.py` — 3 games generated

---

### Story 2: POST /game/generate endpoint (3 pts) ✅
**As an** API consumer  
**I want** `POST /game/generate` to return a full game manifest  
**So that** any client can generate a game over HTTP

**Acceptance Criteria**:
- [x] Returns `GameGenerateResponse` with scene_path, run_command, counts
- [x] All 6 genres work
- [x] Endpoint documented at `/docs`

---

### Story 3: `generate_game` AI tool (2 pts) ✅
**As an** LLM agent  
**I want** a `generate_game` OpenAI function-calling tool  
**So that** GPT-4o/Claude can generate a full game autonomously

**Acceptance Criteria**:
- [x] Added to `TOOLS` list (10 total tools)
- [x] HTTP + local dispatch both work
- [x] Tool description says "COMPLETE, immediately playable"

---

### Story 4: Lua script templates (5 pts) ✅
**As a** player  
**I want** player controller, enemy AI, and objective scripts  
**So that** the generated game is playable without manual scripting

**Acceptance Criteria**:
- [x] `player.lua` — WASD movement, jump, camera follow, HUD
- [x] `enemy_N.lua` — patrol/chase/attack states per enemy
- [x] `objective.lua` — chest collection win condition
- [x] Scripts use string concatenation (no f-string/Lua brace conflict)

---

### Story 5: Dashboard game generator panel (3 pts) ✅
**As a** user  
**I want** a "Generate Complete Game" panel in the web dashboard  
**So that** I can create a game with one button click

**Acceptance Criteria**:
- [x] Genre, player class, enemies, props, level size controls
- [x] Shows scene path and `run_command` after generation
- [x] Calls `POST /game/generate`

---

### Story 6: 3-game example script (2 pts) ✅
**As a** developer learning VoxelForge  
**I want** `examples/05_generate_full_game.py` to demo 3 different genres  
**So that** I can see the variety of games producible

**Acceptance Criteria**:
- [x] Generates dungeon, village, and space games
- [x] Prints scene paths and run commands
- [x] Runs without errors: `python3 examples/05_generate_full_game.py`

---

## Technical Tasks Completed

| Task | Module |
|------|--------|
| `_player_script()` function | `forge/generators/game.py` |
| `_enemy_script()` function | `forge/generators/game.py` |
| `_objective_script()` function | `forge/generators/game.py` |
| `GameGenerator.generate()` | `forge/generators/game.py` |
| `GameGenerateRequest/Response` models | `forge/api/models.py` |
| `POST /game/generate` endpoint | `forge/api/server.py` |
| `generate_game` HTTP + local + schema | `forge/ai/tools.py` |
| Game panel in dashboard | `forge/api/static/index.html` |
| Example 05 | `examples/05_generate_full_game.py` |

## Definition of Done ✅

- [x] All code written and passing pyright syntax check
- [x] 29 pytest tests still passing (no regressions)
- [x] Scene format validated (entities array, direct component keys)
- [x] 3 games generated in `examples/05_generate_full_game.py`
- [x] Committed with Co-Authored-By trailer
