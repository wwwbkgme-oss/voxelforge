/* VFE — High-resolution timer and frame-rate limiter */
#pragma once
#ifndef VFE_TIMER_H
#define VFE_TIMER_H
#include "types.h"
#include <SDL2/SDL.h>

typedef struct {
    u64   now_ticks;
    u64   last_ticks;
    u64   freq;
    f64   delta;      /* seconds elapsed since last frame   */
    f64   time;       /* total seconds since engine start   */
    u32   frame;      /* frame counter                      */
    f32   fps;        /* smoothed frames-per-second         */
    u32   max_fps;    /* 0 = unlimited                      */
    f64   acc_fps;    /* accumulator for fps smoothing      */
    u32   acc_frames;
} VFE_Timer;

void vfe_timer_init (VFE_Timer *t, u32 max_fps);
void vfe_timer_tick (VFE_Timer *t);   /* call once per frame at top of loop */
void vfe_timer_limit(VFE_Timer *t);   /* busy-wait or sleep to cap FPS      */
#endif
