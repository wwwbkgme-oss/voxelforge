/*
 * VFE — Main render pipeline
 *
 * Orchestrates the full render frame:
 *   1. Shadow pass    — depth map from directional light
 *   2. Geometry pass  — voxel models with Phong + AO lighting
 *   3. Sky pass       — procedural gradient sky
 *   4. Post-process   — bloom, vignette, chromatic aberration, tone-map
 *   5. UI pass        — 2D text/icon overlay
 */
#pragma once
#ifndef VFE_RENDERER_H
#define VFE_RENDERER_H

#include "../core/ecs.h"
#include "camera.h"
#include "shader.h"
#include "../core/window.h"

#define VFE_SHADOW_MAP_SIZE 2048

typedef struct {
    VFE_Window  *win;
    VFE_Camera  *cam;
    World       *world;

    /* Shaders */
    ShaderID  sh_voxel;
    ShaderID  sh_shadow;
    ShaderID  sh_sky;
    ShaderID  sh_post;

    /* Shadow map framebuffer */
    unsigned int fbo_shadow;
    unsigned int tex_shadow;

    /* Off-screen framebuffer (game resolution before upscale) */
    unsigned int fbo_game;
    unsigned int tex_game_color;
    unsigned int tex_game_depth;
    unsigned int vao_quad;   /* fullscreen quad for post-process */
    unsigned int vbo_quad;

    /* Palette texture (1D, 256 RGBA) */
    unsigned int tex_palette;

    /* Sun direction + colour */
    Vec3  sun_dir;
    Vec3  sun_color;
    Vec3  ambient_color;
    float ambient_intensity;

    /* Stats (updated each frame) */
    u32  draw_calls;
    u32  verts_submitted;

    bool wireframe;
    bool show_normals;
} VFE_Renderer;

bool vfe_renderer_init   (VFE_Renderer *r, VFE_Window *w,
                          VFE_Camera *cam, World *world);
void vfe_renderer_destroy(VFE_Renderer *r);
void vfe_renderer_frame  (VFE_Renderer *r, float dt);

/* Upload all dirty voxel model assets to GPU */
void vfe_renderer_upload_dirty(VFE_Renderer *r);

/* Update the palette texture from a VoxelPalette */
void vfe_renderer_set_palette(VFE_Renderer *r, const struct VoxelPalette *pal);

/* 2D text overlay (simple textured quads via SDL_ttf) */
void vfe_renderer_draw_text(VFE_Renderer *r, const char *text,
                             int x, int y, float r_, float g_, float b_);
#endif
