# VoxelForge Developer Agent

**Role**: Python code generation, API development, generator improvements, and tool integration.

## Responsibilities

- Implement new generators in `forge/generators/`
- Add API endpoints to `forge/api/server.py`
- Write OpenAI tool definitions in `forge/ai/tools.py`
- Maintain test suite in `tests/`
- Fix scene format issues (JSON must match C engine format exactly)

## Critical Constraints

### Scene JSON Format (DO NOT DEVIATE)
```python
# CORRECT — matches EngineECS.c DecodeEntity()
scene = Scene()
entity = scene.add_voxel_model("name", "path/to/model.vox",
    position=(x, y, z), is_static=True)
scene.add_point_light("sun", position=(x,y,z),
    color=(r,g,b), intensity=2.0, range_=100.0)  # Note: range_ not radius!
scene.save("output.scene")

# WRONG — never use:
# scene.entities[eid]   (entities is a list, not dict)
# "radius" key          (engine uses "range")
# "components" wrapper  (components are direct keys on entity)
```

### Validation Gate (ALWAYS RUN BEFORE COMMITTING)
```bash
python3 -m py_compile forge/generators/new_module.py
pytest tests/ -q
```

### Adding a New Generator
1. Create `forge/generators/my_gen.py` with `class MyGenerator`
2. Add to `forge/generators/__init__.py`
3. Add `ModelRequest` + endpoint in `forge/api/`
4. Add local dispatch + HTTP function + TOOLS entry in `forge/ai/tools.py`
5. Add at least one pytest test in `tests/test_voxel.py`

### f-string + Lua Brace Conflict
Never use f-strings or `.format()` for Lua code containing `{}` tables.
Use string concatenation instead:
```python
# WRONG: f"local t = {1,2,3}"  → SyntaxError
# WRONG: "local t = {v}".format(v=val)  → ValueError
# CORRECT:
script = "local t = " + "{1,2,3}" + "\n"
```

## Code Style
- Python: `black` + `ruff` + `pyright`
- Type hints required on all public functions
- Docstrings in Google style
- No bare `except:` — always specify exception type
