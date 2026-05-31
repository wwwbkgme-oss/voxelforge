# /adr — Create an Architecture Decision Record

**Usage**: `/adr <decision_title>`

**Description**: Document a significant design or architecture decision.
Saves to `design/adrs/ADR-NNN-<title>.md` with auto-incrementing number.

## ADR Template

```markdown
# ADR-NNN: <TITLE>

**Date**: <today>
**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**Deciders**: VoxelForge AI Studio

---

## Context

What is the situation that forces this decision?
What constraints or requirements exist?

## Decision

What was decided?
State the decision clearly in one or two sentences.

## Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|-------------|
| A | ... | ... | ... |
| B | ... | ... | ... |
| **Chosen** | ... | ... | *Selected* |

## Consequences

**Positive**:
- ...

**Negative / Trade-offs**:
- ...

**Neutral**:
- ...

## Implementation Notes

How to implement this decision in VoxelForge:

```python
# Example code
```

## Related ADRs

- ADR-NNN: <related>
```

## Existing ADRs

Check `design/adrs/` for all current ADRs before creating a new one.

## Example ADRs to Document

- ADR-001: Scene JSON format matches C engine exactly (no intermediate representation)
- ADR-002: Python generators are pure-Python (no C compilation needed)
- ADR-003: API-first design with local fallback for offline use
- ADR-004: Lua templates use string concatenation (f-string/format conflict with Lua `{}`)
- ADR-005: `Palette.natural()` as default (not MagicaVoxel default) for better world colours
