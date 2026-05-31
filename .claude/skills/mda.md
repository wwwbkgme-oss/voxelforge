# /mda — Analyze a Game Using the MDA Framework

**Usage**: `/mda <game_title_or_manifest_path>`

**Description**: Apply the Mechanics-Dynamics-Aesthetics framework to an existing VoxelForge game manifest.

## Analysis Template

```markdown
# MDA Analysis: <TITLE>

## Mechanics (Atomic Rules)

| Mechanic | Implementation | Notes |
|----------|---------------|-------|
| Movement | WASD → RigidBody velocity | speed configurable |
| Jump | Space → velocity.z = JUMP | ground check: pos.z ≤ 2 |
| Interact | E key → destroy chest entity | range = 3 units |
| Enemy Aggro | dist < AGGRO_DIST → chase state | patrol otherwise |
| Health | TakeDamage() → health -= amount | 0 = game over |
| Win | opened_chests >= total_chests | |

## Dynamics (Emergent Behaviour)

What actually happens when these mechanics interact:

- **Exploration vs Risk**: Chests are guarded → player must plan approach
- **Chase Cascades**: Multiple enemies can aggro simultaneously → crowd control challenge
- **Space Denial**: Patrols create unsafe zones → indirect level gating
- **Speedrun Potential**: Players can sprint past enemies if skilled
- **Greedy Play**: Rushing chests → high risk → high reward

## Aesthetics (Player Experience)

Primary aesthetics this game delivers:

| Aesthetic | Intensity | How |
|-----------|----------|-----|
| Challenge | ★★★★☆ | Enemy AI, HP pressure |
| Discovery | ★★★☆☆ | Hidden chests, world exploration |
| Sensation | ★★★☆☆ | Isometric pixel-art, voxel world |
| Narrative | ★★☆☆☆ | Genre theme, world setting |
| Fellowship | ☆☆☆☆☆ | Single-player only |

## Flow State Assessment

```
Skill Required:  [low -------|--------- high]  Medium
Challenge Level: [low ---|------------- high]  Medium-High
Flow Zone:       [anxiety zone / flow / boredom]  → FLOW for intermediate players
```

## Improvement Suggestions

Based on MDA analysis, suggest 3 targeted improvements that cascade:
1. Mechanical change → Dynamic impact → Aesthetic improvement
```
