/* VFE — Camera implementation  (original C99) */
#include "camera.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#define DEG2RAD(d) ((f32)((d) * M_PI / 180.0))

/* ── Identity and basic matrix ops ────────────────────────────────── */

void vfe_mat4_identity(Mat4 *m) {
    memset(m, 0, sizeof(*m));
    m->m[0][0] = m->m[1][1] = m->m[2][2] = m->m[3][3] = 1.0f;
}

void vfe_mat4_mul(Mat4 *out, const Mat4 *a, const Mat4 *b) {
    Mat4 tmp; memset(&tmp, 0, sizeof(tmp));
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            for (int k = 0; k < 4; k++)
                tmp.m[i][j] += a->m[i][k] * b->m[k][j];
    *out = tmp;
}

void vfe_mat4_ortho(Mat4 *m, float l, float r, float b, float t,
                    float n, float f) {
    vfe_mat4_identity(m);
    m->m[0][0] =  2.0f / (r - l);
    m->m[1][1] =  2.0f / (t - b);
    m->m[2][2] = -2.0f / (f - n);
    m->m[3][0] = -(r + l) / (r - l);
    m->m[3][1] = -(t + b) / (t - b);
    m->m[3][2] = -(f + n) / (f - n);
}

void vfe_mat4_persp(Mat4 *m, float fov_deg, float aspect,
                    float near_p, float far_p) {
    float fov = DEG2RAD(fov_deg);
    float f   = 1.0f / tanf(fov * 0.5f);
    memset(m, 0, sizeof(*m));
    m->m[0][0] =  f / aspect;
    m->m[1][1] =  f;
    m->m[2][2] =  (far_p + near_p) / (near_p - far_p);
    m->m[2][3] = -1.0f;
    m->m[3][2] =  (2.0f * far_p * near_p) / (near_p - far_p);
}

void vfe_mat4_lookat(Mat4 *m, Vec3 eye, Vec3 center, Vec3 up) {
    Vec3 f = vec3_sub(center, eye);
    float fl = sqrtf(f.x*f.x + f.y*f.y + f.z*f.z);
    f = vec3_scale(f, 1.0f / fl);

    /* right = forward × up */
    Vec3 r = {
        f.y*up.z - f.z*up.y,
        f.z*up.x - f.x*up.z,
        f.x*up.y - f.y*up.x
    };
    float rl = sqrtf(r.x*r.x + r.y*r.y + r.z*r.z);
    r = vec3_scale(r, 1.0f / (rl > 0 ? rl : 1.0f));

    /* reorthogonalise up */
    Vec3 u = {
        r.y*f.z - r.z*f.y,
        r.z*f.x - r.x*f.z,
        r.x*f.y - r.y*f.x
    };

    memset(m, 0, sizeof(*m));
    m->m[0][0] = r.x; m->m[1][0] = r.y; m->m[2][0] = r.z;
    m->m[0][1] = u.x; m->m[1][1] = u.y; m->m[2][1] = u.z;
    m->m[0][2] =-f.x; m->m[1][2] =-f.y; m->m[2][2] =-f.z;
    m->m[3][0] = -(r.x*eye.x + r.y*eye.y + r.z*eye.z);
    m->m[3][1] = -(u.x*eye.x + u.y*eye.y + u.z*eye.z);
    m->m[3][2] =  (f.x*eye.x + f.y*eye.y + f.z*eye.z);
    m->m[3][3] = 1.0f;
}

/* ── Camera init and update ───────────────────────────────────────── */

void vfe_cam_init(VFE_Camera *cam, VFE_CamMode mode, int vp_w, int vp_h) {
    memset(cam, 0, sizeof(*cam));
    cam->mode      = mode;
    cam->vp_w      = vp_w;
    cam->vp_h      = vp_h;
    cam->zoom      = 1.0f;
    cam->fov_deg   = 60.0f;
    cam->near_plane= 0.1f;
    cam->far_plane = 1000.0f;
    cam->pitch_deg = 45.0f;  /* isometric classic angle */
    cam->yaw_deg   = 225.0f;
    cam->target    = vec3(0, 0, 0);
    vfe_cam_update(cam);
}

