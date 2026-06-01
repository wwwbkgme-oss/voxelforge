"""
forge.studio
============
Claude Code Game Studios-inspired design tools for VoxelForge.

Provides structured game design document generation, MDA framework analysis,
brainstorming sessions, sprint planning, and ADR creation — inspired by the
Claude Code Game Studios methodology.

All tools work in two modes:
  - direct: generate structured documents from parameters (no LLM needed)
  - llm: use OpenAI to generate rich, creative content

Usage
-----
>>> from forge.studio import GameDesignDoc, BrainstormSession, MDAAnalyzer

>>> gdd = GameDesignDoc("Crystal Dungeon", genre="dungeon", player_class="mage")
>>> gdd.save("design/gdds/crystal_dungeon.md")
>>> print(gdd.to_markdown())
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_GENRE_TONE = {
    "village": {"tone": "cozy, hopeful",          "setting": "a lush medieval village",          "enemy": "bandits"},
    "dungeon": {"tone": "tense, mysterious",       "setting": "an ancient underground dungeon",   "enemy": "stone guardians"},
    "space":   {"tone": "vast, wonder",            "setting": "a derelict space station",         "enemy": "rogue drones"},
    "fantasy": {"tone": "epic, magical",           "setting": "an enchanted forest kingdom",      "enemy": "dark mages"},
    "horror":  {"tone": "dread, survival",         "setting": "a cursed forest ruin",             "enemy": "shadow wraiths"},
    "arctic":  {"tone": "stark, brutal",           "setting": "a frozen research outpost",        "enemy": "ice constructs"},
}

_CLASS_DESC = {
    "warrior": ("a heavily armoured fighter", "sword", "close-range combat mastery"),
    "mage":    ("a robed spellcaster",        "staff", "area magic and ranged attacks"),
    "archer":  ("a swift ranger",             "bow",   "long-range precision and speed"),
    "rogue":   ("a nimble assassin",          "axe",   "speed, evasion, and ambushes"),
}

_PLAYER_TYPES = {
    "village": ("Explorer", "★★★"),
    "dungeon": ("Achiever", "★★★★"),
    "space":   ("Explorer", "★★★"),
    "fantasy": ("Achiever + Explorer", "★★★"),
    "horror":  ("Achiever", "★★★★★"),
    "arctic":  ("Achiever", "★★★"),
}


# ---------------------------------------------------------------------------
# GameDesignDoc
# ---------------------------------------------------------------------------

class GameDesignDoc:
    """Generates a structured Game Design Document for a VoxelForge game."""

    def __init__(
        self,
        title:        str,
        genre:        str = "village",
        player_class: str = "warrior",
        enemies:      int = 3,
        props:        int = 6,
        level_size:   int = 48,
        seed:         int = 0,
    ):
        self.title        = title
        self.genre        = genre
        self.player_class = player_class
        self.enemies      = enemies
        self.props        = props
        self.level_size   = level_size
        self.seed         = seed
        self.slug         = re.sub(r"[^\w]", "_", title.lower())[:20]

    # ------------------------------------------------------------------
    def to_markdown(self) -> str:
        gt    = _GENRE_TONE.get(self.genre, _GENRE_TONE["village"])
        cls   = _CLASS_DESC.get(self.player_class, _CLASS_DESC["warrior"])
        ptype, prank = _PLAYER_TYPES.get(self.genre, ("Achiever", "★★★"))
        today = date.today().isoformat()

        return f"""# Game Design Document: {self.title}

**Version**: 1.0
**Date**: {today}
**Genre**: {self.genre.title()}
**Studio**: VoxelForge AI Game Studios

---

## 1. Executive Summary

{self.title} is a single-player isometric voxel game set in {gt['setting']}.
The player controls {cls[0]}, wielding a {cls[1]}, and must navigate the world to
collect scattered treasures while defeating {gt['enemy']}.
The tone is **{gt['tone']}**, delivering a focused {self.genre} experience.

---

## 2. Target Audience

- **Primary Player Type**: {ptype} (Bartle) — {prank}
- **Age Range**: 10+
- **Experience Level**: Casual to mid-core
- **Play Session**: 10–30 minutes

---

## 3. Core Loops

