/* VFE — Physics: AABB dynamics + collision resolution  (original C99) */
#include "physics.h"
#include "../core/log.h"
#include <math.h>
#include <stdlib.h>

/* ── AABB helpers ────────────────────────────────────────────────────── */

typedef struct { Vec3 min, max; } AABB;

static AABB entity_aabb(const TransformComponent *t, const RigidBodyComponent *rb) {
    Vec3 he = rb->half_extents;
    return (AABB){
        .min = { t->position.x - he.x, t->position.y - he.y, t->position.z - he.z },
        .max = { t->position.x + he.x, t->position.y + he.y, t->position.z + he.z },
    };
}

static bool aabb_overlap(AABB a, AABB b, Vec3 *penetration) {
    float dx0 = b.max.x - a.min.x,  dx1 = a.max.x - b.min.x;
    float dy0 = b.max.y - a.min.y,  dy1 = a.max.y - b.min.y;
    float dz0 = b.max.z - a.min.z,  dz1 = a.max.z - b.min.z;
    if (dx0 < 0 || dx1 < 0 || dy0 < 0 || dy1 < 0 || dz0 < 0 || dz1 < 0)
        return false;
    float px = (dx0 < dx1) ? dx0 : -dx1;
    float py = (dy0 < dy1) ? dy0 : -dy1;
    float pz = (dz0 < dz1) ? dz0 : -dz1;
    float apx = px < 0 ? -px : px;
    float apy = py < 0 ? -py : py;
    float apz = pz < 0 ? -pz : pz;
    if (apx <= apy && apx <= apz)      *penetration = (Vec3){ px, 0, 0 };
    else if (apy <= apx && apy <= apz) *penetration = (Vec3){ 0, py, 0 };
    else                               *penetration = (Vec3){ 0, 0, pz };
    return true;
}

/* ── Iteration context ───────────────────────────────────────────────── */

typedef struct {
    World *world;
    float  dt;
} PhysCtx;

static void integrate_entity(World *w, EntityID id, void *ud) {
    PhysCtx *ctx = (PhysCtx *)ud;
    TransformComponent *t  = VFE_TRANSFORM(w, id);
    RigidBodyComponent *rb = VFE_RIGIDBODY(w, id);
    if (!t || !rb || rb->is_static || rb->mass == 0.0f) return;

    /* Apply gravity */
    if (rb->use_gravity) rb->velocity.y += VFE_GRAVITY * ctx->dt;

    /* Integrate position */
    t->position.x += rb->velocity.x * ctx->dt;
    t->position.y += rb->velocity.y * ctx->dt;
    t->position.z += rb->velocity.z * ctx->dt;

    /* Clamp extreme velocities */
    const float MAX_SPEED = 200.0f;
    if (rb->velocity.y < -MAX_SPEED) rb->velocity.y = -MAX_SPEED;
}

static void resolve_pair(World *w,
                          EntityID ai, TransformComponent *ta,
                          RigidBodyComponent *ra,
                          EntityID bi, TransformComponent *tb,
                          RigidBodyComponent *rb) {
    (void)ai; (void)bi;
    Vec3 pen;
    AABB aa = entity_aabb(ta, ra);
    AABB ba = entity_aabb(tb, rb);
    if (!aabb_overlap(aa, ba, &pen)) return;

    /* Push dynamic body out of static/heavier body */
    bool a_dynamic = !ra->is_static && ra->mass > 0;
    bool b_dynamic = !rb->is_static && rb->mass > 0;

    if (a_dynamic && !b_dynamic) {
        ta->position.x -= pen.x;
        ta->position.y -= pen.y;
        ta->position.z -= pen.z;
        /* Velocity response */
        if (pen.y != 0) {
            float rebound = ra->restitution;
            if (ra->velocity.y * pen.y > 0)
                ra->velocity.y = -ra->velocity.y * rebound;
            /* Friction on horizontal */
            ra->velocity.x *= (1.0f - ra->friction * 0.1f);
            ra->velocity.z *= (1.0f - ra->friction * 0.1f);
        }
        if (pen.x != 0 && ra->velocity.x * pen.x > 0) ra->velocity.x = 0;
        if (pen.z != 0 && ra->velocity.z * pen.z > 0) ra->velocity.z = 0;
    } else if (!a_dynamic && b_dynamic) {
        tb->position.x += pen.x;
        tb->position.y += pen.y;
        tb->position.z += pen.z;
        if (pen.y != 0 && rb->velocity.y * (-pen.y) > 0)
            rb->velocity.y = -rb->velocity.y * rb->restitution;
        if (pen.x != 0 && rb->velocity.x * (-pen.x) > 0) rb->velocity.x = 0;
        if (pen.z != 0 && rb->velocity.z * (-pen.z) > 0) rb->velocity.z = 0;
    } else if (a_dynamic && b_dynamic) {
        /* Split the penetration by mass ratio */
        float total = ra->mass + rb->mass;
        float fa    = rb->mass / total;
        float fb    = ra->mass / total;
        ta->position.x -= pen.x * fa;
        ta->position.y -= pen.y * fa;
        ta->position.z -= pen.z * fa;
        tb->position.x += pen.x * fb;
        tb->position.y += pen.y * fb;
        tb->position.z += pen.z * fb;
    }
}

