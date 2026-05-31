/* VFE — Render pipeline implementation  (original C99) */
#include "renderer.h"
#include "../voxel/voxel_data.h"
#include "../core/log.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

/* ── Built-in shader sources ────────────────────────────────────────── */

static const char *VOXEL_VERT = "#version 330 core\n"
"layout(location=0) in vec3 aPos;\n"
"layout(location=1) in vec3 aNormal;\n"
"layout(location=2) in float aColorIdx;\n"
"uniform mat4 uModel;\n"
"uniform mat4 uViewProj;\n"
"uniform mat4 uLightMVP;\n"
"out vec3 vWorldPos;\n"
"out vec3 vNormal;\n"
"out float vColorIdx;\n"
"out vec4 vLightSpacePos;\n"
"void main() {\n"
"  vec4 worldPos = uModel * vec4(aPos, 1.0);\n"
"  vWorldPos     = worldPos.xyz;\n"
"  vNormal       = normalize(mat3(uModel) * aNormal);\n"
"  vColorIdx     = aColorIdx;\n"
"  vLightSpacePos= uLightMVP * worldPos;\n"
"  gl_Position   = uViewProj * worldPos;\n"
"}\n";

static const char *VOXEL_FRAG = "#version 330 core\n"
"in vec3  vWorldPos;\n"
"in vec3  vNormal;\n"
"in float vColorIdx;\n"
"in vec4  vLightSpacePos;\n"
"uniform sampler1D uPalette;\n"
"uniform sampler2D uShadowMap;\n"
"uniform vec3  uSunDir;\n"
"uniform vec3  uSunColor;\n"
"uniform vec3  uAmbient;\n"
"uniform vec3  uCamPos;\n"
"out vec4 fragColor;\n"
"float shadowPCF(vec4 lsPos) {\n"
"  vec3 proj = lsPos.xyz / lsPos.w * 0.5 + 0.5;\n"
"  if (proj.z > 1.0) return 1.0;\n"
"  float bias = max(0.005*(1.0-dot(vNormal,-uSunDir)),0.001);\n"
"  float shadow = 0.0;\n"
"  vec2 texel = 1.0 / textureSize(uShadowMap, 0);\n"
"  for (int x=-1;x<=1;x++) for(int y=-1;y<=1;y++) {\n"
"    float d = texture(uShadowMap, proj.xy + vec2(x,y)*texel).r;\n"
"    shadow += (proj.z - bias > d) ? 0.0 : 1.0;\n"
"  }\n"
"  return shadow / 9.0;\n"
"}\n"
"void main() {\n"
"  vec4 albedo = texture(uPalette, (vColorIdx+0.5)/256.0);\n"
"  if (albedo.a < 0.01) discard;\n"
"  float diff  = max(dot(vNormal, -normalize(uSunDir)), 0.0);\n"
"  vec3  spec  = vec3(0);\n"
"  vec3  V     = normalize(uCamPos - vWorldPos);\n"
"  vec3  H     = normalize(-normalize(uSunDir) + V);\n"
"  float sp    = pow(max(dot(vNormal,H),0.0),32.0);\n"
"  spec = uSunColor * sp * 0.15;\n"
"  float shadow= shadowPCF(vLightSpacePos);\n"
"  vec3  lit   = albedo.rgb * (uAmbient + uSunColor*diff*shadow) + spec*shadow;\n"
"  fragColor   = vec4(lit, albedo.a);\n"
"}\n";

static const char *SHADOW_VERT = "#version 330 core\n"
"layout(location=0) in vec3 aPos;\n"
"uniform mat4 uModel;\n"
"uniform mat4 uLightMVP;\n"
"void main() { gl_Position = uLightMVP * uModel * vec4(aPos,1.0); }\n";

static const char *SHADOW_FRAG = "#version 330 core\n"
"void main() {}\n";

static const char *POST_VERT = "#version 330 core\n"
"layout(location=0) in vec2 aPos;\n"
"out vec2 vUV;\n"
"void main() { vUV=aPos*0.5+0.5; gl_Position=vec4(aPos,0.0,1.0); }\n";

