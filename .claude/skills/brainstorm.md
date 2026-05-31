# /brainstorm — Creative Brainstorming Session

**Usage**: `/brainstorm <concept>`

**Description**: Run a structured creative brainstorming session for a game concept.
Produces 5 distinct game directions, each with a unique hook, MDA breakdown, and quick-start command.

## Output Format

When invoked with a concept, generate **5 numbered game directions**:

---

### Direction N: <PUNCHY TITLE>

**One-Line Pitch**: <exciting 1-sentence description>

**Core Fantasy**: <what power/experience does the player live?>

**Unique Hook**: <what makes this unforgettable?>

**MDA Snapshot**:
- M: <2-3 key mechanics>
- D: <emergent behavior>
- A: <primary emotion>

**VoxelForge Config**:
```python
gen.generate(
    title="<title>",
    genre="<genre>",
    player_class="<class>",
    enemies=<N>,
    level_size=<S>,
)
```

**Bartle Appeal**: [Achiever ★★★] [Explorer ★★☆] [Killer ★☆☆] [Socializer ☆☆☆]

---

## Brainstorming Triggers

When stuck, apply these lenses to any concept:

| Lens | Question |
|------|---------|
| Reversal | What if the player IS the enemy? |
| Escalation | What happens when you add 10× more of everything? |
| Constraint | What if the player can only do ONE thing? |
| Mashup | Combine this genre with a completely different one |
| Emotion First | What feeling do you want in the last 10 seconds? |
| Time | What if everything happened 10× faster / slower? |
| Space | What if the level was 1 voxel wide? Or 1000? |
