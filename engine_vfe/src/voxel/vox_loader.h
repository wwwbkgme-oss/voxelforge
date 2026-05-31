/*
 * VFE — MagicaVoxel .vox file loader
 *
 * Parses the well-documented .vox binary format (version 150/200).
 * Reference: https://github.com/ephtracy/voxel-model (public domain spec)
 *
 * Supported chunks: SIZE, XYZI, RGBA, nTRN, nSHP, nGRP (multi-model).
 * All code below is original — the .vox format specification is public.
 */
#pragma once
#ifndef VFE_VOX_LOADER_H
#define VFE_VOX_LOADER_H

#include "voxel_data.h"

/*
 * Load a single-model or multi-model .vox file.
 * Returns a newly allocated VoxelGrid and fills *pal with the embedded
 * palette (or the MagicaVoxel default if no RGBA chunk is present).
 * Caller owns the returned VoxelGrid; free with vfe_grid_destroy().
 * Returns NULL on failure.
 */
VoxelGrid *vfe_vox_load(const char *path, VoxelPalette *pal);

/*
 * Write a VoxelGrid + palette back to a .vox file (SIZE + XYZI + RGBA).
 * Returns true on success.
 */
bool vfe_vox_save(const VoxelGrid *grid, const VoxelPalette *pal,
                  const char *path);

#endif /* VFE_VOX_LOADER_H */