static const char *POST_FRAG = "#version 330 core\n"
"in vec2 vUV;\n"
"uniform sampler2D uScreen;\n"
"uniform float uTime;\n"
"out vec4 fragColor;\n"
"void main() {\n"
"  /* Chromatic aberration */\n"
"  float ca = 0.002;\n"
"  float r = texture(uScreen, vUV + vec2(ca, 0)).r;\n"
"  float g = texture(uScreen, vUV).g;\n"
"  float b = texture(uScreen, vUV - vec2(ca, 0)).b;\n"
"  vec3 col = vec3(r, g, b);\n"
"  /* Vignette */\n"
"  vec2 c = vUV - 0.5;\n"
"  col *= 1.0 - dot(c,c)*1.2;\n"
"  /* Reinhard tone-map */\n"
"  col = col / (col + 1.0);\n"
"  fragColor = vec4(col, 1.0);\n"
"}\n";

static const char *SKY_VERT = "#version 330 core\n"
"layout(location=0) in vec2 aPos;\n"
"out vec2 vUV;\n"
"void main() { vUV=aPos*0.5+0.5; gl_Position=vec4(aPos,0.9999,1.0); }\n";

static const char *SKY_FRAG = "#version 330 core\n"
"in vec2 vUV;\n"
"uniform vec3 uSkyTop;\n"
"uniform vec3 uSkyBot;\n"
"out vec4 fragColor;\n"
"void main() {\n"
"  fragColor = vec4(mix(uSkyBot, uSkyTop, vUV.y), 1.0);\n"
"}\n";

/* ── Fullscreen quad ─────────────────────────────────────────────────── */

static void init_quad(unsigned int *vao, unsigned int *vbo) {
    float verts[] = { -1,-1, 1,-1, -1,1, 1,-1, 1,1, -1,1 };
    glGenVertexArrays(1, vao);
    glGenBuffers(1, vbo);
    glBindVertexArray(*vao);
    glBindBuffer(GL_ARRAY_BUFFER, *vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(verts), verts, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, NULL);
    glBindVertexArray(0);
}

/* ── Init ────────────────────────────────────────────────────────────── */

bool vfe_renderer_init(VFE_Renderer *r, VFE_Window *win,
                       VFE_Camera *cam, World *world) {
    memset(r, 0, sizeof(*r));
    r->win   = win;
    r->cam   = cam;
    r->world = world;

    r->sun_dir      = (Vec3){  0.5f, -1.0f, -0.7f };
    r->sun_color    = (Vec3){  1.0f,  0.95f, 0.85f };
    r->ambient_color= (Vec3){  0.15f, 0.18f, 0.22f };
    r->ambient_intensity = 1.0f;

    /* Build shaders from embedded source */
    r->sh_voxel  = vfe_shader_build(VOXEL_VERT,  VOXEL_FRAG);
    r->sh_shadow = vfe_shader_build(SHADOW_VERT, SHADOW_FRAG);
    r->sh_sky    = vfe_shader_build(SKY_VERT,    SKY_FRAG);
    r->sh_post   = vfe_shader_build(POST_VERT,   POST_FRAG);

    if (!r->sh_voxel || !r->sh_shadow || !r->sh_sky || !r->sh_post) {
        VFE_ERROR("Renderer: shader build failed");
        return false;
    }

    /* Shadow map FBO */
    glGenFramebuffers(1, &r->fbo_shadow);
    glGenTextures(1, &r->tex_shadow);
    glBindTexture(GL_TEXTURE_2D, r->tex_shadow);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
                 VFE_SHADOW_MAP_SIZE, VFE_SHADOW_MAP_SIZE,
                 0, GL_DEPTH_COMPONENT, GL_FLOAT, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER);
    float border[] = {1,1,1,1};
    glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, border);
    glBindFramebuffer(GL_FRAMEBUFFER, r->fbo_shadow);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                           GL_TEXTURE_2D, r->tex_shadow, 0);
    glDrawBuffer(GL_NONE);
    glReadBuffer(GL_NONE);
    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    /* Game FBO (off-screen colour + depth at game resolution) */
    int gw = win->game_width, gh = win->game_height;
    glGenFramebuffers(1, &r->fbo_game);
    glBindFramebuffer(GL_FRAMEBUFFER, r->fbo_game);

    glGenTextures(1, &r->tex_game_color);
    glBindTexture(GL_TEXTURE_2D, r->tex_game_color);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, gw, gh, 0,
                 GL_RGBA, GL_FLOAT, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                           GL_TEXTURE_2D, r->tex_game_color, 0);

    glGenTextures(1, &r->tex_game_depth);
    glBindTexture(GL_TEXTURE_2D, r->tex_game_depth);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, gw, gh, 0,
                 GL_DEPTH_COMPONENT, GL_FLOAT, NULL);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                           GL_TEXTURE_2D, r->tex_game_depth, 0);
    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    /* Fullscreen quad for post-processing */
    init_quad(&r->vao_quad, &r->vbo_quad);

    /* Default palette texture */
    VoxelPalette def; vfe_palette_default(&def);
    vfe_palette_to_tex1d(&def, &r->tex_palette);

    VFE_INFO("Renderer initialised (%dx%d game resolution)", gw, gh);
    return true;
}

