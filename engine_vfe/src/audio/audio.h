/* VFE — Audio subsystem (SDL_mixer wrapper) */
#pragma once
#ifndef VFE_AUDIO_H
#define VFE_AUDIO_H
#include "../core/types.h"
#include <stdbool.h>

typedef struct {
    bool  initialised;
    float master_volume;  /* [0, 1] */
    int   frequency;
    int   channels;
} VFE_Audio;

bool  vfe_audio_init   (VFE_Audio *a);
void  vfe_audio_close  (VFE_Audio *a);
void  vfe_audio_set_vol(VFE_Audio *a, float v);
bool  vfe_audio_play_sfx  (VFE_Audio *a, const char *path);
bool  vfe_audio_play_music(VFE_Audio *a, const char *path, bool loop);
void  vfe_audio_stop_music(VFE_Audio *a);
#endif
