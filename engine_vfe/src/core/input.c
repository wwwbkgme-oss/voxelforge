/* VFE — Input subsystem implementation */
#include "input.h"
#include <string.h>

void vfe_input_init(InputState *inp) {
    memset(inp, 0, sizeof(*inp));
    inp->keys_now = SDL_GetKeyboardState(NULL);
}

void vfe_input_begin_frame(InputState *inp) {
    /* Save previous frame state */
    memcpy(inp->keys_prev, inp->keys_now, SDL_NUM_SCANCODES);
    memcpy(inp->mouse_btn_prev, inp->mouse_btn, sizeof(inp->mouse_btn));
    inp->mouse_dx = inp->mouse_dy = inp->scroll = 0;
    inp->text_input = false;
    inp->text_buf[0] = '\0';
}

void vfe_input_process_event(InputState *inp, const SDL_Event *ev) {
    switch (ev->type) {
    case SDL_MOUSEMOTION:
        inp->mouse_x  = ev->motion.x;
        inp->mouse_y  = ev->motion.y;
        inp->mouse_dx = ev->motion.xrel;
        inp->mouse_dy = ev->motion.yrel;
        break;
    case SDL_MOUSEBUTTONDOWN:
        if (ev->button.button < 6) inp->mouse_btn[ev->button.button] = true;
        break;
    case SDL_MOUSEBUTTONUP:
        if (ev->button.button < 6) inp->mouse_btn[ev->button.button] = false;
        break;
    case SDL_MOUSEWHEEL:
        inp->scroll = (ev->wheel.y > 0) ? 1 : (ev->wheel.y < 0) ? -1 : 0;
        break;
    case SDL_TEXTINPUT:
        strncpy(inp->text_buf, ev->text.text, sizeof(inp->text_buf)-1);
        inp->text_input = true;
        break;
    default: break;
    }
}

bool vfe_key_down(const InputState *inp, SDL_Scancode sc) {
    return inp->keys_now[sc] != 0;
}
bool vfe_key_pressed(const InputState *inp, SDL_Scancode sc) {
    return inp->keys_now[sc] && !inp->keys_prev[sc];
}
bool vfe_key_released(const InputState *inp, SDL_Scancode sc) {
    return !inp->keys_now[sc] && inp->keys_prev[sc];
}
bool vfe_mouse_down(const InputState *inp, int btn) {
    return btn < 6 && inp->mouse_btn[btn];
}
bool vfe_mouse_pressed(const InputState *inp, int btn) {
    return btn < 6 && inp->mouse_btn[btn] && !inp->mouse_btn_prev[btn];
}
bool vfe_mouse_released(const InputState *inp, int btn) {
    return btn < 6 && !inp->mouse_btn[btn] && inp->mouse_btn_prev[btn];
}
