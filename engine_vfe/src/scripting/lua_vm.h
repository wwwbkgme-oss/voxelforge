/* VFE — Lua 5.4 scripting subsystem */
#pragma once
#ifndef VFE_LUA_VM_H
#define VFE_LUA_VM_H

#include "../core/ecs.h"
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>

typedef struct {
    lua_State *L;
    World     *world;
    EntityID   current_entity; /* entity running the current script */
    bool       initialised;
} VFE_LuaVM;

bool  vfe_lua_init   (VFE_LuaVM *vm, World *world);
void  vfe_lua_close  (VFE_LuaVM *vm);

/* Load + call Start() for one entity's script component */
bool  vfe_lua_load_script  (VFE_LuaVM *vm, EntityID id);

/* Call Update() for all entities with an active script component */
void  vfe_lua_update_all   (VFE_LuaVM *vm, float dt);

/* Execute an arbitrary Lua string (for console / IPC commands) */
bool  vfe_lua_exec_string  (VFE_LuaVM *vm, const char *code);

/* Hot-reload all scripts */
void  vfe_lua_reload_all   (VFE_LuaVM *vm);
#endif