void vfe_cam_update(VFE_Camera *cam) {
    float aspect = (cam->vp_h > 0)
                   ? (float)cam->vp_w / (float)cam->vp_h : 1.0f;

    switch (cam->mode) {
    case VFE_CAM_ISOMETRIC: {
        /* Classic dimetric isometric: 45° yaw, atan(1/√2) ≈ 35.26° pitch */
        float p = DEG2RAD(cam->pitch_deg);
        float y = DEG2RAD(cam->yaw_deg);
        float dist = 100.0f / cam->zoom;
        cam->position = (Vec3){
            cam->target.x + dist * cosf(p) * sinf(y),
            cam->target.y + dist * sinf(p),
            cam->target.z + dist * cosf(p) * cosf(y)
        };
        vfe_mat4_lookat(&cam->view, cam->position, cam->target,
                         (Vec3){0,1,0});

        float hw = (float)cam->vp_w * 0.5f / cam->zoom;
        float hh = (float)cam->vp_h * 0.5f / cam->zoom;
        vfe_mat4_ortho(&cam->proj, -hw, hw, -hh, hh,
                        cam->near_plane, cam->far_plane);
        break;
    }
    case VFE_CAM_TOPDOWN: {
        cam->position = vec3_add(cam->target, (Vec3){0, 50.0f / cam->zoom, 0});
        vfe_mat4_lookat(&cam->view, cam->position, cam->target,
                         (Vec3){0,0,-1});
        float hw = (float)cam->vp_w * 0.5f / cam->zoom;
        float hh = (float)cam->vp_h * 0.5f / cam->zoom;
        vfe_mat4_ortho(&cam->proj, -hw, hw, -hh, hh,
                        cam->near_plane, cam->far_plane);
        break;
    }
    case VFE_CAM_PERSPECTIVE: {
        float p = DEG2RAD(cam->pitch_deg);
        float y = DEG2RAD(cam->yaw_deg);
        float dist = 20.0f;
        cam->position = (Vec3){
            cam->target.x + dist * cosf(p) * sinf(y),
            cam->target.y + dist * sinf(p),
            cam->target.z + dist * cosf(p) * cosf(y)
        };
        vfe_mat4_lookat(&cam->view, cam->position, cam->target,
                         (Vec3){0,1,0});
        vfe_mat4_persp (&cam->proj, cam->fov_deg, aspect,
                         cam->near_plane, cam->far_plane);
        break;
    }
    }
    vfe_mat4_mul(&cam->view_proj, &cam->proj, &cam->view);
}

void vfe_cam_move(VFE_Camera *cam, float dx, float dy, float dz) {
    cam->target.x += dx;
    cam->target.y += dy;
    cam->target.z += dz;
    vfe_cam_update(cam);
}

void vfe_cam_zoom(VFE_Camera *cam, float delta) {
    cam->zoom += delta;
    if (cam->zoom < 0.05f) cam->zoom = 0.05f;
    if (cam->zoom > 50.0f) cam->zoom = 50.0f;
    vfe_cam_update(cam);
}

Vec2 vfe_cam_project(const VFE_Camera *cam, Vec3 w) {
    /* Multiply by view_proj, divide by w */
    float x = cam->view_proj.m[0][0]*w.x + cam->view_proj.m[1][0]*w.y +
               cam->view_proj.m[2][0]*w.z + cam->view_proj.m[3][0];
    float y = cam->view_proj.m[0][1]*w.x + cam->view_proj.m[1][1]*w.y +
               cam->view_proj.m[2][1]*w.z + cam->view_proj.m[3][1];
    float ww= cam->view_proj.m[0][3]*w.x + cam->view_proj.m[1][3]*w.y +
               cam->view_proj.m[2][3]*w.z + cam->view_proj.m[3][3];
    if (ww != 0.0f) { x /= ww; y /= ww; }
    return (Vec2){ x, y };
}

void vfe_cam_unproject(const VFE_Camera *cam, float sx, float sy,
                        Vec3 *ray_origin, Vec3 *ray_dir) {
    /* Convert pixel to NDC */
    float ndcx = (2.0f * sx / (float)cam->vp_w) - 1.0f;
    float ndcy = 1.0f - (2.0f * sy / (float)cam->vp_h);
    *ray_origin = cam->position;
    /* For perspective we emit a ray; for ortho the ray is always down */
    if (cam->mode == VFE_CAM_PERSPECTIVE) {
        /* Approximate: direction from eye through the NDC point on near plane */
        float tanH  = tanf(DEG2RAD(cam->fov_deg * 0.5f));
        float aspect= (cam->vp_h > 0) ? (float)cam->vp_w / cam->vp_h : 1.0f;
        *ray_dir = (Vec3){ ndcx * tanH * aspect, ndcy * tanH, -1.0f };
    } else {
        *ray_dir = (Vec3){ 0, -1, 0 }; /* straight down for ortho views */
    }
}
