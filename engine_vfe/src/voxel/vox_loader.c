/*
 * VFE — .vox file loader
 *
 * Implements reading of the MagicaVoxel .vox binary format.
 * The format specification is publicly documented at:
 *   https://github.com/ephtracy/voxel-model
 * This implementation is entirely original C99 code.
 */
#include "vox_loader.h"
#include "../core/log.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── Low-level reader helpers ────────────────────────────────────────── */

static bool read_u32(FILE *f, u32 *out) {
    return fread(out, 4, 1, f) == 1;
}
static bool read_bytes(FILE *f, void *buf, size_t n) {
    return fread(buf, 1, n, f) == n;
}
static bool read_str(FILE *f, char *buf, int len) {
    /* .vox stores length-prefixed strings without null terminators */
    u32 sz = 0;
    if (!read_u32(f, &sz)) return false;
    if ((int)sz >= len) { fseek(f, (long)sz, SEEK_CUR); return false; }
    if (!read_bytes(f, buf, sz)) return false;
    buf[sz] = '\0';
    return true;
}

/* ── Fallback palette (procedural, no third-party data) ─────────────── */

static void palette_from_mv_default(VoxelPalette *pal) {
    /*
     * When a .vox file has no RGBA chunk we build a simple procedural
     * palette rather than embedding any third-party colour data.
     * Uses vfe_palette_default() from voxel_data.c which generates
     * the VFE natural palette from scratch.
     */
    vfe_palette_default(pal);
}

/* ── Chunk IDs ───────────────────────────────────────────────────────── */
#define CID(a,b,c,d) ((u32)(a)|((u32)(b)<<8)|((u32)(c)<<16)|((u32)(d)<<24))
#define CHUNK_MAIN CID('M','A','I','N')
#define CHUNK_SIZE CID('S','I','Z','E')
#define CHUNK_XYZI CID('X','Y','Z','I')
#define CHUNK_RGBA CID('R','G','B','A')

/* ── Loader ─────────────────────────────────────────────────────────── */

VoxelGrid *vfe_vox_load(const char *path, VoxelPalette *pal) {
    FILE *f = fopen(path, "rb");
    if (!f) { VFE_ERROR("vfe_vox_load: cannot open '%s'", path); return NULL; }

    /* Magic + version */
    char magic[4];
    u32  version = 0;
    if (!read_bytes(f, magic, 4) || memcmp(magic, "VOX ", 4) != 0) {
        VFE_ERROR("vfe_vox_load: not a .vox file: '%s'", path);
        fclose(f); return NULL;
    }
    read_u32(f, &version);

    /* Use MagicaVoxel default palette until an RGBA chunk is found */
    palette_from_mv_default(pal);

    VoxelGrid *grid = NULL;
    u32 gw = 0, gh = 0, gd = 0;
    u32 nvox = 0;
    u8 *vox_buf = NULL;

    /* Walk chunks */
    long file_end;
    fseek(f, 0, SEEK_END); file_end = ftell(f);
    fseek(f, 8, SEEK_SET); /* skip past magic + version */

    while (ftell(f) < file_end) {
        u32 chunk_id, chunk_bytes, child_bytes;
        if (!read_u32(f, &chunk_id))   break;
        if (!read_u32(f, &chunk_bytes)) break;
        if (!read_u32(f, &child_bytes)) break;
        long chunk_end = ftell(f) + (long)chunk_bytes;

        if (chunk_id == CHUNK_SIZE) {
            read_u32(f, &gw);
            read_u32(f, &gh);
            read_u32(f, &gd);
        } else if (chunk_id == CHUNK_XYZI) {
            read_u32(f, &nvox);
            vox_buf = (u8 *)malloc((size_t)nvox * 4);
            if (vox_buf) read_bytes(f, vox_buf, (size_t)nvox * 4);
        } else if (chunk_id == CHUNK_RGBA) {
            /* 256 RGBA entries (index 0 unused in MV, so shift by +1) */
            u8 tmp[256 * 4];
            read_bytes(f, tmp, sizeof(tmp));
            for (int i = 0; i < 255; i++) {
                pal->colors[i+1].r = tmp[i*4 + 0];
                pal->colors[i+1].g = tmp[i*4 + 1];
                pal->colors[i+1].b = tmp[i*4 + 2];
                pal->colors[i+1].a = tmp[i*4 + 3];
            }
            pal->colors[0] = (Color8){0,0,0,0};
        }
        fseek(f, chunk_end, SEEK_SET);
    }
    fclose(f);

    /* Build grid */
    if (gw > 0 && gh > 0 && gd > 0 && vox_buf) {
        grid = vfe_grid_create((u16)gw, (u16)gh, (u16)gd);
        if (grid) {
            for (u32 i = 0; i < nvox; i++) {
                u8 x = vox_buf[i*4+0];
                u8 y = vox_buf[i*4+1];
                u8 z = vox_buf[i*4+2];
                u8 c = vox_buf[i*4+3];
                vfe_grid_set(grid, x, z, y, c); /* swap Y/Z for engine coords */
            }
        }
    }
    free(vox_buf);
    if (!grid) VFE_ERROR("vfe_vox_load: no usable data in '%s'", path);
    return grid;
}

