# ADR-002: Python Generators Are Pure-Python (No C Compilation)

**Date**: 2025-05-31
**Status**: Accepted

## Context

VoxelForge needs to generate voxel assets programmatically. The question was
whether to call into the C engine (via subprocess or ctypes) or implement
all generation logic in pure Python.

## Decision

All generators are pure Python using NumPy arrays. The C engine is only used
for rendering and gameplay, never for asset generation.

## Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|-------------|
| Call C engine headlessly | Single codebase | SDL/OpenGL needed even for generation, no CI | Rejected |
| ctypes bindings | Shared logic | Complex build, brittle ABI | Rejected |
| **Pure Python + NumPy** | Portable, no build, works in CI | Separate logic from C engine | Selected |

## Consequences

**Positive**:
- Generators run without SDL2/OpenGL installed
- Works in Docker, CI, headless servers
- Fast iteration — no recompile after changes

**Negative / Trade-offs**:
- Generation logic duplicated from C engine (voxel indexing, .vox format)
- Must keep Python .vox writer in sync with engine's reader

## Related ADRs
- ADR-003: API-first design with local fallback
