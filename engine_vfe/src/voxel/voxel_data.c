/* VFE — Voxel data implementation */
#include "voxel_data.h"
#include "vox_loader.h"
#include "mesher.h"
#include "../core/log.h"
#include <stdlib.h>
#include <string.h>
#include <GL/glew.h>

/* ── Palette ─────────────────────────────────────────────────────────── */

void vfe_palette_default(VoxelPalette *pal) {
    /* Index 0 = air (transparent) */
    pal->colors[0] = (Color8){0, 0, 0, 0};
    /* Greens (1-20) */
    for (int i = 1; i <= 20; i++) {
        pal->colors[i] = (Color8){(u8)(30 + i*2), (u8)(80 + i*7), (u8)(20 + i*2), 255};
    }
    /* Browns (21-40) */
    for (int i = 0; i < 20; i++) {
        pal->colors[21+i] = (Color8){(u8)(100+i*5), (u8)(60+i*3), (u8)(20+i*2), 255};
    }
    /* Greys/stone (41-60) */
    for (int i = 0; i < 20; i++) {
        u8 v = (u8)(80 + i * 8);
        pal->colors[41+i] = (Color8){v, v, v, 255};
    }
    /* Blues/water (61-80) */
    for (int i = 0; i < 20; i++) {
        pal->colors[61+i] = (Color8){(u8)(20+i*3), (u8)(60+i*4), (u8)(180+i), 255};
    }
    /* Reds/warm (81-100) */
    for (int i = 0; i < 20; i++) {
        pal->colors[81+i] = (Color8){(u8)(180+i*3), (u8)(60+i*3), (u8)(40+i*2), 255};
    }
    /* Yellows (101-120) */
    for (int i = 0; i < 20; i++) {
        u8 v = (u8)(200 + i);
        pal->colors[101+i] = (Color8){v, (u8)(v - 20), (u8)(80 + i*2), 255};
    }
    /* Whites (121-130) */
    for (int i = 0; i < 10; i++) {
        u8 v = (u8)(220 + i*3);
        pal->colors[121+i] = (Color8){v, v, (u8)(v+5), 255};
    }
    /* Remainder — procedural variation */
    for (int i = 131; i < 256; i++) {
        pal->colors[i] = (Color8){
            (u8)((i * 37) % 256),
            (u8)((i * 83) % 256),
            (u8)((i * 151) % 256),
            255
        };
    }
}

void vfe_palette_to_tex1d(const VoxelPalette *pal, unsigned int *tex_id) {
    if (*tex_id == 0) glGenTextures(1, tex_id);
    glBindTexture(GL_TEXTURE_1D, *tex_id);
    glTexImage1D(GL_TEXTURE_1D, 0, GL_RGBA8, VFE_PALETTE_SIZE, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, pal->colors);
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_1D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glBindTexture(GL_TEXTURE_1D, 0);
}

/* ── VoxelGrid ───────────────────────────────────────────────────────── */

VoxelGrid *vfe_grid_create(u16 w, u16 h, u16 d) {
    VoxelGrid *g = (VoxelGrid *)calloc(1, sizeof(VoxelGrid));
    if (!g) return NULL;
    g->data = (u8 *)calloc((size_t)w * h * d, 1);
    if (!g->data) { free(g); return NULL; }
    g->w = w;  g->h = h;  g->d = d;
    g->pivot = (Vec3){ w * 0.5f, h * 0.5f, d * 0.5f };
    g->dirty = true;
    return g;
}

void vfe_grid_destroy(VoxelGrid *g) {
    if (!g) return;
    free(g->data);
    free(g);
}

u32 vfe_grid_voxel_count(const VoxelGrid *g) {
    if (!g) return 0;
    u32 count = 0;
    u32 total = (u32)g->w * g->h * g->d;
    for (u32 i = 0; i < total; i++) if (g->data[i] != 0) count++;
    return count;
}

void vfe_grid_fill(VoxelGrid *g, u8 color) {
    memset(g->data, color, (size_t)g->w * g->h * g->d);
    g->dirty = true;
}

void vfe_grid_fill_box(VoxelGrid *g,
                        i32 x0, i32 y0, i32 z0,
                        i32 x1, i32 y1, i32 z1, u8 color) {
    for (i32 z = z0; z <= z1; z++)
        for (i32 y = y0; y <= y1; y++)
            for (i32 x = x0; x <= x1; x++)
                vfe_grid_set(g, x, y, z, color);
}

/* ── VoxelModelAsset ─────────────────────────────────────────────────── */

VoxelModelAsset *vfe_asset_load_vox(const char *path) {
    VoxelModelAsset *a = (VoxelModelAsset *)calloc(1, sizeof(VoxelModelAsset));
    if (!a) return NULL;
    strncpy(a->path, path, sizeof(a->path)-1);

    a->grid = vfe_vox_load(path, &a->palette);
    if (!a->grid) {
        VFE_WARN("vfe_asset_load_vox: failed to load '%s'", path);
        free(a);
        return NULL;
    }

    /* Build GPU buffers */
    glGenVertexArrays(1, &a->vao);
    glGenBuffers(3, a->vbo);
    vfe_asset_rebuild(a);
    a->loaded = true;
    VFE_INFO("Loaded vox asset '%s' (%ux%ux%u, %u voxels)",
             path, a->grid->w, a->grid->h, a->grid->d,
             vfe_grid_voxel_count(a->grid));
    return a;
}

void vfe_asset_unload(VoxelModelAsset *a) {
    if (!a) return;
    if (a->vao)    { glDeleteVertexArrays(1, &a->vao); a->vao = 0; }
    if (a->vbo[0]) { glDeleteBuffers(3, a->vbo); memset(a->vbo, 0, sizeof(a->vbo)); }
    vfe_grid_destroy(a->grid);
    free(a);
}

bool vfe_asset_rebuild(VoxelModelAsset *a) {
    if (!a || !a->grid) return false;
    MeshData mesh = {0};
    vfe_mesh_greedy(a->grid, &mesh);

    glBindVertexArray(a->vao);

    /* positions */
    glBindBuffer(GL_ARRAY_BUFFER, a->vbo[0]);
    glBufferData(GL_ARRAY_BUFFER,
                 (GLsizeiptr)(mesh.vert_count * sizeof(Vec3)),
                 mesh.positions, GL_DYNAMIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, NULL);

    /* normals + AO packed as Vec3 */
    glBindBuffer(GL_ARRAY_BUFFER, a->vbo[1]);
    glBufferData(GL_ARRAY_BUFFER,
                 (GLsizeiptr)(mesh.vert_count * sizeof(Vec3)),
                 mesh.normals, GL_DYNAMIC_DRAW);
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, NULL);

    /* colour index (0-255) stored as float */
    glBindBuffer(GL_ARRAY_BUFFER, a->vbo[2]);
    glBufferData(GL_ARRAY_BUFFER,
                 (GLsizeiptr)(mesh.vert_count * sizeof(f32)),
                 mesh.colors, GL_DYNAMIC_DRAW);
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 1, GL_FLOAT, GL_FALSE, 0, NULL);

    glBindVertexArray(0);

    a->vert_count  = mesh.vert_count;
    a->mesh_dirty  = false;
    a->grid->dirty = false;

    vfe_mesh_free(&mesh);
    return true;
}
