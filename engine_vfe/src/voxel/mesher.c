/*
 * VFE — Greedy mesh implementation
 *
 * The greedy meshing algorithm is a well-known technique in voxel graphics.
 * This implementation is original C99 code.
 *
 * Algorithm overview (per axis-direction):
 *   1. Slice the grid into 2D masks perpendicular to each axis.
 *   2. For each slice, find connected rectangles of matching colour
 *      by sweeping rows and greedily extending runs.
 *   3. Emit two triangles per rectangle.
 * Result: far fewer triangles than naive face-per-voxel meshing.
 */
#include "mesher.h"
#include "../core/log.h"
#include <stdlib.h>
#include <string.h>

/* ── Dynamic array helpers ───────────────────────────────────────────── */

#define MESH_INITIAL_CAPACITY 4096

static bool mesh_grow(MeshData *m, u32 needed) {
    if (m->vert_count + needed <= m->capacity) return true;
    u32 new_cap = m->capacity ? m->capacity * 2 : MESH_INITIAL_CAPACITY;
    while (new_cap < m->vert_count + needed) new_cap *= 2;

    Vec3 *pos = (Vec3 *)realloc(m->positions, new_cap * sizeof(Vec3));
    Vec3 *nor = (Vec3 *)realloc(m->normals,   new_cap * sizeof(Vec3));
    f32  *col = (f32  *)realloc(m->colors,    new_cap * sizeof(f32));
    if (!pos || !nor || !col) {
        free(pos); free(nor); free(col);
        return false;
    }
    m->positions = pos;
    m->normals   = nor;
    m->colors    = col;
    m->capacity  = new_cap;
    return true;
}

/* Emit a quad (2 triangles, 6 vertices) */
static void emit_quad(MeshData *m,
                       Vec3 v0, Vec3 v1, Vec3 v2, Vec3 v3,
                       Vec3 normal, f32 color_idx) {
    if (!mesh_grow(m, 6)) return;
    u32 b = m->vert_count;
    /* Triangle 1: v0 v1 v2 */
    m->positions[b+0] = v0; m->normals[b+0] = normal; m->colors[b+0] = color_idx;
    m->positions[b+1] = v1; m->normals[b+1] = normal; m->colors[b+1] = color_idx;
    m->positions[b+2] = v2; m->normals[b+2] = normal; m->colors[b+2] = color_idx;
    /* Triangle 2: v0 v2 v3 */
    m->positions[b+3] = v0; m->normals[b+3] = normal; m->colors[b+3] = color_idx;
    m->positions[b+4] = v2; m->normals[b+4] = normal; m->colors[b+4] = color_idx;
    m->positions[b+5] = v3; m->normals[b+5] = normal; m->colors[b+5] = color_idx;
    m->vert_count += 6;
}

/* ── Face visibility mask ─────────────────────────────────────────────
 *
 * For each of the 6 face directions (+X,-X,+Y,-Y,+Z,-Z) build a 2D
 * slice mask and run the greedy algorithm on it.
 *
 * Axes:
 *   dim=0 → X axis   (faces perpendicular to X)
 *   dim=1 → Y axis
 *   dim=2 → Z axis
 */

typedef struct { i32 u, v, w; } Axes; /* u,v = slice axes; w = normal axis */

static Axes get_axes(int dim) {
    if (dim == 0) return (Axes){1, 2, 0}; /* slice in YZ, normal X */
    if (dim == 1) return (Axes){0, 2, 1}; /* slice in XZ, normal Y */
    return            (Axes){0, 1, 2};   /* slice in XY, normal Z */
}

static int dim_size(const VoxelGrid *g, int d) {
    if (d == 0) return (int)g->w;
    if (d == 1) return (int)g->h;
    return             (int)g->d;
}

static u8 grid_at(const VoxelGrid *g, i32 coords[3]) {
    return vfe_grid_get(g, coords[0], coords[1], coords[2]);
}