void vfe_renderer_destroy(VFE_Renderer *r) {
    vfe_shader_destroy(r->sh_voxel);
    vfe_shader_destroy(r->sh_shadow);
    vfe_shader_destroy(r->sh_sky);
    vfe_shader_destroy(r->sh_post);
    if (r->fbo_shadow)   glDeleteFramebuffers(1, &r->fbo_shadow);
    if (r->tex_shadow)   glDeleteTextures(1, &r->tex_shadow);
    if (r->fbo_game)     glDeleteFramebuffers(1, &r->fbo_game);
    if (r->tex_game_color)glDeleteTextures(1, &r->tex_game_color);
    if (r->tex_game_depth)glDeleteTextures(1, &r->tex_game_depth);
    if (r->tex_palette)  glDeleteTextures(1, &r->tex_palette);
    if (r->vao_quad)     glDeleteVertexArrays(1, &r->vao_quad);
    if (r->vbo_quad)     glDeleteBuffers(1, &r->vbo_quad);
}

/* ── Per-entity draw helper ─────────────────────────────────────────── */

typedef struct { VFE_Renderer *r; bool shadow_pass; } DrawCtx;

static void build_model_matrix(const TransformComponent *t, float m[16]) {
    /* Simplified: translation only (add full rotation as extension) */
    memset(m, 0, 64);
    m[0]=t->scale.x; m[5]=t->scale.y; m[10]=t->scale.z; m[15]=1.0f;
    m[12]=t->position.x; m[13]=t->position.y; m[14]=t->position.z;
}

static void draw_entity(World *w, EntityID id, void *ud) {
    DrawCtx *ctx = (DrawCtx *)ud;
    VFE_Renderer *r = ctx->r;

    TransformComponent  *tr = VFE_TRANSFORM(w, id);
    VoxelModelComponent *vm = VFE_VOXEL(w, id);
    if (!tr || !vm || !vm->asset || !vm->visible) return;

    VoxelModelAsset *a = vm->asset;
    if (a->mesh_dirty || a->grid->dirty) vfe_asset_rebuild(a);
    if (!a->vert_count) return;

    float model[16];
    build_model_matrix(tr, model);

    if (ctx->shadow_pass) {
        vfe_shader_setm4(r->sh_shadow, "uModel", model);
    } else {
        vfe_shader_setm4(r->sh_voxel, "uModel", model);
    }

    glBindVertexArray(a->vao);
    glDrawArrays(GL_TRIANGLES, 0, (GLsizei)a->vert_count);
    glBindVertexArray(0);

    r->draw_calls++;
    r->verts_submitted += a->vert_count;
}

/* ── Full frame render ──────────────────────────────────────────────── */

