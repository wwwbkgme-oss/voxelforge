/*
 * VoxelForge Engine (VFE) — Entity Component System
 *
 * Data-oriented ECS.  Components are stored in flat contiguous arrays
 * (Structure-of-Arrays), one array per component type, indexed by EntityID.
 * This gives O(1) component access, excellent cache behaviour for systems
 * that iterate over all entities, and simple deterministic entity handles.
 *
 * Limits (tuneable via #define):
 *   VFE_MAX_ENTITIES    4096
 *   VFE_MAX_COMPONENTS  32
 *   VFE_MAX_SYSTEMS     64
 */
#pragma once
#ifndef VFE_ECS_H
#define VFE_ECS_H

#include "types.h"
#include <stddef.h>

/* ══════════════════════════════════════════════════════════════════════
 * Built-in component IDs  (0-based; add your own after VFE_COMP__COUNT)
 * ══════════════════════════════════════════════════════════════════════ */
typedef enum {
    VFE_COMP_TRANSFORM    = 0,
    VFE_COMP_VOXEL_MODEL  = 1,
    VFE_COMP_RIGID_BODY   = 2,
    VFE_COMP_POINT_LIGHT  = 3,
    VFE_COMP_CAMERA       = 4,
    VFE_COMP_SCRIPT       = 5,
    VFE_COMP_ANIMATION    = 6,
    VFE_COMP_AUDIO        = 7,
    VFE_COMP_TAG          = 8,   /* free-text name tag                 */
    VFE_COMP__BUILTIN_COUNT = 9,
    VFE_COMP__COUNT = VFE_MAX_COMPONENTS
} BuiltinComponentID;

/* ══════════════════════════════════════════════════════════════════════
 * Component data structures
 * ══════════════════════════════════════════════════════════════════════ */

typedef struct {
    Vec3 position;  /* world-space position                              */
    Vec3 rotation;  /* Euler angles (degrees, XYZ)                       */
    Vec3 scale;     /* per-axis scale; (1,1,1) = no scale                */
} TransformComponent;

/* Opaque handle to a loaded VoxelModel (see voxel/voxel_data.h) */
typedef struct VoxelModelAsset VoxelModelAsset;

typedef struct {
    VoxelModelAsset *asset;     /* loaded voxel grid; NULL = not loaded  */
    char             path[256]; /* .vox file path (relative to assets/)  */
    bool             visible;
    bool             cast_shadow;
    Vec3             mesh_offset; /* pivot offset                         */
} VoxelModelComponent;

typedef struct {
    Vec3  velocity;      /* units/second                                  */
    Vec3  acceleration;  /* external forces (gravity, etc.)               */
    f32   mass;          /* kg; 0 = kinematic (ignores forces)            */
    f32   restitution;   /* bounce coefficient [0,1]                      */
    f32   friction;      /* surface friction  [0,1]                       */
    bool  use_gravity;
    bool  is_static;     /* true = immovable collider                     */
    Vec3  half_extents;  /* AABB half-size for collision                  */
} RigidBodyComponent;

typedef struct {
    Vec3  color;         /* RGB in [0, ∞) HDR                             */
    f32   intensity;
    f32   radius;        /* attenuation cutoff distance                   */
    f32   hue_shift;     /* artistic hue rotation (degrees)               */
    bool  cast_shadow;
} PointLightComponent;

typedef enum {
    CAM_ISOMETRIC  = 0,
    CAM_TOP_DOWN   = 1,
    CAM_PERSPECTIVE= 2
} CameraMode;

typedef struct {
    CameraMode mode;
    f32  zoom;           /* isometric: tile size multiplier               */
    f32  fov_deg;        /* perspective only                               */
    f32  near_plane;
    f32  far_plane;
    bool is_active;      /* only one active camera renders                */
} CameraComponent;

typedef struct {
    char path[256];      /* Lua script path                               */
    bool loaded;
    int  lua_ref;        /* LUA_REGISTRYINDEX ref to the script table     */
} ScriptComponent;

typedef struct {
    u32  current_frame;
    u32  total_frames;
    f32  fps;
    f32  elapsed;        /* time since last frame change                  */
    bool looping;
    bool playing;
    char base_path[200]; /* base path; frames are base_path_000.vox, etc. */
} AnimationComponent;

typedef struct {
    char sfx_path[200];  /* one-shot sound effect to play                 */
    bool play_sfx;       /* set true → AudioSystem plays it once          */
    char music_path[200];
    bool play_music;
    f32  volume;         /* [0, 1]                                        */
} AudioComponent;

typedef struct {
    char name[64];       /* human-readable entity name                    */
    char group[32];      /* group tag for batch queries                   */
} TagComponent;

/* ══════════════════════════════════════════════════════════════════════
 * Component pool — one per registered component type
 * ══════════════════════════════════════════════════════════════════════ */