/* ── Saver ──────────────────────────────────────────────────────────── */

bool vfe_vox_save(const VoxelGrid *grid, const VoxelPalette *pal,
                  const char *path) {
    if (!grid || !path) return false;

    /* Count non-empty voxels */
    u32 total = (u32)grid->w * grid->h * grid->d;
    u32 nvox  = 0;
    for (u32 i = 0; i < total; i++) if (grid->data[i]) nvox++;

    FILE *f = fopen(path, "wb");
    if (!f) { VFE_ERROR("vfe_vox_save: cannot create '%s'", path); return false; }

    /* Header */
    fwrite("VOX ", 1, 4, f);
    u32 ver = 150; fwrite(&ver, 4, 1, f);

    /* SIZE chunk = 12 bytes */
    u32 size_id = CHUNK_SIZE;
    u32 sz_bytes = 12, sz_child = 0;
    fwrite(&size_id, 4,1,f); fwrite(&sz_bytes,4,1,f); fwrite(&sz_child,4,1,f);
    u32 uw=grid->w, uh=grid->h, ud=grid->d;
    fwrite(&uw,4,1,f); fwrite(&uh,4,1,f); fwrite(&ud,4,1,f);

    /* XYZI chunk */
    u32 xyzi_id = CHUNK_XYZI;
    u32 xyzi_bytes = 4 + nvox * 4, xyzi_child = 0;
    fwrite(&xyzi_id,4,1,f); fwrite(&xyzi_bytes,4,1,f); fwrite(&xyzi_child,4,1,f);
    fwrite(&nvox, 4, 1, f);
    for (u32 z = 0; z < grid->d; z++)
        for (u32 y = 0; y < grid->h; y++)
            for (u32 x = 0; x < grid->w; x++) {
                u8 c = vfe_grid_get(grid, (i32)x, (i32)y, (i32)z);
                if (!c) continue;
                u8 v[4] = {(u8)x, (u8)z, (u8)y, c}; /* swap back to MV coords */
                fwrite(v, 1, 4, f);
            }

    /* RGBA chunk */
    u32 rgba_id = CHUNK_RGBA;
    u32 rgba_bytes = 256*4, rgba_child = 0;
    fwrite(&rgba_id,4,1,f); fwrite(&rgba_bytes,4,1,f); fwrite(&rgba_child,4,1,f);
    u8 palette_bytes[256*4];
    for (int i = 0; i < 255; i++) {
        palette_bytes[i*4+0] = pal->colors[i+1].r;
        palette_bytes[i*4+1] = pal->colors[i+1].g;
        palette_bytes[i*4+2] = pal->colors[i+1].b;
        palette_bytes[i*4+3] = pal->colors[i+1].a;
    }
    memset(palette_bytes + 255*4, 0, 4);
    fwrite(palette_bytes, 1, 256*4, f);

    fclose(f);
    VFE_INFO("vfe_vox_save: wrote '%s' (%u voxels)", path, nvox);
    return true;
}
