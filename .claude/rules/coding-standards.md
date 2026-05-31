# VoxelForge Coding Standards

## Python

- **Type hints** required on all public functions and class attributes
- **Black** for formatting: `black forge/ tests/`
- **Ruff** for linting: `ruff check forge/ tests/ --ignore E501`
- **Pyright** for type checking: `pyright forge/ cli/`
- No bare `except:` — always `except SpecificError:`
- Docstrings in **Google style**

## Scene JSON (Critical)

NEVER produce scene JSON that doesn't exactly match `EngineECS.c`:

```python
# ✅ CORRECT
scene.add_point_light("sun", range_=100.0, hue_shift=0.0)

# ❌ WRONG (radius doesn't exist in engine)
scene.add_point_light("sun", radius=100.0)
```

## Lua Templates

NEVER use f-strings or `.format()` for Lua code that contains `{}`:

```python
# ✅ CORRECT
script = "local t = " + "{1,2,3}" + "\n"

# ❌ WRONG (SyntaxError in Python 3.12+)
script = f"local t = {1,2,3}\n"
```

## Git Commits

Every commit MUST include the Co-Authored-By trailer:

```
feat: description of what was added

Co-Authored-By: ey sho <eysho.it@gmail.com>
```

## File Organisation

- New generators → `forge/generators/<name>.py`
- New API models → `forge/api/models.py`
- New endpoints → `forge/api/server.py`
- New tools → `forge/ai/tools.py` (HTTP + local dispatch + TOOLS schema)
- New tests → `tests/test_voxel.py`

## Naming

- Asset names: `snake_case`, descriptive, no spaces
- Scene files: `<world_name>.scene`
- Vox files: `<category>_<name>.vox`
- Lua scripts: `<role>.lua` (player.lua, enemy_0.lua, objective.lua)
