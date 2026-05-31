/* VFE — Camera system (isometric / top-down / perspective) */
#pragma once
#ifndef VFE_CAMERA_H
#define VFE_CAMERA_H
#include "../core/types.h"

typedef enum { VFE_CAM_ISOMETRIC=0, VFE_CAM_TOPDOWN=1, VFE_CAM_PERSPECTIVE=2 } VFE_CamMode;

typedef struct {
    VFE_CamMode mode;
    Vec3  target;      /* look-at point / follow target position */
    Vec3  position;    /* eye position (computed from target + angles) */
    f32   pitch_deg;   /* isometric: angle from horizontal */
    f32   yaw_deg;     /* rotation around up-axis */
    f32   zoom;        /* isometric / topdown zoom scale */
    f32   fov_deg;     /* perspective only */
    f32   near_plane;
    f32   far_plane;
    int   vp_w, vp_h;  /* viewport size (for aspect ratio) */

    /* Computed matrices (call vfe_cam_update to refresh) */
    Mat4  view;
    Mat4  proj;
    Mat4  view_proj;
} VFE_Camera;

void vfe_cam_init      (VFE_Camera *cam, VFE_CamMode mode, int vp_w, int vp_h);
void vfe_cam_update    (VFE_Camera *cam);
void vfe_cam_move      (VFE_Camera *cam, float dx, float dy, float dz);
void vfe_cam_zoom      (VFE_Camera *cam, float delta);

/* Project a world-space point into NDC [-1,1]^2 */
Vec2 vfe_cam_project   (const VFE_Camera *cam, Vec3 world);

/* Unproject a screen-space pixel to a world ray */
void vfe_cam_unproject (const VFE_Camera *cam, float sx, float sy,
                        Vec3 *ray_origin, Vec3 *ray_dir);

/* Build standard orthographic and perspective matrices */
void vfe_mat4_ortho   (Mat4 *m, float l, float r, float b, float t, float n, float f);
void vfe_mat4_persp   (Mat4 *m, float fov_deg, float aspect, float n, float f);
void vfe_mat4_lookat  (Mat4 *m, Vec3 eye, Vec3 center, Vec3 up);
void vfe_mat4_mul     (Mat4 *out, const Mat4 *a, const Mat4 *b);
void vfe_mat4_identity(Mat4 *m);
#endif
