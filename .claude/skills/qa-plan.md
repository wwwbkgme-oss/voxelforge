# /qa-plan — Generate a QA Test Plan

**Usage**: `/qa-plan <feature>`

## Test Plan Template

```markdown
# QA Test Plan: <FEATURE>

## Smoke Tests (run first, ~1 min)
- [ ] `pytest tests/ -q`  — all 29 must pass
- [ ] Scene format check  — `{"data":{...}, "entities":[...]}`
- [ ] Generated .vox file opens in MagicaVoxel

## Functional Tests
| Test | Input | Expected | Pass |
|------|-------|---------|------|
| ... | ... | ... | [ ] |

## Edge Cases
- [ ] level_size=16 (minimum) — no index out of bounds
- [ ] enemies=0 — game still generates
- [ ] Empty VoxelModel — valid .vox file
- [ ] Palette index 0 — transparent, not rendered

## Regression Tests
- [ ] `python3 examples/05_generate_full_game.py` — 3 games OK
- [ ] `python3 examples/02_build_scene.py` — 15 entities, correct JSON
- [ ] Sprite renderer produces non-empty PNG

## API Tests (with server)
```bash
curl -X POST localhost:8080/health         # 200
curl -X POST localhost:8080/asset/terrain -d '{}' | jq .status  # "ok"
curl -X POST localhost:8080/game/generate \
  -d '{"title":"t","genre":"dungeon"}' | jq .scene_path
```
```
