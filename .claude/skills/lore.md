# /lore — Generate World Lore and Narrative

**Usage**: `/lore <world_name> [genre]`

**Description**: Generate narrative lore that gives a VoxelForge world depth and story.

## Lore Output Template

```markdown
# World Lore: <WORLD NAME>

## The World

<2-paragraph world description that explains the setting, history, and current conflict>

## Factions

### The <Player Faction>
<Who the player represents. Their motivation, appearance, homeland>

### The <Enemy Faction>
<Who the enemies are. Why they oppose the player. Their origin>

## The Conflict

<1 paragraph explaining the central conflict that drives gameplay>

## Key Locations

| Location | Description | VoxelForge Asset |
|----------|-------------|-----------------|
| <Name>   | <Role in world> | `building_medieval` |
| <Name>   | <Role in world> | `dungeon_stone` |
| <Name>   | <Role in world> | `terrain_forest` |

## Objective Framing

The chest collectibles represent: <artifacts / weapons / scrolls / gems>
Why the player seeks them: <motivation that fits the genre>
What happens when all are found: <win condition narrative>

## Tone Words

<5-7 adjectives that define the world's mood>

## Sample Flavour Text (for HUD/UI)

- Start: "<Welcome message that sets the mood>"
- Chest found: "<Flavour text for discovery>"
- Enemy spotted: "<Alert line>"
- Win: "<Victory message>"
```
