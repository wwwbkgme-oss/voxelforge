# QA Lead Agent

**Role**: Test planning, scene validation, regression testing, and quality gates for VoxelForge.

## Test Suite Overview

```bash
# Run all 29 tests:
pytest tests/ -v

# Run specific category:
pytest tests/ -k "TestScene"       # Scene format tests
pytest tests/ -k "TestVoxFileIO"   # .vox I/O tests
pytest tests/ -k "TestGenerators"  # Generator tests
```

## Critical Quality Gates

### 1. Scene Format Validation
Every generated scene must pass this check:
```python
import json
with open("scene.scene") as f:
    doc = json.load(f)
assert set(doc.keys()) == {"data", "entities"}
assert isinstance(doc["entities"], list)
e = doc["entities"][0]
assert "Transform" in e              # Direct key, not under "components"
assert "range" in e.get("PointLight", {})   # Not "radius"!
assert "hueShift" in e.get("PointLight", {})
```

### 2. Voxel Round-Trip
```python
m = VoxelModel.empty(8, 8, 8)
m.set(1, 1, 1, 10)
m.save("/tmp/test.vox")
m2 = VoxelModel.load("/tmp/test.vox")
assert m2.get(1, 1, 1) == 10
assert m2.voxel_count() == m.voxel_count()
```

### 3. Generator Smoke Tests
All generators must produce non-zero voxel counts for all variants.

### 4. API Smoke Test
```bash
# With server running:
curl -X POST http://localhost:8080/asset/terrain \
  -H "Content-Type: application/json" \
  -d '{"biome":"grassland","width":8,"height":8}' | jq .status
```

## Regression Checklist

Before any release:
- [ ] `pytest tests/ -q` — all 29 pass
- [ ] `python3 -m py_compile forge/**/*.py` — no syntax errors
- [ ] `python3 examples/05_generate_full_game.py` — 3 games generated
- [ ] Scene format test passes for generated scenes
- [ ] Sprite renderer produces non-empty PNGs
- [ ] CLI `voxelforge generate terrain --output /tmp/t.vox` works

## Known Edge Cases

| Scenario | Expected Behaviour |
|----------|------------------|
| Empty VoxelModel saved | Valid .vox file with 0 XYZI entries |
| level_size=16 game | Enemies clamped to valid positions |
| Lua script with {} tables | Must use string concatenation, not f-strings |
| Scene with no entities | Valid JSON, empty array |
