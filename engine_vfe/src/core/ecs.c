/* VoxelForge Engine (VFE) — ECS implementation  */
#include "ecs.h"
#include "log.h"
#include <stdlib.h>
#include <string.h>
#include <assert.h>

/* ── World lifecycle ────────────────────────────────────────────────── */

World *vfe_world_create(void) {
    World *w = (World *)calloc(1, sizeof(World));
    if (!w) { VFE_ERROR("vfe_world_create: out of memory"); return NULL; }

    /* Pre-register built-in component pools */
    vfe_register_component(w, "Transform",   sizeof(TransformComponent));
    vfe_register_component(w, "VoxelModel",  sizeof(VoxelModelComponent));
    vfe_register_component(w, "RigidBody",   sizeof(RigidBodyComponent));
    vfe_register_component(w, "PointLight",  sizeof(PointLightComponent));
    vfe_register_component(w, "Camera",      sizeof(CameraComponent));
    vfe_register_component(w, "Script",      sizeof(ScriptComponent));
    vfe_register_component(w, "Animation",   sizeof(AnimationComponent));
    vfe_register_component(w, "Audio",       sizeof(AudioComponent));
    vfe_register_component(w, "Tag",         sizeof(TagComponent));

    /* Seed the free-list with IDs 1..VFE_MAX_ENTITIES-1
     * (0 is reserved as VFE_INVALID_ENTITY) */
    for (u32 i = VFE_MAX_ENTITIES - 1; i >= 1; i--) {
        w->free_list[w->free_head++] = (EntityID)i;
    }

    VFE_INFO("World created — capacity %u entities, %u component types",
             VFE_MAX_ENTITIES, VFE_MAX_COMPONENTS);
    return w;
}

void vfe_world_destroy(World *w) {
    if (!w) return;
    for (u32 i = 0; i < w->pool_count; i++) {
        free(w->pools[i].data);
        w->pools[i].data = NULL;
    }
    free(w);
}

/* ── Component registration ─────────────────────────────────────────── */

ComponentID vfe_register_component(World *w, const char *name, size_t size) {
    assert(w && name);
    if (w->pool_count >= VFE_MAX_COMPONENTS) {
        VFE_ERROR("vfe_register_component: reached max %u types", VFE_MAX_COMPONENTS);
        return (ComponentID)255;
    }
    ComponentID id = (ComponentID)w->pool_count++;
    ComponentPool *pool = &w->pools[id];

    pool->data   = calloc(VFE_MAX_ENTITIES, size);
    pool->stride = size;
    strncpy(pool->name, name, sizeof(pool->name) - 1);
    memset(pool->active, 0, sizeof(pool->active));

    if (!pool->data) {
        VFE_ERROR("vfe_register_component: OOM for '%s'", name);
        return (ComponentID)255;
    }
    VFE_DEBUG("Registered component[%u] '%s' (stride=%zu)", id, name, size);
    return id;
}

/* ── Entity operations ──────────────────────────────────────────────── */

EntityID vfe_entity_create(World *w) {
    assert(w);
    if (w->free_head == 0) {
        VFE_ERROR("vfe_entity_create: entity pool exhausted (%u max)", VFE_MAX_ENTITIES);
        return VFE_INVALID_ENTITY;
    }
    EntityID id = w->free_list[--w->free_head];
    EntityRecord *rec = &w->entities[id];
    memset(rec, 0, sizeof(*rec));
    rec->alive  = true;
    rec->parent = VFE_INVALID_ENTITY;
    w->entity_count++;
    if (id > w->highest_id) w->highest_id = id;
    return id;
}

void vfe_entity_destroy(World *w, EntityID id) {
    assert(w && id > 0 && id < VFE_MAX_ENTITIES);
    if (!w->entities[id].alive) return;

    /* Remove all components */
    for (ComponentID c = 0; c < (ComponentID)w->pool_count; c++) {
        if (VFE_MASK_HAS(w->entities[id].mask, c)) {
            w->pools[c].active[id] = false;
        }
    }
    /* Unlink from parent's child list */
    EntityID parent = w->entities[id].parent;
    if (parent != VFE_INVALID_ENTITY) {
        EntityID *cursor = &w->entities[parent].first_child;
        while (*cursor != VFE_INVALID_ENTITY && *cursor != id) {
            cursor = &w->entities[*cursor].next_sibling;
        }
        if (*cursor == id) *cursor = w->entities[id].next_sibling;
    }
    /* Recurse into children */
    EntityID child = w->entities[id].first_child;
    while (child != VFE_INVALID_ENTITY) {
        EntityID next = w->entities[child].next_sibling;
        w->entities[child].parent = VFE_INVALID_ENTITY;
        vfe_entity_destroy(w, child);
        child = next;
    }

    w->entities[id].alive = false;
    w->entities[id].mask  = 0;
    w->free_list[w->free_head++] = id;
    w->entity_count--;
}

bool vfe_entity_alive(const World *w, EntityID id) {
    if (!w || id == VFE_INVALID_ENTITY || id >= VFE_MAX_ENTITIES) return false;
    return w->entities[id].alive;
}

