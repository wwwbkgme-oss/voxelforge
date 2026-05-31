/* VFE — Scene load/save system */
#pragma once
#ifndef VFE_SCENE_H
#define VFE_SCENE_H

#include "../core/ecs.h"
#include "../voxel/voxel_data.h"

typedef struct {
    char     name[128];
    Vec3     background_color;
    Vec3     sun_direction;
    Vec3     sun_color;
    float    ambient_intensity;
    char     palette_path[256];
} SceneMetadata;

/*
 * Load a VoxelForge JSON scene file (.scene) into the World.
 * Spawns entities and attaches all components listed in the JSON.
 * Returns true on success.
 */
bool vfe_scene_load(World *w, const char *path, SceneMetadata *meta_out);

/*
 * Save the current World state to a .scene file.
 */
bool vfe_scene_save(const World *w, const SceneMetadata *meta, const char *path);

/* Clear all entities from the world */
void vfe_scene_clear(World *w);

#endif
