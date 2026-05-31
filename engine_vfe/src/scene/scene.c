/* VFE — Scene loader/saver  (original C99, uses cJSON) */
#include "scene.h"
#include "../libs/cjson.h"
#include "../core/log.h"
#include "../voxel/vox_loader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── Helpers ─────────────────────────────────────────────────────────── */

static Vec3 json_vec3(cJSON *arr, Vec3 def) {
    if (!arr || !cJSON_IsArray(arr) || cJSON_GetArraySize(arr) < 3) return def;
    return (Vec3){
        (float)cJSON_GetArrayItem(arr,0)->valuedouble,
        (float)cJSON_GetArrayItem(arr,1)->valuedouble,
        (float)cJSON_GetArrayItem(arr,2)->valuedouble
    };
}
static cJSON *vec3_json(Vec3 v) {
    cJSON *a = cJSON_CreateArray();
    cJSON_AddItemToArray(a, cJSON_CreateNumber((double)v.x));
    cJSON_AddItemToArray(a, cJSON_CreateNumber((double)v.y));
    cJSON_AddItemToArray(a, cJSON_CreateNumber((double)v.z));
    return a;
}
static float json_f(cJSON *obj, const char *key, float def) {
    cJSON *v = cJSON_GetObjectItem(obj, key);
    return v ? (float)v->valuedouble : def;
}
static const char *json_s(cJSON *obj, const char *key, const char *def) {
    cJSON *v = cJSON_GetObjectItem(obj, key);
    return (v && v->valuestring) ? v->valuestring : def;
}

/* ── Load ────────────────────────────────────────────────────────────── */

bool vfe_scene_load(World *w, const char *path, SceneMetadata *meta_out) {
    FILE *f = fopen(path, "r");
    if (!f) { VFE_ERROR("vfe_scene_load: cannot open '%s'", path); return false; }
    fseek(f, 0, SEEK_END); long len = ftell(f); rewind(f);
    char *buf = (char *)malloc((size_t)len + 1);
    if (!buf) { fclose(f); return false; }
    fread(buf, 1, (size_t)len, f); buf[len] = '\0'; fclose(f);

    cJSON *root = cJSON_Parse(buf);
    free(buf);
    if (!root) { VFE_ERROR("vfe_scene_load: JSON parse error in '%s'", path); return false; }

    /* Scene metadata */
    cJSON *data = cJSON_GetObjectItem(root, "data");
    if (meta_out && data) {
        meta_out->background_color = json_vec3(cJSON_GetObjectItem(data,"backgroundColor"),
                                               (Vec3){0.05f,0.1f,0.2f});
        meta_out->sun_direction    = json_vec3(cJSON_GetObjectItem(data,"sunDirection"),
                                               (Vec3){0.5f,-1.0f,-0.5f});
        meta_out->sun_color        = json_vec3(cJSON_GetObjectItem(data,"sunColor"),
                                               (Vec3){1.0f,0.95f,0.85f});
        meta_out->ambient_intensity= json_f(data,"ambientIntensity",0.3f);
        strncpy(meta_out->palette_path,
                json_s(data,"palettePath",""),
                sizeof(meta_out->palette_path)-1);
    }

    /* Entities */
    cJSON *entities = cJSON_GetObjectItem(root, "entities");
    if (!entities || !cJSON_IsArray(entities)) {
        cJSON_Delete(root); return true; /* empty scene is valid */
    }

    cJSON *ent_json = NULL;
    cJSON_ArrayForEach(ent_json, entities) {
        EntityID id = vfe_entity_create(w);
        if (id == VFE_INVALID_ENTITY) break;

        /* Transform */
        cJSON *tr = cJSON_GetObjectItem(ent_json, "Transform");
        if (tr) {
            TransformComponent *t = (TransformComponent *)vfe_comp_add(w, id, VFE_COMP_TRANSFORM);
            t->position = json_vec3(cJSON_GetObjectItem(tr,"position"), vec3_zero());
            t->rotation = json_vec3(cJSON_GetObjectItem(tr,"rotation"), vec3_zero());
            Vec3 sc = json_vec3(cJSON_GetObjectItem(tr,"scale"), (Vec3){1,1,1});
            t->scale    = sc;
        }

        /* VoxelModel */
        cJSON *vm = cJSON_GetObjectItem(ent_json, "VoxelModel");
        if (vm) {
            VoxelModelComponent *vmc = (VoxelModelComponent *)
                                       vfe_comp_add(w, id, VFE_COMP_VOXEL_MODEL);
            const char *mp = json_s(vm,"modelPath","");
            const char *mn = json_s(vm,"modelName","");
            char full[512];
            snprintf(full, sizeof(full), "%s%s", mp, mn);
            strncpy(vmc->path, full, sizeof(vmc->path)-1);
            vmc->visible = true;
            /* Lazy-load: asset will be loaded by renderer on first draw */
            VoxelPalette pal;
            vmc->asset = vfe_asset_load_vox(full, &pal);
        }

        /* PointLight */
        cJSON *pl = cJSON_GetObjectItem(ent_json, "PointLight");
        if (pl) {
            PointLightComponent *plc = (PointLightComponent *)
                                        vfe_comp_add(w, id, VFE_COMP_POINT_LIGHT);
            plc->color     = json_vec3(cJSON_GetObjectItem(pl,"color"),(Vec3){1,1,1});
            plc->intensity = json_f(pl,"intensity",1.0f);
            plc->radius    = json_f(pl,"range",100.0f);
            plc->hue_shift = json_f(pl,"hueShift",0.0f);
        }

        /* RigidBody */
        cJSON *rb = cJSON_GetObjectItem(ent_json, "RigidBody");
        if (rb) {
            RigidBodyComponent *rbc = (RigidBodyComponent *)
                                       vfe_comp_add(w, id, VFE_COMP_RIGID_BODY);
            rbc->mass        = json_f(rb,"mass",1.0f);
            rbc->restitution = json_f(rb,"bounciness",0.2f);
            rbc->use_gravity = cJSON_IsTrue(cJSON_GetObjectItem(rb,"useGravity"));
            rbc->is_static   = cJSON_IsTrue(cJSON_GetObjectItem(rb,"isStatic"));
            rbc->half_extents= (Vec3){0.5f,0.5f,0.5f};
        }

        /* LuaScript */
        cJSON *sc = cJSON_GetObjectItem(ent_json, "LuaScript");
        if (sc) {
            ScriptComponent *scc = (ScriptComponent *)
                                    vfe_comp_add(w, id, VFE_COMP_SCRIPT);
            const char *sp = json_s(sc,"scriptPath",".");
            const char *sn = json_s(sc,"scriptName","script.lua");
            snprintf(scc->path, sizeof(scc->path), "%s/%s", sp, sn);
        }
    }

    cJSON_Delete(root);
    VFE_INFO("Scene loaded: '%s'", path);
    return true;
}

