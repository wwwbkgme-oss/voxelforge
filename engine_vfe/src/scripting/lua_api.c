/* VFE — Lua API bindings  (original C99)
 * Exposes the engine's C API to Lua scripts running inside entities.
 * All functions follow the Lua C API calling convention.
 */
#include "lua_api.h"
#include "../core/log.h"
#include "../physics/physics.h"
#include <string.h>
#include <math.h>

/* Helper: fetch VFE_LuaVM from Lua registry */
static VFE_LuaVM *get_vm(lua_State *L) {
    lua_getfield(L, LUA_REGISTRYINDEX, "vfe_vm");
    VFE_LuaVM *vm = (VFE_LuaVM *)lua_touserdata(L, -1);
    lua_pop(L, 1);
    return vm;
}

/* ── Transform API ─────────────────────────────────────────────────── */

static int l_transform_get_pos(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    TransformComponent *t = VFE_TRANSFORM(vm->world, id);
    if (!t) { lua_pushnil(L); return 1; }
    lua_newtable(L);
    lua_pushnumber(L, t->position.x); lua_setfield(L, -2, "x");
    lua_pushnumber(L, t->position.y); lua_setfield(L, -2, "y");
    lua_pushnumber(L, t->position.z); lua_setfield(L, -2, "z");
    return 1;
}

static int l_transform_set_pos(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    float x = (float)luaL_checknumber(L, 2);
    float y = (float)luaL_checknumber(L, 3);
    float z = (float)luaL_checknumber(L, 4);
    TransformComponent *t = VFE_TRANSFORM(vm->world, id);
    if (t) { t->position.x = x; t->position.y = y; t->position.z = z; }
    return 0;
}

static int l_transform_move(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    float dx = (float)luaL_checknumber(L, 2);
    float dy = (float)luaL_checknumber(L, 3);
    float dz = (float)luaL_checknumber(L, 4);
    TransformComponent *t = VFE_TRANSFORM(vm->world, id);
    if (t) { t->position.x+=dx; t->position.y+=dy; t->position.z+=dz; }
    return 0;
}

/* ── RigidBody API ─────────────────────────────────────────────────── */

static int l_rb_get_vel(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    RigidBodyComponent *rb = VFE_RIGIDBODY(vm->world, id);
    if (!rb) { lua_pushnil(L); return 1; }
    lua_newtable(L);
    lua_pushnumber(L, rb->velocity.x); lua_setfield(L, -2, "x");
    lua_pushnumber(L, rb->velocity.y); lua_setfield(L, -2, "y");
    lua_pushnumber(L, rb->velocity.z); lua_setfield(L, -2, "z");
    return 1;
}

static int l_rb_set_vel(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    float x=(float)luaL_checknumber(L,2),
          y=(float)luaL_checknumber(L,3),
          z=(float)luaL_checknumber(L,4);
    RigidBodyComponent *rb = VFE_RIGIDBODY(vm->world, id);
    if (rb) { rb->velocity.x=x; rb->velocity.y=y; rb->velocity.z=z; }
    return 0;
}

static int l_rb_apply_impulse(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    float x=(float)luaL_checknumber(L,2),
          y=(float)luaL_checknumber(L,3),
          z=(float)luaL_checknumber(L,4);
    RigidBodyComponent *rb = VFE_RIGIDBODY(vm->world, id);
    if (rb && rb->mass > 0) {
        rb->velocity.x += x / rb->mass;
        rb->velocity.y += y / rb->mass;
        rb->velocity.z += z / rb->mass;
    }
    return 0;
}

/* ── Entity API ────────────────────────────────────────────────────── */

static int l_entity_create(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = vfe_entity_create(vm->world);
    /* Always add a transform */
    vfe_comp_add(vm->world, id, VFE_COMP_TRANSFORM);
    TransformComponent *t = VFE_TRANSFORM(vm->world, id);
    if (t) { t->scale.x=t->scale.y=t->scale.z=1.0f; }
    lua_pushinteger(L, (lua_Integer)id);
    return 1;
}

static int l_entity_destroy(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    vfe_entity_destroy(vm->world, id);
    return 0;
}

static int l_entity_find_by_name(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    const char *name = luaL_checkstring(L, 1);
    EntityID id = vfe_find_by_name(vm->world, name);
    if (id == VFE_INVALID_ENTITY) lua_pushnil(L);
    else lua_pushinteger(L, (lua_Integer)id);
    return 1;
}

static int l_entity_find_by_group(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    const char *group = luaL_checkstring(L, 1);
    EntityID ids[256];
    u32 n = vfe_find_by_group(vm->world, group, ids, 256);
    lua_newtable(L);
    for (u32 i = 0; i < n; i++) {
        lua_pushinteger(L, (lua_Integer)i+1);
        lua_pushinteger(L, (lua_Integer)ids[i]);
        lua_settable(L, -3);
    }
    return 1;
}

