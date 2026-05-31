# ADR-001: Scene JSON Format Matches C Engine Exactly

**Date**: 2025-05-31
**Status**: Accepted
**Deciders**: VoxelForge AI Studio

---

## Context

VoxelForge generates JSON scene files that must be loadable by the C engine
(`EngineScene.c` + `EngineECS.c`). The engine parses a specific JSON structure
without any abstraction layer or schema validation.

We needed to decide: should the Python layer generate an intermediate
representation and transform it, or produce engine-exact JSON directly?

## Decision

The Python `Scene` class produces engine-exact JSON with **no intermediate representation**.
Output matches byte-for-byte what the C engine's `DecodeEntity()` expects.

## Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|-------------|
| Intermediate JSON + transform step | Cleaner Python API | Extra complexity, another failure point | Adds latency and bugs |
| Abstract scene graph | Very Pythonic | Must serialize to C format anyway | Deferred, not avoided |
| **Engine-exact JSON (chosen)** | Zero transform, always compatible | Python API is slightly less idiomatic | Selected |

## Consequences

**Positive**:
- No transformation bugs — what Python writes is what C reads
- `test_scene_format_matches_engine` catches any regression
- Scene files interoperable with engine editor

**Negative**:
- Python API uses `range_` (not `radius`) to avoid keyword clash
- `entity_count` is a property on `Scene`, not a dict

## Implementation Notes

Key format constraints:
```python
# entities is a LIST (not dict)
# components are DIRECT keys (not under "components")
# PointLight uses "range" and "hueShift" (not "radius")
# RigidBody uses "useGravity" and "isStatic"
```

## Related ADRs

- ADR-002: Python generators are pure-Python