void vfe_entity_set_parent(World *w, EntityID child, EntityID parent) {
    assert(w && vfe_entity_alive(w, child));
    EntityRecord *crec = &w->entities[child];
    /* Remove from old parent */
    if (crec->parent != VFE_INVALID_ENTITY) {
        EntityID *cur = &w->entities[crec->parent].first_child;
        while (*cur != VFE_INVALID_ENTITY && *cur != child)
            cur = &w->entities[*cur].next_sibling;
        if (*cur == child) *cur = crec->next_sibling;
    }
    crec->parent = parent;
    crec->next_sibling = VFE_INVALID_ENTITY;
    if (parent != VFE_INVALID_ENTITY) {
        crec->next_sibling = w->entities[parent].first_child;
        w->entities[parent].first_child = child;
    }
}

EntityID vfe_entity_get_parent(const World *w, EntityID id) {
    if (!vfe_entity_alive(w, id)) return VFE_INVALID_ENTITY;
    return w->entities[id].parent;
}

/* ── Component operations ───────────────────────────────────────────── */

void *vfe_comp_add(World *w, EntityID id, ComponentID cid) {
    assert(w && vfe_entity_alive(w, id) && cid < w->pool_count);
    ComponentPool *pool = &w->pools[cid];
    pool->active[id] = true;
    w->entities[id].mask = VFE_MASK_ADD(w->entities[id].mask, cid);
    void *ptr = (u8 *)pool->data + (size_t)id * pool->stride;
    memset(ptr, 0, pool->stride);
    return ptr;
}

void vfe_comp_rem(World *w, EntityID id, ComponentID cid) {
    assert(w && vfe_entity_alive(w, id) && cid < w->pool_count);
    w->pools[cid].active[id] = false;
    w->entities[id].mask = VFE_MASK_REM(w->entities[id].mask, cid);
}

void *vfe_comp_get(World *w, EntityID id, ComponentID cid) {
    if (!w || !vfe_entity_alive(w, id) || cid >= w->pool_count) return NULL;
    if (!w->pools[cid].active[id]) return NULL;
    return (u8 *)w->pools[cid].data + (size_t)id * w->pools[cid].stride;
}

bool vfe_comp_has(const World *w, EntityID id, ComponentID cid) {
    if (!w || !vfe_entity_alive(w, id) || cid >= w->pool_count) return false;
    return w->pools[cid].active[id];
}

/* ── System management ──────────────────────────────────────────────── */

static int system_cmp(const void *a, const void *b) {
    return ((SystemDescriptor *)a)->priority -
           ((SystemDescriptor *)b)->priority;
}

SystemID vfe_system_register(World *w, const SystemDescriptor *desc) {
    assert(w && desc);
    if (w->system_count >= VFE_MAX_SYSTEMS) {
        VFE_ERROR("vfe_system_register: max systems reached");
        return (SystemID)255;
    }
    SystemID id = (SystemID)w->system_count++;
    w->systems[id] = *desc;
    /* Keep sorted by priority */
    qsort(w->systems, w->system_count, sizeof(SystemDescriptor), system_cmp);
    VFE_DEBUG("Registered system '%s' (priority=%d)", desc->name, desc->priority);
    return id;
}

void vfe_system_enable(World *w, SystemID id, bool enabled) {
    if (id < w->system_count) w->systems[id].enabled = enabled;
}

void vfe_world_init_systems(World *w) {
    for (u32 i = 0; i < w->system_count; i++) {
        if (w->systems[i].enabled && w->systems[i].init)
            w->systems[i].init();
    }
}

void vfe_world_update_systems(World *w) {
    for (u32 i = 0; i < w->system_count; i++) {
        if (w->systems[i].enabled && w->systems[i].update)
            w->systems[i].update();
    }
}

void vfe_world_shutdown_systems(World *w) {
    /* Shutdown in reverse order */
    for (i32 i = (i32)w->system_count - 1; i >= 0; i--) {
        if (w->systems[i].shutdown)
            w->systems[i].shutdown();
    }
}

/* ── Entity iteration ────────────────────────────────────────────────── */

void vfe_foreach_entity(World *w, ComponentMask required,
                         ComponentMask excluded,
                         EntityIterFn cb, void *userdata) {
    for (EntityID id = 1; id <= w->highest_id; id++) {
        if (!w->entities[id].alive) continue;
        ComponentMask m = w->entities[id].mask;
        if ((m & required) != required)   continue;
        if ((m & excluded) != 0)           continue;
        cb(w, id, userdata);
    }
}

/* ── Tag queries ─────────────────────────────────────────────────────── */

EntityID vfe_find_by_name(World *w, const char *name) {
    ComponentPool *pool = &w->pools[VFE_COMP_TAG];
    for (EntityID id = 1; id <= w->highest_id; id++) {
        if (!pool->active[id]) continue;
        TagComponent *tag = (TagComponent *)((u8 *)pool->data +
                             (size_t)id * pool->stride);
        if (strncmp(tag->name, name, sizeof(tag->name)) == 0)
            return id;
    }
    return VFE_INVALID_ENTITY;
}

u32 vfe_find_by_group(World *w, const char *group,
                       EntityID *out, u32 out_max) {
    ComponentPool *pool = &w->pools[VFE_COMP_TAG];
    u32 count = 0;
    for (EntityID id = 1; id <= w->highest_id && count < out_max; id++) {
        if (!pool->active[id]) continue;
        TagComponent *tag = (TagComponent *)((u8 *)pool->data +
                             (size_t)id * pool->stride);
        if (strncmp(tag->group, group, sizeof(tag->group)) == 0)
            out[count++] = id;
    }
    return count;
}