void vfe_mesh_greedy(const VoxelGrid *grid, MeshData *out) {
    if (!grid || !out) return;
    memset(out, 0, sizeof(*out));

    int W = (int)grid->w, H = (int)grid->h, D = (int)grid->d;
    int dims[3] = {W, H, D};
    (void)dims; /* used via dim_size() */

    /* mask[u*sv + v] = colour index of visible face, 0 = nothing */
    int max_slice = (W > H ? W : H);
    if (D > max_slice) max_slice = D;
    u8 *mask = (u8 *)malloc((size_t)max_slice * max_slice);
    if (!mask) { VFE_ERROR("mesher: out of memory"); return; }

    /* For each axis, for each forward and backward facing */
    for (int dim = 0; dim < 3; dim++) {
        Axes ax = get_axes(dim);
        int sw  = dim_size(grid, ax.u); /* slice width  */
        int sh  = dim_size(grid, ax.v); /* slice height */
        int sd  = dim_size(grid, ax.w); /* depth along normal axis */

        for (int side = 0; side < 2; side++) { /* 0=positive 1=negative */
            int normal_dir = (side == 0) ? 1 : -1;
            Vec3 face_normal = {0,0,0};
            if (ax.w == 0) face_normal.x = (f32)normal_dir;
            if (ax.w == 1) face_normal.y = (f32)normal_dir;
            if (ax.w == 2) face_normal.z = (f32)normal_dir;

            for (int w = 0; w < sd; w++) {
                /* Build mask for this slice */
                memset(mask, 0, (size_t)sw * sh);
                for (int v = 0; v < sh; v++) {
                    for (int u = 0; u < sw; u++) {
                        i32 cur[3] = {0,0,0};
                        cur[ax.u] = u; cur[ax.v] = v; cur[ax.w] = w;
                        i32 adj[3] = {cur[0], cur[1], cur[2]};
                        adj[ax.w]  = w + normal_dir;

                        u8 c_cur = grid_at(grid, cur);
                        u8 c_adj = (adj[ax.w] >= 0 && adj[ax.w] < sd)
                                   ? grid_at(grid, adj) : 0;

                        /* Visible face: current is solid, neighbour is air */
                        if (c_cur && !c_adj) {
                            mask[v * sw + u] = c_cur;
                        }
                    }
                }

                /* Greedy merge: find largest rectangle of same colour */
                for (int v0 = 0; v0 < sh; v0++) {
                    for (int u0 = 0; u0 < sw; ) {
                        u8 c = mask[v0 * sw + u0];
                        if (!c) { u0++; continue; }

                        /* Width: extend u as far as same colour */
                        int width = 1;
                        while (u0 + width < sw &&
                               mask[v0 * sw + u0 + width] == c) {
                            width++;
                        }

                        /* Height: extend v until a row doesn't fully match */
                        int height = 1;
                        bool can_extend = true;
                        while (can_extend && v0 + height < sh) {
                            for (int k = 0; k < width; k++) {
                                if (mask[(v0+height)*sw + u0+k] != c) {
                                    can_extend = false; break;
                                }
                            }
                            if (can_extend) height++;
                        }

                        /* Emit the quad */
                        Vec3 origin = {0,0,0}, du = {0,0,0}, dv = {0,0,0};
                        float fw = (float)w + (side == 0 ? 1.0f : 0.0f);
                        float fu0 = (float)u0, fv0 = (float)v0;

                        if (ax.w == 0) { origin.x = fw; origin.y = fu0; origin.z = fv0;
                                          du.y = (float)width;  dv.z = (float)height; }
                        else if (ax.w == 1) { origin.y = fw; origin.x = fu0; origin.z = fv0;
                                              du.x = (float)width;  dv.z = (float)height; }
                        else { origin.z = fw; origin.x = fu0; origin.y = fv0;
                                du.x = (float)width;  dv.y = (float)height; }

                        Vec3 v0v = origin;
                        Vec3 v1v = vec3_add(origin, du);
                        Vec3 v2v = vec3_add(vec3_add(origin, du), dv);
                        Vec3 v3v = vec3_add(origin, dv);

                        if (side == 0) {
                            emit_quad(out, v0v, v1v, v2v, v3v, face_normal, (f32)c);
                        } else {
                            emit_quad(out, v0v, v3v, v2v, v1v, face_normal, (f32)c);
                        }

                        /* Clear processed cells from mask */
                        for (int dh = 0; dh < height; dh++)
                            for (int dw = 0; dw < width; dw++)
                                mask[(v0+dh)*sw + u0+dw] = 0;

                        u0 += width;
                    }
                }
            }
        }
    }

    free(mask);
}

void vfe_mesh_free(MeshData *m) {
    if (!m) return;
    free(m->positions); free(m->normals); free(m->colors);
    memset(m, 0, sizeof(*m));
}
