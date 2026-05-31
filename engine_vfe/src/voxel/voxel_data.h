/*
 * VFE — Voxel data structures
 *
 * A VoxelGrid stores voxels in a flat uint8 array.
 * Index = x + y * W + z * W * H
 * Value 0 = empty; 1-255 = palette colour index.
 *
 * Large worlds are managed as 16×16×16 Chunks, addressed by chunk
 * coordinates.  Each chunk owns its own VoxelGrid and dirty flag so
 * the greedy mesher only re-triangulates changed chunks.
 */
#pragma once
#ifndef VFE_VOXEL_DATA_H
#define VFE_VOXEL_DATA_H

#include "../core/types.h"
#include <stdbool.h>

/* ── Palette ─────────────────────────────────────────────────────────── */
#define VFE_PALETTE_SIZE 256

typedef struct {
    Color8 colors[VFE_PALETTE_SIZE]; /* RGBA, index 0 = transparent/air  */
} VoxelPalette;

void vfe_palette_default  (VoxelPalette *pal);
void vfe_palette_from_png (VoxelPalette *pal, const char *path);
void vfe_palette_to_tex1d (const VoxelPalette *pal, unsigned int *tex_id);

/* ── Voxel Grid ──────────────────────────────────────────────────────── */
typedef struct {
    u8   *data;        /* flat W*H*D array, index = x + y*W + z*W*H     */
    u16   w, h, d;     /* dimensions in voxels                            */
    Vec3  pivot;       /* model-space pivot (centre)                      */
    bool  dirty;       /* mesh needs rebuilding                           */
} VoxelGrid;

VoxelGrid *vfe_grid_create (u16 w, u16 h, u16 d);
void       vfe_grid_destroy(VoxelGrid *g);

static inline u8 vfe_grid_get(const VoxelGrid *g, i32 x, i32 y, i32 z) {
    if (x < 0 || x >= g->w || y < 0 || y >= g->h || z < 0 || z >= g->d)
        return 0;
    return g->data[(u32)x + (u32)y * g->w + (u32)z * g->w * g->h];
}
static inline void vfe_grid_set(VoxelGrid *g, i32 x, i32 y, i32 z, u8 v) {
    if (x < 0 || x >= g->w || y < 0 || y >= g->h || z < 0 || z >= g->d)
        return;
    g->data[(u32)x + (u32)y * g->w + (u32)z * g->w * g->h] = v;
    g->dirty = true;
}
u32  vfe_grid_voxel_count(const VoxelGrid *g);
void vfe_grid_fill(VoxelGrid *g, u8 color);
void vfe_grid_fill_box(VoxelGrid *g, i32 x0,i32 y0,i32 z0,
                                     i32 x1,i32 y1,i32 z1, u8 color);

/* ── Chunk ───────────────────────────────────────────────────────────── */
#define VFE_CHUNK_DIM VFE_CHUNK_SIZE   /* 16 voxels per axis             */

typedef struct {
    VoxelGrid   *grid;
    IVec3        coord;   /* chunk coordinates (not voxel coordinates)    */
    bool         active;
    unsigned int vao, vbo_pos, vbo_norm, vbo_col;
    u32          vert_count;
    bool         mesh_dirty;
} Chunk;

/* ── VoxelModelAsset (shared across entities) ───────────────────────── */
struct VoxelModelAsset {
    VoxelGrid   *grid;
    VoxelPalette palette;
    char         path[256];
    unsigned int vao;
    unsigned int vbo[3];   /* position, normal-occlusion, color          */
    u32          vert_count;
    bool         loaded;
    bool         mesh_dirty;
};

VoxelModelAsset *vfe_asset_load_vox (const char *path);
void             vfe_asset_unload   (VoxelModelAsset *a);
bool             vfe_asset_rebuild  (VoxelModelAsset *a);

#endif /* VFE_VOXEL_DATA_H */
