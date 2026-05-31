/* VFE — Window/context implementation */
#include "window.h"
#include "log.h"
#include <SDL2/SDL_image.h>
#include <string.h>
#include <stdlib.h>

bool vfe_window_create(VFE_Window *win, const char *title,
                       int w, int h, float scale, bool headless) {
    memset(win, 0, sizeof(*win));
    win->width      = w;
    win->height     = h;
    win->scale      = scale > 0.0f ? scale : 1.0f;
    win->game_width  = (int)(w / win->scale);
    win->game_height = (int)(h / win->scale);
    win->headless   = headless;

    if (headless) {
        SDL_setenv("SDL_VIDEODRIVER", "offscreen", 1);
        VFE_INFO("Window: headless mode (offscreen SDL driver)");
    }

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_EVENTS) != 0) {
        VFE_ERROR("SDL_Init: %s", SDL_GetError());
        return false;
    }
    if (IMG_Init(IMG_INIT_PNG) == 0) {
        VFE_WARN("SDL_image PNG init failed: %s", IMG_GetError());
    }

    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 3);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8);

    Uint32 flags = SDL_WINDOW_OPENGL;
    flags |= headless ? SDL_WINDOW_HIDDEN : SDL_WINDOW_SHOWN;

    win->sdl_win = SDL_CreateWindow(
        title, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        w, h, flags);
    if (!win->sdl_win) {
        VFE_ERROR("SDL_CreateWindow: %s", SDL_GetError());
        return false;
    }

    win->gl_ctx = SDL_GL_CreateContext(win->sdl_win);
    if (!win->gl_ctx) {
        VFE_ERROR("SDL_GL_CreateContext: %s", SDL_GetError());
        return false;
    }
    SDL_GL_MakeCurrent(win->sdl_win, win->gl_ctx);
    SDL_GL_SetSwapInterval(0); /* vsync off for max throughput */

    glewExperimental = GL_TRUE;
    GLenum err = glewInit();
    if (err != GLEW_OK) {
        VFE_ERROR("GLEW init: %s", glewGetErrorString(err));
        return false;
    }

    VFE_INFO("OpenGL %s | %s", glGetString(GL_VERSION), glGetString(GL_RENDERER));
    glViewport(0, 0, win->game_width, win->game_height);
    glEnable(GL_DEPTH_TEST);
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

    return true;
}

void vfe_window_destroy(VFE_Window *win) {
    if (!win) return;
    if (win->gl_ctx)  SDL_GL_DeleteContext(win->gl_ctx);
    if (win->sdl_win) SDL_DestroyWindow(win->sdl_win);
    IMG_Quit();
    SDL_Quit();
}

void vfe_window_swap(VFE_Window *win) {
    if (!win || win->headless) return;
    SDL_GL_SwapWindow(win->sdl_win);
}

void vfe_window_poll_close(VFE_Window *win, SDL_Event *ev) {
    if (ev->type == SDL_QUIT) win->should_close = true;
    if (ev->type == SDL_KEYDOWN &&
        ev->key.keysym.scancode == SDL_SCANCODE_F4 &&
        (SDL_GetModState() & KMOD_ALT)) {
        win->should_close = true;
    }
}

bool vfe_window_screenshot(VFE_Window *win, const char *path) {
    int w = win->game_width, h = win->game_height;
    unsigned char *px = (unsigned char *)malloc((size_t)w * h * 4);
    if (!px) return false;

    glReadBuffer(GL_FRONT);
    glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, px);

    /* Flip vertically (OpenGL origin is bottom-left) */
    unsigned char *row = (unsigned char *)malloc((size_t)w * 4);
    if (row) {
        for (int y = 0; y < h / 2; y++) {
            unsigned char *a = px + (size_t)y * w * 4;
            unsigned char *b = px + (size_t)(h - 1 - y) * w * 4;
            memcpy(row, a, (size_t)w * 4);
            memcpy(a,   b, (size_t)w * 4);
            memcpy(b, row, (size_t)w * 4);
        }
        free(row);
    }

    SDL_Surface *surf = SDL_CreateRGBSurfaceFrom(
        px, w, h, 32, w * 4,
        0x000000FFu, 0x0000FF00u, 0x00FF0000u, 0xFF000000u);
    bool ok = false;
    if (surf) {
        ok = (IMG_SavePNG(surf, path) == 0);
        SDL_FreeSurface(surf);
    }
    free(px);
    if (ok) VFE_INFO("Screenshot saved → %s", path);
    else    VFE_ERROR("Screenshot failed: %s", IMG_GetError());
    return ok;
}
