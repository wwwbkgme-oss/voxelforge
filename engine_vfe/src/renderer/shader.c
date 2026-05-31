/* VFE — Shader implementation */
#include "shader.h"
#include "../core/log.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

static GLuint compile_stage(GLenum type, const char *src) {
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, NULL);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[512];
        glGetShaderInfoLog(s, sizeof(log), NULL, log);
        VFE_ERROR("Shader compile: %s", log);
        glDeleteShader(s);
        return 0;
    }
    return s;
}

ShaderID vfe_shader_build(const char *vert_src, const char *frag_src) {
    GLuint vs = compile_stage(GL_VERTEX_SHADER,   vert_src);
    GLuint fs = compile_stage(GL_FRAGMENT_SHADER, frag_src);
    if (!vs || !fs) { glDeleteShader(vs); glDeleteShader(fs); return 0; }

    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glLinkProgram(prog);
    glDeleteShader(vs);
    glDeleteShader(fs);

    GLint ok = 0;
    glGetProgramiv(prog, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[512];
        glGetProgramInfoLog(prog, sizeof(log), NULL, log);
        VFE_ERROR("Shader link: %s", log);
        glDeleteProgram(prog);
        return 0;
    }
    return prog;
}

static char *read_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { VFE_ERROR("Cannot read shader '%s'", path); return NULL; }
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    rewind(f);
    char *buf = (char *)malloc((size_t)len + 1);
    if (buf) { fread(buf, 1, (size_t)len, f); buf[len] = '\0'; }
    fclose(f);
    return buf;
}

ShaderID vfe_shader_load_files(const char *vp, const char *fp) {
    char *vs = read_file(vp), *fs = read_file(fp);
    ShaderID id = (vs && fs) ? vfe_shader_build(vs, fs) : 0;
    free(vs); free(fs);
    return id;
}

void vfe_shader_destroy(ShaderID id) { if (id) glDeleteProgram(id); }
void vfe_shader_use    (ShaderID id) { glUseProgram(id); }

void vfe_shader_seti (ShaderID id, const char *n, int v)
    { glUniform1i(glGetUniformLocation(id,n), v); }
void vfe_shader_setf (ShaderID id, const char *n, float v)
    { glUniform1f(glGetUniformLocation(id,n), v); }
void vfe_shader_set2f(ShaderID id, const char *n, float x, float y)
    { glUniform2f(glGetUniformLocation(id,n), x, y); }
void vfe_shader_set3f(ShaderID id, const char *n, float x, float y, float z)
    { glUniform3f(glGetUniformLocation(id,n), x, y, z); }
void vfe_shader_set4f(ShaderID id, const char *n, float x, float y, float z, float w)
    { glUniform4f(glGetUniformLocation(id,n), x, y, z, w); }
void vfe_shader_setm4(ShaderID id, const char *n, const float *m)
    { glUniformMatrix4fv(glGetUniformLocation(id,n), 1, GL_FALSE, m); }
