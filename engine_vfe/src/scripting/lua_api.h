/* VFE — Lua engine API (bindings header) */
#pragma once
#ifndef VFE_LUA_API_H
#define VFE_LUA_API_H
#include "lua_vm.h"

/* Register all VFE C functions into the Lua state */
void vfe_lua_register_api(VFE_LuaVM *vm);
#endif
