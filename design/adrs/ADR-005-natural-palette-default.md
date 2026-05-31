# ADR-005: Palette.natural() Is the Default Palette

**Date**: 2025-05-31
**Status**: Accepted

## Context

MagicaVoxel's default palette is designed for visual variety but doesn't
map well to the biome/genre colour ranges VoxelForge uses.
We needed a default palette that makes generated worlds visually coherent.

## Decision

`Palette.natural()` is used as the default palette throughout VoxelForge.
It groups colours by semantic category (greens for foliage, browns for earth,
greys for stone, blues for water, etc.) with indices that match the generator
colour range constants.

## Consequences

**Positive**:
- Generated worlds have coherent, themed colours per biome
- Generator colour ranges (e.g., greens 1–20) are reliable and consistent
- Sprite renderer produces visually legible thumbnails

**Negative**:
- Not compatible with assets created in MagicaVoxel with default palette
- Loading engine .vox files (which use MagicaVoxel palette) results in colour mismatch

## Mitigation

When loading engine .vox files with `VoxelModel.load()`, the embedded RGBA
palette chunk is used automatically, so existing assets display correctly.
The conflict only arises when mixing engine assets with generated assets in
the same scene.
