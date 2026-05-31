/*
 * VoxelForge Engine (VFE) — Main Entry Point
 *
 * CLI flags:
 *   --headless               Run without display window
 *   --screenshot <path>      Export one frame to PNG then exit
 *   --scene     <path>       Load .scene file on start
 *   --width  <n>             Window width  (default 1280)
 *   --height <n>             Window height (default 720)
 *   --scale  <n>             Pixel-art scale divisor (default 1)
 *   --fps    <n>             Max FPS (default 60, 0=unlimited)
 *   --ipc-socket <path>      Enable Unix socket IPC
 *   --ipc-stdin              Enable stdin/stdout IPC (headless automation)
 *   --cam isometric|topdown|perspective
 *
 * All code in this file is original.
 */
#include "vfe.h"
#include "core/log.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── Argument parsing ───────────────────────────────────────────────── */

static bool flag(int argc, char **argv, const char *flag_name) {
    for (int i = 1; i < argc; i++)
        if (strcmp(argv[i], flag_name) == 0) return true;
    return false;
}
static const char *flag_val(int argc, char **argv, const char *f) {
    for (int i = 1; i < argc - 1; i++)
        if (strcmp(argv[i], f) == 0) return argv[i + 1];
    return NULL;
}
static int flag_int(int argc, char **argv, const char *f, int def) {
    const char *v = flag_val(argc, argv, f);
    return v ? atoi(v) : def;
}

/* ── Engine init ────────────────────────────────────────────────────── */

bool vfe_engine_init(VFE_Engine *e, int argc, char **argv) {
    memset(e, 0, sizeof(*e));

    /* Parse flags */
    e->headless  = flag(argc, argv, "--headless");
    e->target_fps= (u32)flag_int(argc, argv, "--fps", 60);
    int w = flag_int(argc, argv, "--width",  1280);
    int h = flag_int(argc, argv, "--height",  720);
    float scale = (float)flag_int(argc, argv, "--scale", 1);

    const char *scene   = flag_val(argc, argv, "--scene");
    const char *shot    = flag_val(argc, argv, "--screenshot");
    const char *sock    = flag_val(argc, argv, "--ipc-socket");
    const char *cam_str = flag_val(argc, argv, "--cam");
    bool use_stdin_ipc  = flag(argc, argv, "--ipc-stdin");

    if (shot) {
        strncpy(e->screenshot_path, shot, sizeof(e->screenshot_path)-1);
        e->headless = true;
    }
    if (scene)  strncpy(e->startup_scene, scene, sizeof(e->startup_scene)-1);
    if (sock)   strncpy(e->ipc_socket_path, sock, sizeof(e->ipc_socket_path)-1);

    /* Logging */
    vfe_log_init("vfe.log", LOG_DEBUG);
    VFE_INFO("VoxelForge Engine %s starting...", VFE_VERSION_STRING);
    if (e->headless) VFE_INFO("  Mode: headless");

    /* World */
    e->world = vfe_world_create();
    if (!e->world) return false;

    /* Window */
    const char *title = "VoxelForge Engine";
    if (!vfe_window_create(&e->win, title, w, h, scale, e->headless)) {
        VFE_ERROR("Window creation failed");
        return false;
    }

    /* Timer */
    vfe_timer_init(&e->timer, e->target_fps);

    /* Input */
    vfe_input_init(&e->input);

    /* Camera */
    VFE_CamMode cam_mode = VFE_CAM_ISOMETRIC;
    if (cam_str) {
        if (strcmp(cam_str, "topdown")     == 0) cam_mode = VFE_CAM_TOPDOWN;
        if (strcmp(cam_str, "perspective") == 0) cam_mode = VFE_CAM_PERSPECTIVE;
    }
    vfe_cam_init(&e->cam, cam_mode, e->win.game_width, e->win.game_height);

    /* Renderer */
    if (!vfe_renderer_init(&e->renderer, &e->win, &e->cam, e->world)) {
        VFE_ERROR("Renderer init failed");
        return false;
    }

    /* Lua VM */
    vfe_lua_init(&e->lua, e->world);

    /* Audio */
    vfe_audio_init(&e->audio);

    /* IPC */
    bool ipc_socket = (e->ipc_socket_path[0] != '\0');
    if (ipc_socket || use_stdin_ipc) {
        vfe_ipc_init(&e->ipc, e->world, &e->win, &e->lua,
                     ipc_socket, e->ipc_socket_path);
    }

    /* Load startup scene */
    if (e->startup_scene[0] != '\0') {
        SceneMetadata meta = {0};
        if (vfe_scene_load(e->world, e->startup_scene, &meta)) {
            e->renderer.sun_direction = meta.sun_direction;
            e->renderer.sun_color     = meta.sun_color;
        }
    }

    vfe_world_init_systems(e->world);
    VFE_INFO("Engine initialised. World entities: %u", e->world->entity_count);
    return true;
}

/* ── Main loop ──────────────────────────────────────────────────────── */

void vfe_engine_run(VFE_Engine *e) {
    VFE_INFO("Entering main loop");
    bool ipc_active = (e->ipc.win != NULL);
    bool one_frame  = (e->screenshot_path[0] != '\0');

    while (!e->win.should_close) {
        vfe_timer_tick(&e->timer);
        float dt = (float)e->timer.delta;

        /* IPC: process Python commands */
        if (ipc_active && !vfe_ipc_poll(&e->ipc)) {
            e->win.should_close = true;
            break;
        }

        /* Input */
        vfe_input_begin_frame(&e->input);
        if (!e->headless) {
            SDL_Event ev;
            while (SDL_PollEvent(&ev)) {
                vfe_input_process_event(&e->input, &ev);
                vfe_window_poll_close(&e->win, &ev);
            }
        }

        /* Systems */
        vfe_physics_step(e->world, dt);
        vfe_lua_update_all(&e->lua, dt);
        vfe_world_update_systems(e->world);

        /* Render */
        vfe_renderer_frame(&e->renderer, dt);

        /* Screenshot mode: capture and exit */
        if (e->headless && e->screenshot_path[0] != '\0') {
            vfe_window_screenshot(&e->win, e->screenshot_path);
            e->win.should_close = true;
        } else if (!e->headless) {
            vfe_window_swap(&e->win);
            vfe_timer_limit(&e->timer);
        }

        if (one_frame) break;
    }

    VFE_INFO("Main loop ended after %u frames", e->timer.frame);
}

void vfe_engine_stop(VFE_Engine *e) {
    vfe_world_shutdown_systems(e->world);
    vfe_ipc_close(&e->ipc);
    vfe_lua_close(&e->lua);
    vfe_audio_close(&e->audio);
    vfe_renderer_destroy(&e->renderer);
    vfe_window_destroy(&e->win);
    vfe_world_destroy(e->world);
    vfe_log_close();
}

/* ── main() ─────────────────────────────────────────────────────────── */

int main(int argc, char **argv) {
    VFE_Engine engine;
    if (!vfe_engine_init(&engine, argc, argv)) {
        fprintf(stderr, "VFE: engine init failed\n");
        return 1;
    }
    vfe_engine_run(&engine);
    vfe_engine_stop(&engine);
    return 0;
}