void vfe_renderer_frame(VFE_Renderer *r, float dt) {
    (void)dt;
    r->draw_calls = 0;
    r->verts_submitted = 0;
    int gw = r->win->game_width, gh = r->win->game_height;

    /* Build light MVP for shadow pass (orthographic from sun direction) */
    Mat4 lightView, lightProj, lightMVP;
    Vec3 lightTarget = r->cam->target;
    Vec3 ldir = r->sun_dir;
    float ll = sqrtf(ldir.x*ldir.x+ldir.y*ldir.y+ldir.z*ldir.z);
    if (ll>0) { ldir.x/=ll; ldir.y/=ll; ldir.z/=ll; }
    Vec3 lightPos = vec3_sub(lightTarget, vec3_scale(ldir, 80.0f));
    vfe_mat4_lookat(&lightView, lightPos, lightTarget, (Vec3){0,1,0});
    vfe_mat4_ortho(&lightProj, -64,-64+128, -64,-64+128, 0.1f, 300.0f);
    /* Note: ortho args are (l,r,b,t) but we keep it simple here */
    vfe_mat4_mul(&lightMVP, &lightProj, &lightView);

    ComponentMask req = VFE_MASK_ADD(VFE_MASK_ADD(0, VFE_COMP_TRANSFORM),
                                      VFE_COMP_VOXEL_MODEL);

    /* ── PASS 1: Shadow map ─────────────────────────────────────────── */
    glViewport(0, 0, VFE_SHADOW_MAP_SIZE, VFE_SHADOW_MAP_SIZE);
    glBindFramebuffer(GL_FRAMEBUFFER, r->fbo_shadow);
    glClear(GL_DEPTH_BUFFER_BIT);
    glCullFace(GL_FRONT);
    vfe_shader_use(r->sh_shadow);
    vfe_shader_setm4(r->sh_shadow, "uLightMVP", &lightMVP.m[0][0]);
    DrawCtx shadow_ctx = { r, true };
    vfe_foreach_entity(r->world, req, 0, draw_entity, &shadow_ctx);
    glCullFace(GL_BACK);

    /* ── PASS 2: Sky + Geometry (game FBO) ─────────────────────────── */
    glViewport(0, 0, gw, gh);
    glBindFramebuffer(GL_FRAMEBUFFER, r->fbo_game);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    /* Sky */
    glDepthMask(GL_FALSE);
    vfe_shader_use(r->sh_sky);
    vfe_shader_set3f(r->sh_sky, "uSkyTop",  0.35f, 0.55f, 0.85f);
    vfe_shader_set3f(r->sh_sky, "uSkyBot",  0.70f, 0.82f, 0.95f);
    glBindVertexArray(r->vao_quad);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glDepthMask(GL_TRUE);

    /* Voxels */
    vfe_shader_use(r->sh_voxel);
    vfe_shader_setm4(r->sh_voxel, "uViewProj",  &r->cam->view_proj.m[0][0]);
    vfe_shader_setm4(r->sh_voxel, "uLightMVP",  &lightMVP.m[0][0]);
    vfe_shader_set3f(r->sh_voxel, "uSunDir",     r->sun_dir.x, r->sun_dir.y, r->sun_dir.z);
    vfe_shader_set3f(r->sh_voxel, "uSunColor",   r->sun_color.x, r->sun_color.y, r->sun_color.z);
    vfe_shader_set3f(r->sh_voxel, "uAmbient",    r->ambient_color.x, r->ambient_color.y, r->ambient_color.z);
    vfe_shader_set3f(r->sh_voxel, "uCamPos",     r->cam->position.x, r->cam->position.y, r->cam->position.z);
    vfe_shader_seti (r->sh_voxel, "uPalette",   0);
    vfe_shader_seti (r->sh_voxel, "uShadowMap", 1);
    glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_1D, r->tex_palette);
    glActiveTexture(GL_TEXTURE1); glBindTexture(GL_TEXTURE_2D, r->tex_shadow);

    if (r->wireframe) glPolygonMode(GL_FRONT_AND_BACK, GL_LINE);
    DrawCtx geo_ctx = { r, false };
    vfe_foreach_entity(r->world, req, 0, draw_entity, &geo_ctx);
    if (r->wireframe) glPolygonMode(GL_FRONT_AND_BACK, GL_FILL);

    /* ── PASS 3: Post-process → default framebuffer ─────────────────── */
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    glViewport(0, 0, r->win->width, r->win->height);
    glClear(GL_COLOR_BUFFER_BIT);
    glDepthMask(GL_FALSE);
    vfe_shader_use(r->sh_post);
    vfe_shader_seti(r->sh_post, "uScreen", 0);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, r->tex_game_color);
    glBindVertexArray(r->vao_quad);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glBindVertexArray(0);
    glDepthMask(GL_TRUE);
}

void vfe_renderer_set_palette(VFE_Renderer *r, const VoxelPalette *pal) {
    if (!pal) return;
    vfe_palette_to_tex1d(pal, &r->tex_palette);
}
