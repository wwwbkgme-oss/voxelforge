/* VFE — GLSL shader loader and cache */
#pragma once
#ifndef VFE_SHADER_H
#define VFE_SHADER_H

#include "../core/types.h"
#include <GL/glew.h>

typedef GLuint ShaderID;
#define VFE_SHADER_INVALID 0u

/* Compile vert + frag source into a linked program. */
ShaderID vfe_shader_build(const char *vert_src, const char *frag_src);

/* Load vert/frag from files and link. */
ShaderID vfe_shader_load_files(const char *vert_path, const char *frag_path);

void     vfe_shader_destroy(ShaderID id);
void     vfe_shader_use    (ShaderID id);

/* Uniform setters */
void vfe_shader_seti(ShaderID id, const char *name, int v);
void vfe_shader_setf(ShaderID id, const char *name, float v);
void vfe_shader_set2f(ShaderID id, const char *name, float x, float y);
void vfe_shader_set3f(ShaderID id, const char *name, float x, float y, float z);
void vfe_shader_set4f(ShaderID id, const char *name, float x, float y, float z, float w);
void vfe_shader_setm4(ShaderID id, const char *name, const float *m16);
#endif
