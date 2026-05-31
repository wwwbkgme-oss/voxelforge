/* VFE — Audio implementation  (original C99, SDL_mixer) */
#include "audio.h"
#include "../core/log.h"
#include <string.h>

/* SDL_mixer is optional — compile with VFE_NO_AUDIO to disable */
#ifndef VFE_NO_AUDIO
#include <SDL2/SDL_mixer.h>
#endif

bool vfe_audio_init(VFE_Audio *a) {
    memset(a, 0, sizeof(*a));
    a->master_volume = 1.0f;
    a->frequency  = 44100;
    a->channels   = 2;
#ifndef VFE_NO_AUDIO
    if (Mix_OpenAudio(a->frequency, MIX_DEFAULT_FORMAT, a->channels, 2048) != 0) {
        VFE_WARN("SDL_mixer init: %s (audio disabled)", Mix_GetError());
        return false;
    }
    Mix_AllocateChannels(16);
    VFE_INFO("Audio initialised (%dHz, %d-channel)", a->frequency, a->channels);
#else
    VFE_INFO("Audio disabled (VFE_NO_AUDIO)");
#endif
    a->initialised = true;
    return true;
}

void vfe_audio_close(VFE_Audio *a) {
#ifndef VFE_NO_AUDIO
    if (a->initialised) Mix_CloseAudio();
#endif
    a->initialised = false;
}

void vfe_audio_set_vol(VFE_Audio *a, float v) {
    if (v < 0) v = 0;
    if (v > 1) v = 1;
    a->master_volume = v;
#ifndef VFE_NO_AUDIO
    Mix_MasterVolume((int)(v * MIX_MAX_VOLUME));
#endif
}

bool vfe_audio_play_sfx(VFE_Audio *a, const char *path) {
    if (!a->initialised || !path) return false;
#ifndef VFE_NO_AUDIO
    Mix_Chunk *chunk = Mix_LoadWAV(path);
    if (!chunk) { VFE_WARN("SFX load '%s': %s", path, Mix_GetError()); return false; }
    Mix_PlayChannel(-1, chunk, 0);
    /* Note: chunk leaks here; production code would use a cache. */
#endif
    return true;
}

bool vfe_audio_play_music(VFE_Audio *a, const char *path, bool loop) {
    if (!a->initialised || !path) return false;
#ifndef VFE_NO_AUDIO
    Mix_Music *mus = Mix_LoadMUS(path);
    if (!mus) { VFE_WARN("Music load '%s': %s", path, Mix_GetError()); return false; }
    Mix_PlayMusic(mus, loop ? -1 : 1);
#endif
    return true;
}

void vfe_audio_stop_music(VFE_Audio *a) {
    if (!a->initialised) return;
#ifndef VFE_NO_AUDIO
    Mix_HaltMusic();
#endif
}