/* Narrow-phase: O(n²) — sufficient for games with <256 physics objects */
static void resolve_collisions(World *w) {
    ComponentMask req = VFE_MASK_ADD(VFE_MASK_ADD(0, VFE_COMP_TRANSFORM),
                                      VFE_COMP_RIGID_BODY);
    /* Collect candidates */
    EntityID ids[VFE_MAX_ENTITIES];
    u32 n = 0;
    for (EntityID id = 1; id <= w->highest_id && n < VFE_MAX_ENTITIES; id++) {
        if (!vfe_entity_alive(w, id)) continue;
        if ((w->entities[id].mask & req) == req) ids[n++] = id;
    }
    /* Test every pair */
    for (u32 i = 0; i < n; i++) {
        for (u32 j = i + 1; j < n; j++) {
            TransformComponent *ta = VFE_TRANSFORM(w, ids[i]);
            TransformComponent *tb = VFE_TRANSFORM(w, ids[j]);
            RigidBodyComponent *ra = VFE_RIGIDBODY(w, ids[i]);
            RigidBodyComponent *rb = VFE_RIGIDBODY(w, ids[j]);
            if (!ta || !tb || !ra || !rb) continue;
            if (ra->is_static && rb->is_static) continue;
            resolve_pair(w, ids[i], ta, ra, ids[j], tb, rb);
        }
    }
}

/* ── Public step function ────────────────────────────────────────────── */

void vfe_physics_step(World *w, float dt) {
    ComponentMask req = VFE_MASK_ADD(VFE_MASK_ADD(0, VFE_COMP_TRANSFORM),
                                      VFE_COMP_RIGID_BODY);
    PhysCtx ctx = { w, dt };
    vfe_foreach_entity(w, req, 0, integrate_entity, &ctx);
    resolve_collisions(w);
}

/* ── Ray-AABB ────────────────────────────────────────────────────────── */

float vfe_ray_aabb(Vec3 o, Vec3 d,
                   Vec3 bmin, Vec3 bmax,
                   Vec3 *hit_normal) {
    float tmin = -1e9f, tmax = 1e9f;
    int   hit_axis = -1;
    float axes_o[3] = {o.x,o.y,o.z};
    float axes_d[3] = {d.x,d.y,d.z};
    float axes_mn[3]= {bmin.x,bmin.y,bmin.z};
    float axes_mx[3]= {bmax.x,bmax.y,bmax.z};

    for (int i = 0; i < 3; i++) {
        if (fabsf(axes_d[i]) < 1e-8f) {
            if (axes_o[i] < axes_mn[i] || axes_o[i] > axes_mx[i]) return -1.0f;
        } else {
            float inv = 1.0f / axes_d[i];
            float t0  = (axes_mn[i] - axes_o[i]) * inv;
            float t1  = (axes_mx[i] - axes_o[i]) * inv;
            if (t0 > t1) { float tmp = t0; t0 = t1; t1 = tmp; }
            if (t0 > tmin) { tmin = t0; hit_axis = i; }
            if (t1 < tmax)   tmax = t1;
            if (tmin > tmax) return -1.0f;
        }
    }
    if (tmin < 0) return -1.0f;
    if (hit_normal && hit_axis >= 0) {
        float n[3] = {0,0,0};
        n[hit_axis] = (axes_d[hit_axis] < 0) ? 1.0f : -1.0f;
        *hit_normal = (Vec3){n[0], n[1], n[2]};
    }
    return tmin;
}

/* ── Sphere broad-phase query ────────────────────────────────────────── */

u32 vfe_query_sphere(World *w, Vec3 center, float radius,
                     EntityID *out, u32 out_max) {
    u32 count = 0;
    ComponentMask req = VFE_MASK_ADD(VFE_MASK_ADD(0, VFE_COMP_TRANSFORM),
                                      VFE_COMP_RIGID_BODY);
    for (EntityID id = 1; id <= w->highest_id && count < out_max; id++) {
        if (!vfe_entity_alive(w, id)) continue;
        if ((w->entities[id].mask & req) != req) continue;
        TransformComponent *t = VFE_TRANSFORM(w, id);
        if (!t) continue;
        float dx = t->position.x - center.x;
        float dy = t->position.y - center.y;
        float dz = t->position.z - center.z;
        if (dx*dx + dy*dy + dz*dz <= radius*radius)
            out[count++] = id;
    }
    return count;
}
