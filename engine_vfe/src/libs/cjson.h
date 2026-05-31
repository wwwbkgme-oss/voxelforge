/*
 * VFE uses cJSON for JSON parsing.
 * cJSON is a standalone public-domain / MIT licensed C JSON library
 * by Dave Gamble: https://github.com/DaveGamble/cJSON
 *
 * To set up:
 *   cmake --build . --target fetch_cjson
 * or manually:
 *   curl -Lo src/libs/cjson.h  https://raw.githubusercontent.com/DaveGamble/cJSON/master/cJSON.h
 *   curl -Lo src/libs/cjson.c  https://raw.githubusercontent.com/DaveGamble/cJSON/master/cJSON.c
 *
 * CMakeLists.txt already handles FetchContent automatically.
 */
#pragma once
#ifndef CJSON_H           /* guard in case the real header is already present */

/* Minimal forward declarations used by VFE — the real header is fetched at build time */
struct cJSON;
typedef struct cJSON cJSON;

cJSON *cJSON_Parse              (const char *value);
cJSON *cJSON_CreateObject       (void);
cJSON *cJSON_CreateArray        (void);
cJSON *cJSON_CreateNumber       (double num);
cJSON *cJSON_CreateString       (const char *string);
cJSON *cJSON_CreateBool         (int boolean);
void   cJSON_Delete             (cJSON *item);
char  *cJSON_Print              (const cJSON *item);
char  *cJSON_PrintUnformatted   (const cJSON *item);
int    cJSON_GetArraySize       (const cJSON *array);
cJSON *cJSON_GetArrayItem       (const cJSON *array, int index);
cJSON *cJSON_GetObjectItem      (const cJSON *object, const char *string);
int    cJSON_IsArray            (const cJSON *item);
int    cJSON_IsTrue             (const cJSON *item);
double cJSON_GetNumberValue     (const cJSON *item);
char  *cJSON_GetStringValue     (const cJSON *item);
void   cJSON_AddItemToArray     (cJSON *array, cJSON *item);
void   cJSON_AddItemToObject    (cJSON *object, const char *string, cJSON *item);
cJSON *cJSON_AddStringToObject  (cJSON *object, const char *name, const char *string);
cJSON *cJSON_AddNumberToObject  (cJSON *object, const char *name, double number);
cJSON *cJSON_AddBoolToObject    (cJSON *object, const char *name, int boolean);

/* Iterator macro */
#define cJSON_ArrayForEach(element, array) \
    for (element = (array != NULL) ? (array)->child : NULL; element != NULL; element = element->next)

#define CJSON_H
#endif /* CJSON_H */