typedef struct {
    void  *data;          /* flat array of component structs              */
    size_t stride;        /* sizeof(component_type)                       */
    bool   active[VFE_MAX_ENTITIES]; /* is this slot in use?              */
    char   name[32];
} ComponentPool;

/* ══════════════════════════════════════════════════════════════════════
 * Entity record
 * ══════════════════════════════════════════════════════════════════════ */
typedef struct {
    ComponentMask mask;   /* which components this entity has             */
    bool          alive;
    EntityID      parent; /* 0 = no parent                                */
    EntityID      first_child;
    EntityID      next_sibling;
} EntityRecord;

/* ══════════════════════════════════════════════════════════════════════
 * System descriptor
 * ══════════════════════════════════════════════════════════════════════ */
typedef void (*SystemFn)(void);

typedef struct {
    char          name[48];
    ComponentMask required;  /* entity must have ALL of these             */
    ComponentMask excluded;  /* entity must have NONE of these            */
    SystemFn      init;
    SystemFn      update;
    SystemFn      shutdown;
    int           priority;  /* lower runs first                          */
    bool          enabled;
} SystemDescriptor;

/* ══════════════════════════════════════════════════════════════════════
 * World (ECS root)
 * ══════════════════════════════════════════════════════════════════════ */
typedef struct {
    EntityRecord    entities[VFE_MAX_ENTITIES];
    ComponentPool   pools[VFE_MAX_COMPONENTS];
    u32             pool_count;

    SystemDescriptor systems[VFE_MAX_SYSTEMS];
    u32              system_count;

    EntityID         free_list[VFE_MAX_ENTITIES];
    u32              free_head;

    u32              entity_count;
    u32              highest_id;   /* for iteration upper bound           */
} World;

/* ══════════════════════════════════════════════════════════════════════
 * API
 * ══════════════════════════════════════════════════════════════════════ */
#ifdef __cplusplus
extern "C" {
#endif

/* World lifecycle */
World *vfe_world_create(void);
void   vfe_world_destroy(World *w);

/* Component type registration */
ComponentID vfe_register_component(World *w, const char *name, size_t size);

/* Entity operations */
EntityID    vfe_entity_create(World *w);
void        vfe_entity_destroy(World *w, EntityID id);
bool        vfe_entity_alive(const World *w, EntityID id);
void        vfe_entity_set_parent(World *w, EntityID child, EntityID parent);
EntityID    vfe_entity_get_parent(const World *w, EntityID id);

/* Component operations */
void  *vfe_comp_add (World *w, EntityID id, ComponentID cid);
void   vfe_comp_rem (World *w, EntityID id, ComponentID cid);
void  *vfe_comp_get (World *w, EntityID id, ComponentID cid);
bool   vfe_comp_has (const World *w, EntityID id, ComponentID cid);

/* Convenience typed accessors (built-in components) */
#define VFE_TRANSFORM(w, e)   ((TransformComponent*)vfe_comp_get(w, e, VFE_COMP_TRANSFORM))
#define VFE_VOXEL(w, e)       ((VoxelModelComponent*)vfe_comp_get(w, e, VFE_COMP_VOXEL_MODEL))
#define VFE_RIGIDBODY(w, e)   ((RigidBodyComponent*)vfe_comp_get(w, e, VFE_COMP_RIGID_BODY))
#define VFE_LIGHT(w, e)       ((PointLightComponent*)vfe_comp_get(w, e, VFE_COMP_POINT_LIGHT))
#define VFE_CAMERA(w, e)      ((CameraComponent*)vfe_comp_get(w, e, VFE_COMP_CAMERA))
#define VFE_SCRIPT(w, e)      ((ScriptComponent*)vfe_comp_get(w, e, VFE_COMP_SCRIPT))
#define VFE_ANIMATION(w, e)   ((AnimationComponent*)vfe_comp_get(w, e, VFE_COMP_ANIMATION))
#define VFE_AUDIO(w, e)       ((AudioComponent*)vfe_comp_get(w, e, VFE_COMP_AUDIO))
#define VFE_TAG(w, e)         ((TagComponent*)vfe_comp_get(w, e, VFE_COMP_TAG))

/* System registration */
SystemID vfe_system_register(World *w, const SystemDescriptor *desc);
void     vfe_system_enable (World *w, SystemID id, bool enabled);

/* Update all enabled systems in priority order */
void vfe_world_init_systems(World *w);
void vfe_world_update_systems(World *w);
void vfe_world_shutdown_systems(World *w);

/* Iteration — callback fires for every entity matching the mask */
typedef void (*EntityIterFn)(World *w, EntityID id, void *userdata);
void vfe_foreach_entity(World *w, ComponentMask required,
                         ComponentMask excluded,
                         EntityIterFn cb, void *userdata);

/* Query by tag */
EntityID vfe_find_by_name(World *w, const char *name);
u32      vfe_find_by_group(World *w, const char *group,
                            EntityID *out, u32 out_max);

#ifdef __cplusplus
}
#endif

#endif /* VFE_ECS_H */
