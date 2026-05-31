/*
 * VFE — Greedy Mesh algorithm for voxel geometry
 *
 * Reduces a voxel grid into a minimal set of quads by merging
 * adjacent same-coloured faces into rectangles.  Produces positions,
 * normals, and per-vertex colour indices ready for OpenGL.
 */
#pragma once
#ifndef VFE_MESHER_H
#define VFE_MESHER_H

#include "voxel_data.h"

typedef struct {
    Vec3  *positions;   /* 6 verts per quad (2 triangles)        */
    Vec3  *normals;     /* face normal for each vertex            */
    f32   *colors;      /* palette index (0-255) as float         */
    u32    vert_count;
    u32    capacity;
} MeshData;

void vfe_mesh_greedy(const VoxelGrid *grid, MeshData *out);
void vfe_mesh_free  (MeshData *m);
#endif
