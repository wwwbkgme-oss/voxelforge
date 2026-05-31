# /sprint — Generate a Sprint Plan

**Usage**: `/sprint <feature_or_milestone> [duration_days]`

**Description**: Break down a VoxelForge feature or milestone into a sprint plan with story points and acceptance criteria.

## Sprint Plan Template

```markdown
# Sprint Plan: <FEATURE>

**Duration**: <N> days
**Goal**: <one-sentence sprint goal>
**Velocity Target**: <N> story points

---

## Stories

### Story 1: <Title> (N pts)
**As a** <persona>
**I want** <capability>
**So that** <benefit>

**Acceptance Criteria**:
- [ ] <AC1>
- [ ] <AC2>
- [ ] Tests pass: `pytest tests/ -k "<test_name>"`

---

## Technical Tasks

| Task | Owner | Est | Done |
|------|-------|-----|------|
| ... | voxelforge-dev | 2h | [ ] |

## Definition of Done

- [ ] Code written and passing pyright
- [ ] pytest tests added and passing
- [ ] Scene format validated
- [ ] Committed with Co-Authored-By trailer
- [ ] PR description includes before/after comparison
```

## Story Point Scale

| Points | Effort |
|--------|--------|
| 1 | Trivial — config change, rename |
| 2 | Small — single function, 1 test |
| 3 | Medium — new generator method |
| 5 | Large — new generator class |
| 8 | Complex — new API endpoint + tool + test |
| 13 | Epic — split into sub-stories |

## VoxelForge Backlog Items (ready to sprint)

- Add particle system support to VoxelModel
- Multi-level game generation (overworld + dungeon)
- Animated voxel models (frame sequences)
- Multiplayer scene export format
- Web-based voxel editor
- Custom palette import from PNG
- Pathfinding for enemy AI
- Audio event triggers in scene JSON
