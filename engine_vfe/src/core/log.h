/*  VFE — Logging subsystem  */
#pragma once
#ifndef VFE_LOG_H
#define VFE_LOG_H
#include <stdio.h>

typedef enum { LOG_DEBUG=0, LOG_INFO, LOG_WARN, LOG_ERROR } LogLevel;

void vfe_log_init(const char *filepath, LogLevel min_level);
void vfe_log_close(void);
void vfe_log_write(LogLevel level, const char *file, int line, const char *fmt, ...);

#define VFE_DEBUG(...)  vfe_log_write(LOG_DEBUG, __FILE__, __LINE__, __VA_ARGS__)
#define VFE_INFO(...)   vfe_log_write(LOG_INFO,  __FILE__, __LINE__, __VA_ARGS__)
#define VFE_WARN(...)   vfe_log_write(LOG_WARN,  __FILE__, __LINE__, __VA_ARGS__)
#define VFE_ERROR(...)  vfe_log_write(LOG_ERROR, __FILE__, __LINE__, __VA_ARGS__)
#endif
