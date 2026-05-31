/* VFE — Logger implementation */
#include "log.h"
#include <stdio.h>
#include <stdarg.h>
#include <time.h>
#include <string.h>

static FILE    *g_log_file  = NULL;
static LogLevel g_min_level = LOG_DEBUG;

static const char *level_str[] = { "DEBUG", "INFO ", "WARN ", "ERROR" };
static const char *level_col[] = { "\033[36m", "\033[32m", "\033[33m", "\033[31m" };
#define COL_RESET "\033[0m"

void vfe_log_init(const char *filepath, LogLevel min_level) {
    g_min_level = min_level;
    if (filepath && strlen(filepath) > 0) {
        g_log_file = fopen(filepath, "w");
    }
}

void vfe_log_close(void) {
    if (g_log_file) { fclose(g_log_file); g_log_file = NULL; }
}

void vfe_log_write(LogLevel level, const char *file, int line,
                   const char *fmt, ...) {
    if (level < g_min_level) return;

    /* Timestamp */
    time_t t = time(NULL);
    struct tm *tm_info = localtime(&t);
    char ts[20];
    strftime(ts, sizeof(ts), "%H:%M:%S", tm_info);

    /* Shorten file path */
    const char *short_file = strrchr(file, '/');
    short_file = short_file ? short_file + 1 : file;

    va_list args;
    va_start(args, fmt);

    /* Console output with colour */
    fprintf(stderr, "%s%s%s [%s:%d] ",
            level_col[level], level_str[level], COL_RESET, short_file, line);
    vfprintf(stderr, fmt, args);
    fputc('\n', stderr);

    /* File output without ANSI codes */
    if (g_log_file) {
        va_end(args);
        va_start(args, fmt);
        fprintf(g_log_file, "%s %s [%s:%d] ", ts, level_str[level],
                short_file, line);
        vfprintf(g_log_file, fmt, args);
        fputc('\n', g_log_file);
        fflush(g_log_file);
    }
    va_end(args);
}