static int l_entity_get_tag(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    TagComponent *tag = VFE_TAG(vm->world, id);
    if (!tag) { lua_pushstring(L, ""); return 1; }
    lua_pushstring(L, tag->name);
    return 1;
}

static int l_entity_set_tag(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id   = (EntityID)luaL_checkinteger(L, 1);
    const char *n = luaL_checkstring(L, 2);
    const char *g = luaL_optstring(L, 3, "");
    if (!vfe_comp_has(vm->world, id, VFE_COMP_TAG))
        vfe_comp_add(vm->world, id, VFE_COMP_TAG);
    TagComponent *tag = VFE_TAG(vm->world, id);
    if (tag) {
        strncpy(tag->name,  n, sizeof(tag->name)-1);
        strncpy(tag->group, g, sizeof(tag->group)-1);
    }
    return 0;
}

/* ── PointLight API ────────────────────────────────────────────────── */

static int l_light_set(lua_State *L) {
    VFE_LuaVM *vm = get_vm(L);
    EntityID id = (EntityID)luaL_checkinteger(L, 1);
    float r=(float)luaL_optnumber(L,2,1), g=(float)luaL_optnumber(L,3,1),
          b=(float)luaL_optnumber(L,4,1), intensity=(float)luaL_optnumber(L,5,1),
          radius=(float)luaL_optnumber(L,6,10);
    if (!vfe_comp_has(vm->world, id, VFE_COMP_POINT_LIGHT))
        vfe_comp_add(vm->world, id, VFE_COMP_POINT_LIGHT);
    PointLightComponent *pl = VFE_LIGHT(vm->world, id);
    if (pl) {
        pl->color=(Vec3){r,g,b}; pl->intensity=intensity; pl->radius=radius;
    }
    return 0;
}

/* ── Math helpers ──────────────────────────────────────────────────── */

static int l_math_dist(lua_State *L) {
    float ax=(float)luaL_checknumber(L,1), ay=(float)luaL_checknumber(L,2),
          az=(float)luaL_checknumber(L,3), bx=(float)luaL_checknumber(L,4),
          by=(float)luaL_checknumber(L,5), bz=(float)luaL_checknumber(L,6);
    float dx=bx-ax, dy=by-ay, dz=bz-az;
    lua_pushnumber(L, (lua_Number)sqrtf(dx*dx+dy*dy+dz*dz));
    return 1;
}

static int l_math_lerp(lua_State *L) {
    float a=(float)luaL_checknumber(L,1), b=(float)luaL_checknumber(L,2),
          t=(float)luaL_checknumber(L,3);
    lua_pushnumber(L, (lua_Number)(a + (b-a)*t));
    return 1;
}

/* ── Log API ───────────────────────────────────────────────────────── */

static int l_log_info (lua_State *L){ VFE_INFO ("%s", luaL_checkstring(L,1)); return 0; }
static int l_log_warn (lua_State *L){ VFE_WARN ("%s", luaL_checkstring(L,1)); return 0; }
static int l_log_error(lua_State *L){ VFE_ERROR("%s", luaL_checkstring(L,1)); return 0; }

/* ── Registration ──────────────────────────────────────────────────── */

#define REG(name, fn) { lua_pushcfunction(L, fn); lua_setfield(L, -2, name); }

void vfe_lua_register_api(VFE_LuaVM *vm) {
    lua_State *L = vm->L;

    /* Transform table */
    lua_newtable(L);
    REG("GetPosition",  l_transform_get_pos);
    REG("SetPosition",  l_transform_set_pos);
    REG("Move",         l_transform_move);
    lua_setglobal(L, "Transform");

    /* RigidBody table */
    lua_newtable(L);
    REG("GetVelocity",  l_rb_get_vel);
    REG("SetVelocity",  l_rb_set_vel);
    REG("ApplyImpulse", l_rb_apply_impulse);
    lua_setglobal(L, "RigidBody");

    /* Entity table */
    lua_newtable(L);
    REG("Create",           l_entity_create);
    REG("Destroy",          l_entity_destroy);
    REG("FindByName",       l_entity_find_by_name);
    REG("FindByGroup",      l_entity_find_by_group);
    REG("GetTag",           l_entity_get_tag);
    REG("SetTag",           l_entity_set_tag);
    lua_setglobal(L, "Entity");

    /* Light table */
    lua_newtable(L);
    REG("Set", l_light_set);
    lua_setglobal(L, "Light");

    /* Math table (extends Lua's built-in math) */
    lua_getglobal(L, "math");
    REG("dist3", l_math_dist);
    REG("lerp",  l_math_lerp);
    lua_pop(L, 1);

    /* Log table */
    lua_newtable(L);
    REG("info",  l_log_info);
    REG("warn",  l_log_warn);
    REG("error", l_log_error);
    lua_setglobal(L, "Log");

    VFE_DEBUG("Lua API registered");
}
