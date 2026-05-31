/*
 * VFE — Python IPC bridge
 * JSON-RPC over stdin/stdout (default) or Unix domain socket.
 * Allows Python (forge package) to drive the engine headlessly.
 *
 * Supported commands:
 *   spawn       — create entity with components
 *   destroy     — destroy entity
 *   set_pos     — set entity position
 *   set_vel     — set entity velocity
 *   load_scene  — load a .scene file
 *   save_scene  — save current world state
 *   screenshot  — export rendered frame to PNG
 *   exec_lua    — execute a Lua string
 *   get_state   — return world summary as JSON
 *   exit        — shut down the engine
 */
#pragma once
#ifndef VFE_IPC_H
#define VFE_IPC_H

#include "../core/ecs.h"
#include "../core/window.h"
#include "../scripting/lua_vm.h"

typedef struct {
    World      *world;
    VFE_Window *win;
    VFE_LuaVM  *lua;
    bool        use_socket;
    char        socket_path[128];
    int         socket_fd;
    int         client_fd;
    bool        running;
} VFE_IPC;

/* Initialise IPC.  use_socket=false → stdin/stdout; true → Unix socket */
bool vfe_ipc_init  (VFE_IPC *ipc, World *w, VFE_Window *win,
                    VFE_LuaVM *lua, bool use_socket,
                    const char *socket_path);
void vfe_ipc_close (VFE_IPC *ipc);

/*
 * Poll for one incoming command and execute it.
 * Non-blocking when use_socket=false (checks if stdin data is ready).
 * Returns false if the engine should shut down.
 */
bool vfe_ipc_poll(VFE_IPC *ipc);

#endif
