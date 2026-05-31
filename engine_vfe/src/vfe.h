/*
 * VoxelForge Engine (VFE) — Master Public Header
 *
 * Include this single header to access the entire engine API.
 * All code in this engine is original and written from first principles.
 * License: MIT
 */
#pragma once
#ifndef VFE_H
#define VFE_H

#include "core/types.h"
#include "core/log.h"
#include "core/ecs.h"
#include "core/window.h"
#include "core/input.h"
#include "core/timer.h"
#include "voxel/voxel_data.h"
#include "voxel/vox_loader.h"
#include "voxel/mesher.h"
#include "renderer/shader.h"
#include "renderer/camera.h"
#include "renderer/renderer.h"
#include "physics/physics.h"
#include "scripting/lua_vm.h"
#include "scripting/lua_api.h"
#include "scene/scene.h"
#include "audio/audio.h"
#include "ipc/ipc.h"

/* ── Engine context (one per process) ──────────────────────────────── */

typedef struct {
    VFE_Window   win;
    VFE_Timer    timer;
    InputState   input;
    VFE_Camera   cam;
    VFE_Renderer renderer;
    VFE_LuaVM    lua;
    VFE_Audio    audio;
    VFE_IPC      ipc;
    World       *world;

    /* Config */
    u32   target_fps;
    bool  headless;
    bool  use_ipc_socket;
    char  ipc_socket_path[128];
    char  startup_scene[256];
    char  screenshot_path[256];  /* non-empty → screenshot then exit */
} VFE_Engine;

/* ── Lifecycle ──────────────────────────────────────────────────────── */

bool vfe_engine_init(VFE_Engine *e, int argc, char **argv);
void vfe_engine_run (VFE_Engine *e);
void vfe_engine_stop(VFE_Engine *e);

/* ── Version ────────────────────────────────────────────────────────── */
#define VFE_VERSION_MAJOR 1
#define VFE_VERSION_MINOR 0
#define VFE_VERSION_PATCH 0
#define VFE_VERSION_STRING "1.0.0"

#endif /* VFE_H */
