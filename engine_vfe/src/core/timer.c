/* VFE — Timer implementation */
#include "timer.h"

void vfe_timer_init(VFE_Timer *t, u32 max_fps) {
    t->freq       = SDL_GetPerformanceFrequency();
    t->now_ticks  = SDL_GetPerformanceCounter();
    t->last_ticks = t->now_ticks;
    t->delta      = 0.0;
    t->time       = 0.0;
    t->frame      = 0;
    t->fps        = 0.0f;
    t->max_fps    = max_fps;
    t->acc_fps    = 0.0;
    t->acc_frames = 0;
}

void vfe_timer_tick(VFE_Timer *t) {
    t->last_ticks = t->now_ticks;
    t->now_ticks  = SDL_GetPerformanceCounter();
    t->delta      = (f64)(t->now_ticks - t->last_ticks) / (f64)t->freq;
    /* Clamp delta to avoid spiral-of-death on large pauses */
    if (t->delta > 0.25) t->delta = 0.25;
    t->time  += t->delta;
    t->frame++;
    /* FPS smoothing over 0.5 s window */
    t->acc_fps    += t->delta;
    t->acc_frames++;
    if (t->acc_fps >= 0.5) {
        t->fps        = (f32)(t->acc_frames / t->acc_fps);
        t->acc_fps    = 0.0;
        t->acc_frames = 0;
    }
}

void vfe_timer_limit(VFE_Timer *t) {
    if (t->max_fps == 0) return;
    f64 target = 1.0 / (f64)t->max_fps;
    f64 elapsed;
    do {
        u64 now = SDL_GetPerformanceCounter();
        elapsed = (f64)(now - t->now_ticks) / (f64)t->freq;
    } while (elapsed < target);
}