### 30-Second Loop (immediate)
Move → Spot enemy/chest → Decide to fight, route around, or rush → Act

### 5-Minute Loop (challenge)
Clear a section → Collect all chests → Survive → Move to next area

### 30-Minute Loop (progression)
Complete the level → All chests found → Win screen → Replay with higher difficulty

---

## 4. MDA Framework

### Mechanics (rules)
- **Movement**: WASD movement, Space to jump
- **Interaction**: E key to collect chests (range: 3 voxels)
- **Combat**: Proximity-based — enemies aggro within 10–15 voxels
- **Enemy AI**: Patrol → Chase → Attack state machine
- **Objective**: Collect all chests to win

### Dynamics (emergent behaviour)
- Players must path-find around enemy patrol zones to reach chests
- Multiple enemies can chain-aggro, creating crowd-control scenarios
- Chest placement behind enemy clusters creates risk/reward decisions
- Advanced players can sprint through aggro zones for speedrun routes

### Aesthetics (player experience)
- **Primary**: Challenge — overcoming enemies and navigating the {self.genre}
- **Secondary**: Discovery — finding hidden chests and exploring the world
- **Tertiary**: Sensation — isometric pixel-art voxel aesthetic

---

## 5. Character Design

### Player: {self.player_class.title()}
- **Description**: {cls[0]}
- **Weapon**: {cls[1]}
- **Strength**: {cls[2]}
- **Speed**: {"12–14" if self.player_class in ("rogue", "archer") else "10–12"} units/s
- **HP**: 100

### Enemy: {gt['enemy'].title()}
- **Aggro Distance**: {"15" if self.genre in ("dungeon", "horror") else "10"} voxels
- **Chase Speed**: 6 units/s
- **Attack Range**: 2.5 voxels
- **HP**: 30

---

## 6. Level Design

