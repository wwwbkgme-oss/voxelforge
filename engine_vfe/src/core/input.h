/* VFE — Input subsystem */
#pragma once
#ifndef VFE_INPUT_H
#define VFE_INPUT_H
#include "types.h"
#include <SDL2/SDL.h>

typedef struct {
    const Uint8 *keys_now;        /* SDL scan-code state this frame  */
    Uint8  keys_prev[SDL_NUM_SCANCODES]; /* previous frame           */

    i32  mouse_x, mouse_y;        /* window-relative pixel position  */
    i32  mouse_dx, mouse_dy;      /* delta since last frame          */
    bool mouse_btn[6];
    bool mouse_btn_prev[6];
    i32  scroll;                  /* +1 up / -1 down / 0             */

    bool text_input;
    char text_buf[32];
} InputState;

void  vfe_input_init(InputState *inp);
void  vfe_input_begin_frame(InputState *inp);
void  vfe_input_process_event(InputState *inp, const SDL_Event *ev);

/* Query helpers */
bool  vfe_key_down    (const InputState *inp, SDL_Scancode sc);
bool  vfe_key_pressed (const InputState *inp, SDL_Scancode sc); /* leading edge  */
bool  vfe_key_released(const InputState *inp, SDL_Scancode sc); /* trailing edge */
bool  vfe_mouse_down  (const InputState *inp, int btn);
bool  vfe_mouse_pressed (const InputState *inp, int btn);
bool  vfe_mouse_released(const InputState *inp, int btn);
#endif
