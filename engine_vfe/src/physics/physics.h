/* VFE — Physics: AABB collision + simple dynamics */
#pragma once
#ifndef VFE_PHYSICS_H
#define VFE_PHYSICS_H

#include "../core/ecs.h"

/* Gravity constant (world units/s²) */
#define VFE_GRAVITY -18.0f

/*
 * Integrate velocity + apply gravity for all RigidBody entities.
 * Resolve AABB vs AABB collisions between dynamic and static bodies.
 * Call once per frame with the elapsed delta time.
 */
void vfe_physics_step(World *w, float dt);

/* Ray-AABB intersection; returns t of first hit or -1 if no hit */
float vfe_ray_aabb(Vec3 origin, Vec3 dir,
                   Vec3 box_min, Vec3 box_max,
                   Vec3 *hit_normal);

/* Broad-phase: collect all entities whose AABB overlaps a sphere */
u32 vfe_query_sphere(World *w, Vec3 center, float radius,
                     EntityID *out, u32 out_max);

#endif