/* ── Save ────────────────────────────────────────────────────────────── */

bool vfe_scene_save(const World *w, const SceneMetadata *meta, const char *path) {
    cJSON *root = cJSON_CreateObject();

    /* data block */
    if (meta) {
        cJSON *data = cJSON_CreateObject();
        cJSON_AddItemToObject(data,"backgroundColor", vec3_json(meta->background_color));
        cJSON_AddItemToObject(data,"sunDirection",    vec3_json(meta->sun_direction));
        cJSON_AddItemToObject(data,"sunColor",        vec3_json(meta->sun_color));
        cJSON_AddNumberToObject(data,"ambientIntensity",(double)meta->ambient_intensity);
        cJSON_AddStringToObject(data,"palettePath",   meta->palette_path);
        cJSON_AddItemToObject(root,"data",data);
    }

    cJSON *entities = cJSON_CreateArray();
    for (EntityID id = 1; id <= w->highest_id; id++) {
        if (!vfe_entity_alive(w,id)) continue;
        if (w->entities[id].parent != VFE_INVALID_ENTITY) continue; /* skip children */

        cJSON *ent = cJSON_CreateObject();

        if (vfe_comp_has(w,id,VFE_COMP_TRANSFORM)) {
            TransformComponent *t = VFE_TRANSFORM((World*)w,id);
            cJSON *tr = cJSON_CreateObject();
            cJSON_AddItemToObject(tr,"position", vec3_json(t->position));
            cJSON_AddItemToObject(tr,"rotation", vec3_json(t->rotation));
            cJSON_AddItemToObject(tr,"scale",    vec3_json(t->scale));
            cJSON_AddItemToObject(ent,"Transform",tr);
        }
        if (vfe_comp_has(w,id,VFE_COMP_VOXEL_MODEL)) {
            VoxelModelComponent *vm = VFE_VOXEL((World*)w,id);
            cJSON *vmj = cJSON_CreateObject();
            cJSON_AddStringToObject(vmj,"path",    vm->path);
            cJSON_AddBoolToObject  (vmj,"visible", vm->visible);
            cJSON_AddItemToObject(ent,"VoxelModel",vmj);
        }
        if (vfe_comp_has(w,id,VFE_COMP_POINT_LIGHT)) {
            PointLightComponent *pl = VFE_LIGHT((World*)w,id);
            cJSON *plj = cJSON_CreateObject();
            cJSON_AddItemToObject(plj,"color", vec3_json(pl->color));
            cJSON_AddNumberToObject(plj,"intensity",(double)pl->intensity);
            cJSON_AddNumberToObject(plj,"range",    (double)pl->radius);
            cJSON_AddItemToObject(ent,"PointLight",plj);
        }
        cJSON_AddItemToArray(entities,ent);
    }
    cJSON_AddItemToObject(root,"entities",entities);

    char *json_str = cJSON_Print(root);
    cJSON_Delete(root);
    if (!json_str) return false;

    FILE *f = fopen(path,"w");
    bool ok = false;
    if (f) { fputs(json_str,f); fclose(f); ok=true;
             VFE_INFO("Scene saved: '%s'",path); }
    else     VFE_ERROR("vfe_scene_save: cannot write '%s'",path);
    free(json_str);
    return ok;
}

void vfe_scene_clear(World *w) {
    for (EntityID id = 1; id <= w->highest_id; id++)
        if (vfe_entity_alive(w,id)) vfe_entity_destroy(w,id);
    w->entity_count = 0;
    w->highest_id   = 0;
}