| Level | Size | Enemies | Chests | Notes |
|-------|------|---------|--------|-------|
| L1 | {self.level_size // 2}×{self.level_size // 2} | 1 | 1 | Tutorial room |
| L2 | {self.level_size}×{self.level_size} | {self.enemies} | {max(1, self.props // 3)} | Main challenge |
| L3 | {min(96, self.level_size + 16)}×{min(96, self.level_size + 16)} | {self.enemies * 2} | {max(2, self.props // 2)} | Final challenge |

---

## 7. Asset List

Generated with VoxelForge:
```python
from forge.generators.game import GameGenerator
from forge.voxel import Palette

gen = GameGenerator(Palette.natural(), seed={self.seed}, output_dir="games")
manifest = gen.generate(
    title        = "{self.title}",
    genre        = "{self.genre}",
    player_class = "{self.player_class}",
    enemies      = {self.enemies},
    props        = {self.props},
    level_size   = {self.level_size},
)
print(manifest["run_command"])
```

Assets produced:
- `level.vox` — {"BSP " + self.genre + " dungeon" if self.genre in ("dungeon","horror") else "terrain (" + self.genre + " biome)"}
- `player.vox` — {self.player_class} character
- `enemy_N.vox` × {self.enemies} — {gt['enemy']}
- `prop_N.vox` × {self.props} — scenery + chest collectibles
- Lua scripts: `player.lua`, `enemy_N.lua` × {self.enemies}, `objective.lua`
- `{self.slug}.scene` — complete scene file

---

## 8. Win / Loss Conditions

- **Win**: All chests collected (`opened_chests >= total_chests`)
- **Loss**: Player HP drops to 0
- **Retry**: Reload the same `.scene` file in the engine

---

## 9. Run Command

```bash
cd engine
make          # build once
./voxelforge --scene ../games/games/{self.slug}/scenes/{self.slug}.scene
```

---

## 10. Milestones

| Sprint | Goal | Status |
|--------|------|--------|
| S1 | Level geometry + player movement | 🔲 |
| S2 | Enemy AI + collision | 🔲 |
| S3 | Objectives + HUD | 🔲 |
| S4 | Polish + difficulty tuning | 🔲 |
"""

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        return path


# ---------------------------------------------------------------------------
# BrainstormSession
# ---------------------------------------------------------------------------

_BRAINSTORM_GENRES = ["village", "dungeon", "space", "fantasy", "horror", "arctic"]
_BRAINSTORM_CLASSES = ["warrior", "mage", "archer", "rogue"]
_BRAINSTORM_HOOKS = [
    "What if the collectibles fight back?",
    "What if the level shrinks over time?",
    "What if enemies become allies when low HP?",
    "What if the player can possess enemies?",
    "What if gravity reverses each level?",
    "What if light sources are the enemy's weakness?",
    "What if the map is procedurally extended as you explore?",
]

class BrainstormSession:
    """Generates 5 distinct game directions from a concept."""

    def __init__(self, concept: str, seed: int = 0):
        self.concept = concept
        self.seed    = seed

    def generate(self) -> str:
        import random
        rng = random.Random(self.seed + hash(self.concept) % 10000)
        today = date.today().isoformat()

        lines = [
            f"# Brainstorm Session: {self.concept}",
            f"\n**Date**: {today}",
            f"**Seed**: {self.seed}",
            "\n---\n",
        ]

        for i in range(1, 6):
            genre  = rng.choice(_BRAINSTORM_GENRES)
            cls    = rng.choice(_BRAINSTORM_CLASSES)
            hook   = rng.choice(_BRAINSTORM_HOOKS)
            size   = rng.choice([24, 32, 48, 64])
            enem   = rng.randint(2, 6)
            gt     = _GENRE_TONE[genre]
            title  = f"{self.concept.title()} — {genre.title()} Variant {i}"

            lines += [
                f"## Direction {i}: {title}",
                f"\n**One-Line Pitch**: Play as {_CLASS_DESC[cls][0]} in {gt['setting']}, {gt['tone']}.",
                f"\n**Core Fantasy**: {_CLASS_DESC[cls][2]}",
                f"\n**Unique Hook**: {hook}",
                "\n**MDA Snapshot**:",
                f"- M: Movement, chest collection, enemy {genre} AI",
                f"- D: Path planning around {gt['enemy']}, risk/reward decisions",
                f"- A: {['Challenge', 'Discovery', 'Sensation'][i % 3]}",
                "\n**VoxelForge Command**:",
                "```python",
                f'gen.generate(title="{title}", genre="{genre}",',
                f'             player_class="{cls}", enemies={enem}, level_size={size})',
                "```",
                f"\n**Bartle Appeal**: [{_PLAYER_TYPES[genre][0]} {_PLAYER_TYPES[genre][1]}]",
                "\n---\n",
            ]

        return "\n".join(lines)

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate())
        return path


# ---------------------------------------------------------------------------
# MDAAnalyzer
# ---------------------------------------------------------------------------

class MDAAnalyzer:
    """Analyzes a VoxelForge game manifest using the MDA Framework."""

    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest

    @classmethod
    def from_file(cls, manifest_path: str) -> "MDAAnalyzer":
        with open(manifest_path) as f:
            return cls(json.load(f))

    def analyze(self) -> str:
        m    = self.manifest
        title = m.get("title", "Unknown Game")
        genre = m.get("genre", "village")
        gt    = _GENRE_TONE.get(genre, _GENRE_TONE["village"])
        n_assets  = len(m.get("assets", []))
        n_scripts = len(m.get("scripts", []))
        n_enemies = sum(1 for a in m.get("assets", []) if "enemy" in a.get("name",""))
        n_chests  = sum(1 for a in m.get("assets", []) if "chest" in a.get("name",""))

        return f"""# MDA Analysis: {title}

**Genre**: {genre}  **Tone**: {gt['tone']}
**Assets**: {n_assets}  **Scripts**: {n_scripts}
**Enemies**: {n_enemies}  **Chests**: {n_chests}

---

## Mechanics (Atomic Rules)

| Mechanic | Implementation |
|----------|---------------|
| Movement | WASD → RigidBody velocity |
| Jump | Space → velocity.z = JUMP |
| Interact | E key → destroy chest (range 3) |
| Enemy Aggro | dist < AGGRO_DIST → chase state |
| Health | TakeDamage() → health -= N |
| Win | opened_chests >= {n_chests} |

## Dynamics (Emergent Behaviour)

- **Exploration vs Risk**: {n_chests} chests guarded by {n_enemies} enemies → path planning
- **Chase Cascades**: Multiple enemies can aggro simultaneously
- **Space Denial**: Patrol zones create indirect level gating
- **Tension Spikes**: Risk escalates near heavily guarded chests

## Aesthetics (Player Experience)

| Aesthetic | Intensity | Source |
|-----------|----------|--------|
| Challenge | ★★★★☆ | Enemy AI, HP pressure |
| Discovery | ★★★☆☆ | Hidden chests, world exploration |
| Sensation | ★★★☆☆ | Isometric pixel-art aesthetic |
| Narrative | ★★☆☆☆ | Genre theme ({genre}) |

## Flow State Assessment

```
Skill Required:  ██████████░░ Medium
Challenge Level: ████████████ Medium-High
Flow Zone:       → FLOW for intermediate players
                   ANXIETY for beginners (add tutorial room)
                   BOREDOM for experts (add time pressure)
```

## Improvement Suggestions

1. **Add time pressure** (M) → creates urgency (D) → fear/excitement (A)
2. **Add enemy variety** (M) → different chase speeds (D) → tactical variety (A)
3. **Add health pickups** (M) → risk/reward calculation (D) → relief/tension (A)

## Run Command

```bash
{m.get("run_command", "cd engine && ./voxelforge --scene <path>")}
```
"""

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.analyze())
        return path


# ---------------------------------------------------------------------------
# ADRWriter
# ---------------------------------------------------------------------------

class ADRWriter:
    """Creates Architecture Decision Records with auto-incrementing numbers."""

    def __init__(self, adr_dir: str = "design/adrs"):
        self.adr_dir = adr_dir

    def _next_number(self) -> int:
        os.makedirs(self.adr_dir, exist_ok=True)
        existing = [f for f in os.listdir(self.adr_dir) if f.startswith("ADR-")]
        numbers  = []
        for f in existing:
            try:
                numbers.append(int(f.split("-")[1]))
            except (IndexError, ValueError):
                pass
        return max(numbers) + 1 if numbers else 1

    def create(self, title: str, context: str = "", decision: str = "") -> str:
        """Create a new ADR file and return its path."""
        num   = self._next_number()
        slug  = re.sub(r"[^\w]", "-", title.lower()).strip("-")
        fname = f"ADR-{num:03d}-{slug}.md"
        path  = os.path.join(self.adr_dir, fname)
        today = date.today().isoformat()

        content = f"""# ADR-{num:03d}: {title}

**Date**: {today}
**Status**: Proposed
**Deciders**: VoxelForge AI Studio

---

## Context

{context or f"<Describe the situation that forces this decision for {title}>"}

## Decision

{decision or f"<State what was decided regarding {title} — 1-2 sentences>"}

## Alternatives Considered

| Option | Pros | Cons | Why Rejected |
|--------|------|------|-------------|
| Option A | ... | ... | ... |
| Option B | ... | ... | ... |
| **Chosen** | ... | ... | Selected |

## Consequences

**Positive**:
- ...

**Negative / Trade-offs**:
- ...

## Implementation Notes

```python
# Example code showing how this decision is implemented in VoxelForge
```

## Related ADRs

- ADR-001: Scene JSON format
- ADR-002: Pure Python generators
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path


# ---------------------------------------------------------------------------
# LoreGenerator
# ---------------------------------------------------------------------------

_LORE_ITEMS = {
    "village": {
        "collectible": "ancient coins stolen by bandits",
        "motivation":  "reclaim the village's stolen wealth",
        "win":         "The village is saved. The stolen coins are returned. Peace restored.",
        "flavor_start":"The village elders speak in whispers. The bandits grow bolder each night.",
        "flavor_chest":"A familiar coin — stolen from the market days ago.",
        "flavor_enemy":"They move in the shadows, blades drawn.",
        "tone_words":  "cozy, tense, hopeful, pastoral, warming",
    },
    "dungeon": {
        "collectible": "seal fragments of an ancient prison",
        "motivation":  "seal an imprisoned evil before it fully wakes",
        "win":         "The seals are placed. The darkness retreats. The dungeon falls silent.",
        "flavor_start":"Cold stone. Dripping water. Something stirs in the deep.",
        "flavor_chest":"A seal fragment, still humming with old magic.",
        "flavor_enemy":"Stone eyes open. It remembers you.",
        "tone_words":  "oppressive, ancient, cold, inevitable, dread",
    },
    "space": {
        "collectible": "reactor cores to power the escape pod",
        "motivation":  "escape the derelict station before it self-destructs",
        "win":         "Cores installed. Pod launches. The station explodes behind you.",
        "flavor_start":"Emergency lighting. No crew. Just the hum of failing systems.",
        "flavor_chest":"A reactor core, still warm.",
        "flavor_enemy":"Target acquired. Lethal force authorised.",
        "tone_words":  "isolated, sterile, urgent, vast, hollow",
    },
    "fantasy": {
        "collectible": "shards of a shattered crystal crown",
        "motivation":  "reunite the shards to restore the fallen kingdom",
        "win":         "The crown is whole. The kingdom stirs. Magic returns to the land.",
        "flavor_start":"The old king's crown was shattered across the forest. Find the shards.",
        "flavor_chest":"A shard pulses with golden light.",
        "flavor_enemy":"The dark mage's minion regards you with hollow eyes.",
        "tone_words":  "mythic, vibrant, destined, ancient, wonder",
    },
    "horror": {
        "collectible": "soul lanterns to seal the ritual circle",
        "motivation":  "seal the ritual before the shadow entity crosses over",
        "win":         "The last lantern placed. Silence. The entity screams and is gone.",
        "flavor_start":"Do not put out your light. Do not let them see your face.",
        "flavor_chest":"A lantern. Still lit. Someone else was here recently.",
        "flavor_enemy":"It moves wrong. Like something wearing a person.",
        "tone_words":  "dread, paranoid, oppressive, bleak, suffocating",
    },
    "arctic": {
        "collectible": "emergency beacon modules",
        "motivation":  "assemble a beacon to signal rescue before freezing",
        "win":         "Beacon online. Signal sent. Now you wait.",
        "flavor_start":"Temperature: -40°C. Fuel: 12%. Rescue ETA: unknown.",
        "flavor_chest":"A beacon module, frosted but functional.",
        "flavor_enemy":"It stopped responding to commands three days ago.",
        "tone_words":  "stark, brutal, silent, cold, survival",
    },
}

class LoreGenerator:
    """Generates narrative world lore for a VoxelForge game."""

    def __init__(self, world_name: str, genre: str = "village"):
        self.world_name = world_name
        self.genre      = genre

    def generate(self) -> str:
        lore  = _LORE_ITEMS.get(self.genre, _LORE_ITEMS["village"])
        gt    = _GENRE_TONE.get(self.genre, _GENRE_TONE["village"])
        today = date.today().isoformat()

        return f"""# World Lore: {self.world_name}

**Genre**: {self.genre.title()}  **Date**: {today}
**Tone**: {gt['tone']}

---

## The World

{self.world_name} is {gt['setting']}, a place of {lore['tone_words'].split(',')[0]} beauty
and {lore['tone_words'].split(',')[-1].strip()} danger.
Once prosperous, it now harbours a threat that only a lone hero can face.

The world is rendered in VoxelForge's isometric pixel-art style —
small, expressive voxel figures moving through a hand-crafted voxel landscape.

## The Mission

The player must collect **{lore['collectible']}** scattered across the map.
Their motivation: **{lore['motivation']}**.

## Flavour Text

| Moment | Text |
|--------|------|
| Game start | *"{lore['flavor_start']}"* |
| Chest found | *"{lore['flavor_chest']}"* |
| Enemy spotted | *"{lore['flavor_enemy']}"* |
| Win | *"{lore['win']}"* |

## Tone Words

`{lore['tone_words']}`

## Enemy Faction

The **{_GENRE_TONE[self.genre]['enemy'].title()}** oppose the player.
They patrol the {self.genre} in a mindless loop — until something triggers their
aggression radius, and they become relentless pursuers.

## World Collectibles

The **{lore['collectible']}** are the game's macguffins.
Each one brings the player closer to the win state.
Each one is guarded — directly or indirectly — by the enemies.
"""

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate())
        return path
