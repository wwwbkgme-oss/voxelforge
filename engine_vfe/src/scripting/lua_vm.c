/* VFE — Lua VM implementation (original C99) */
#include "lua_vm.h"
#include "lua_api.h"
#include "../core/log.h"
#include <string.h>
#include <stdio.h>

bool vfe_lua_init(VFE_LuaVM *vm, World *world) {
    memset(vm, 0, sizeof(*vm));
    vm->world = world;

    vm->L = luaL_newstate();
    if (!vm->L) { VFE_ERROR("luaL_newstate failed"); return false; }

    luaL_openlibs(vm->L);
    vfe_lua_register_api(vm);   /* register all VFE bindings */

    /* Store VM pointer in registry for C→Lua callbacks */
    lua_pushlightuserdata(vm->L, vm);
    lua_setfield(vm->L, LUA_REGISTRYINDEX, "vfe_vm");

    vm->initialised = true;
    VFE_INFO("Lua VM initialised (Lua %s)", LUA_VERSION);
    return true;
}

void vfe_lua_close(VFE_LuaVM *vm) {
    if (vm->L) { lua_close(vm->L); vm->L = NULL; }
    vm->initialised = false;
}

bool vfe_lua_load_script(VFE_LuaVM *vm, EntityID id) {
    if (!vm->L) return false;
    ScriptComponent *sc = VFE_SCRIPT(vm->world, id);
    if (!sc || sc->loaded) return sc ? sc->loaded : false;

    /* Expose 'self' as the entity ID for this script */
    vm->current_entity = id;
    lua_pushinteger(vm->L, (lua_Integer)id);
    lua_setglobal(vm->L, "self");

    /* Load and compile the script file */
    if (luaL_loadfile(vm->L, sc->path) != LUA_OK) {
        VFE_ERROR("Lua load '%s': %s", sc->path, lua_tostring(vm->L, -1));
        lua_pop(vm->L, 1);
        return false;
    }
    /* Execute the top-level chunk (defines functions) */
    if (lua_pcall(vm->L, 0, 0, 0) != LUA_OK) {
        VFE_ERROR("Lua exec '%s': %s", sc->path, lua_tostring(vm->L, -1));
        lua_pop(vm->L, 1);
        return false;
    }
    /* Call Start() if it exists */
    lua_getglobal(vm->L, "Start");
    if (lua_isfunction(vm->L, -1)) {
        if (lua_pcall(vm->L, 0, 0, 0) != LUA_OK) {
            VFE_WARN("Lua Start() '%s': %s", sc->path, lua_tostring(vm->L, -1));
            lua_pop(vm->L, 1);
        }
    } else {
        lua_pop(vm->L, 1);
    }

    sc->loaded = true;
    VFE_DEBUG("Loaded Lua script '%s' for entity %u", sc->path, id);
    return true;
}

static void update_one(World *w, EntityID id, void *ud) {
    VFE_LuaVM *vm = (VFE_LuaVM *)ud;
    ScriptComponent *sc = VFE_SCRIPT(w, id);
    if (!sc) return;
    if (!sc->loaded) { vfe_lua_load_script(vm, id); return; }

    vm->current_entity = id;
    lua_pushinteger(vm->L, (lua_Integer)id);
    lua_setglobal(vm->L, "self");

    lua_getglobal(vm->L, "Update");
    if (lua_isfunction(vm->L, -1)) {
        if (lua_pcall(vm->L, 0, 0, 0) != LUA_OK) {
            VFE_WARN("Lua Update entity %u: %s", id, lua_tostring(vm->L, -1));
            lua_pop(vm->L, 1);
        }
    } else {
        lua_pop(vm->L, 1);
    }
}

void vfe_lua_update_all(VFE_LuaVM *vm, float dt) {
    if (!vm->L) return;
    /* Expose DeltaTime as a global */
    lua_pushnumber(vm->L, (lua_Number)dt);
    lua_setglobal(vm->L, "DeltaTime");

    ComponentMask req = VFE_MASK_ADD(0, VFE_COMP_SCRIPT);
    vfe_foreach_entity(vm->world, req, 0, update_one, vm);
}

bool vfe_lua_exec_string(VFE_LuaVM *vm, const char *code) {
    if (!vm->L || !code) return false;
    if (luaL_dostring(vm->L, code) != LUA_OK) {
        VFE_ERROR("Lua exec: %s", lua_tostring(vm->L, -1));
        lua_pop(vm->L, 1);
        return false;
    }
    return true;
}

void vfe_lua_reload_all(VFE_LuaVM *vm) {
    ComponentMask req = VFE_MASK_ADD(0, VFE_COMP_SCRIPT);
    for (EntityID id = 1; id <= vm->world->highest_id; id++) {
        if (!vfe_entity_alive(vm->world, id)) continue;
        if (!VFE_MASK_HAS(vm->world->entities[id].mask, VFE_COMP_SCRIPT)) continue;
        ScriptComponent *sc = VFE_SCRIPT(vm->world, id);
        if (sc) { sc->loaded = false; sc->lua_ref = 0; }
    }
    VFE_INFO("All scripts marked for reload");
}
