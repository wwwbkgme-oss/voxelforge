/* VFE — Window and OpenGL context management */
#pragma once
#ifndef VFE_WINDOW_H
#define VFE_WINDOW_H

#include "types.h"
#include <SDL2/SDL.h>
#include <GL/glew.h>
#include <SDL2/SDL_opengl.h>

typedef struct {
    SDL_Window   *sdl_win;
    SDL_GLContext  gl_ctx;

    int width, height;     /* window/framebuffer size in pixels */
    int game_width;        /* internal render resolution        */
    int game_height;
    float scale;           /* game_size = window_size / scale   */

    bool headless;         /* offscreen rendering — no display  */
    bool should_close;
} VFE_Window;

bool vfe_window_create(VFE_Window *win, const char *title,
                       int w, int h, float scale, bool headless);
void vfe_window_destroy(VFE_Window *win);
void vfe_window_swap(VFE_Window *win);
void vfe_window_poll_close(VFE_Window *win, SDL_Event *ev);

/* Export current front-buffer to PNG (works in headless mode too) */
bool vfe_window_screenshot(VFE_Window *win, const char *path);

#endif
