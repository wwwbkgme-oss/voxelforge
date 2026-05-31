/*
 * VoxelForge Engine (VFE) — Common Types
 * Original source — not derived from any third-party engine.
 * License: MIT
 */
#pragma once
#ifndef VFE_TYPES_H
#define VFE_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* ── Integer aliases ──────────────────────────────────────────────────── */
typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t   i8;
typedef int16_t  i16;
typedef int32_t  i32;
typedef int64_t  i64;
typedef float    f32;
typedef double   f64;

/* ── Handle types ─────────────────────────────────────────────────────── */
typedef u32 EntityID;    /* 0 == invalid/null entity                       */
typedef u8  ComponentID; /* component type index; max VFE_MAX_COMPONENTS   */
typedef u8  SystemID;    /* system index; max VFE_MAX_SYSTEMS               */

#define VFE_INVALID_ENTITY   ((EntityID)0)
#define VFE_MAX_ENTITIES     4096
#define VFE_MAX_COMPONENTS   32
#define VFE_MAX_SYSTEMS      64
#define VFE_MAX_LIGHTS       64
#define VFE_CHUNK_SIZE       16    /* voxels per chunk axis                 */
#define VFE_MAX_CHUNKS       512

/* ── Math types ───────────────────────────────────────────────────────── */
typedef struct { f32 x, y; }          Vec2;
typedef struct { f32 x, y, z; }       Vec3;
typedef struct { f32 x, y, z, w; }    Vec4;
typedef struct { i32 x, y, z; }       IVec3;
typedef struct { f32 m[4][4]; }       Mat4;
typedef struct { f32 r, g, b, a; }    Color;
typedef struct { u8  r, g, b, a; }    Color8;

static inline Vec3  vec3(f32 x, f32 y, f32 z) { return (Vec3){x, y, z}; }
static inline Vec3  vec3_zero(void)            { return (Vec3){0,0,0};   }
static inline Vec3  vec3_add (Vec3 a, Vec3 b)  { return (Vec3){a.x+b.x, a.y+b.y, a.z+b.z}; }
static inline Vec3  vec3_sub (Vec3 a, Vec3 b)  { return (Vec3){a.x-b.x, a.y-b.y, a.z-b.z}; }
static inline Vec3  vec3_scale(Vec3 a, f32 s)  { return (Vec3){a.x*s, a.y*s, a.z*s}; }

/* Component-mask for cheap archetype queries — 32 components max */
typedef u32 ComponentMask;

#define VFE_MASK_HAS(mask, cid)   (((mask) >> (cid)) & 1u)
#define VFE_MASK_ADD(mask, cid)   ((mask) | (1u << (cid)))
#define VFE_MASK_REM(mask, cid)   ((mask) & ~(1u << (cid)))

#endif /* VFE_TYPES_H */
