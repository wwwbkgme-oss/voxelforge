#include "EngineCore.h"

/* ---------------------------------------------------------------------------
 * VoxelForge Engine — Core initialisation
 * Rebranded from Vopix Engine (original: KellerMartins/PixelVoxels)
 * ---------------------------------------------------------------------------
 */

engineCore Core;
engineTime Time;
engineScreen Screen;

int exitGame = 0;

void ExitGame(){
	exitGame = 1;
}

int GameExited(){
	return exitGame;
}

int InitCore(){
    exitGame = 0;

	srand( (unsigned)time(NULL) );

    /* -----------------------------------------------------------------------
     * Headless mode: use SDL's built-in offscreen video driver so the engine
     * runs without any display.  Set the environment variable before SDL_Init.
     * ----------------------------------------------------------------------- */
    if(Core.isHeadless){
        SDL_setenv("SDL_VIDEODRIVER", "offscreen", 1);
        SDL_setenv("DISPLAY", "", 1);
        PrintLog(Info, "EngineCore: headless mode — using offscreen SDL driver\n");
    }

	if(IMG_Init(IMG_INIT_PNG) != IMG_INIT_PNG){
		PrintLog(Error,"SDL Image could not initialize! \n");
        return 0;
	}

	if(TTF_Init()==-1) {
    	PrintLog(Error,"TTF_Init could not initialize! %s\n", TTF_GetError());
        return 0;
	}
	SDL_SetHint(SDL_HINT_WINDOWS_DISABLE_THREAD_NAMING, "1");
    if(SDL_Init(SDL_INIT_EVERYTHING) < 0)
	{
        PrintLog(Error,"SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return 0;
    }

    Uint32 windowFlags = SDL_WINDOW_OPENGL;
    if(Core.isHeadless){
        windowFlags |= SDL_WINDOW_HIDDEN;
    }else{
        windowFlags |= SDL_WINDOW_SHOWN;
    }

	Core.window = SDL_CreateWindow(
        "VoxelForge Engine",
        SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
        Screen.windowWidth, Screen.windowHeight,
        windowFlags);

	if(Core.window == NULL){
		PrintLog(Error,"Window could not be created! SDL_Error %s\n", SDL_GetError());
        return 0;
	}

    return 1;
}

void InitTime(){
    Time.frameTicks = 0;
	Time.msTime = 0;
    Time.deltaTime = 0;

    Time.nowCounter = SDL_GetPerformanceCounter();
	Time.lastCounter = 0;
}

void InitScreen(int windowWidth, int windowHeight, int scale, int maxFPS){
    Screen.windowWidth = windowWidth;
    Screen.windowHeight = windowHeight;
    Screen.gameScale = scale;
    Screen.maxFPS = maxFPS;

    //Define internal game resolution
	Screen.gameWidth = Screen.windowWidth/Screen.gameScale;
	Screen.gameHeight = Screen.windowHeight/Screen.gameScale;
}

void UpdateTime(){
	//Start elapsed ms time and delta time calculation
    Time.frameTicks = SDL_GetTicks();
	Time.lastCounter = Time.nowCounter;
	Time.nowCounter = SDL_GetPerformanceCounter();
	Time.deltaTime = (double)((Time.nowCounter - Time.lastCounter)*1000 / SDL_GetPerformanceFrequency() )*0.001;
}

void WaitUntilNextFrame(){
	Time.msTime = SDL_GetTicks()-Time.frameTicks;
	if(Screen.maxFPS == 0) return;
    while( SDL_GetTicks()-Time.frameTicks <  (1000/Screen.maxFPS) ){ }
}

/* ---------------------------------------------------------------------------
 * ExportScreenshot — read the current OpenGL front-buffer and write to PNG.
 * Works both in normal and headless mode.
 * Returns 1 on success, 0 on failure.
 * --------------------------------------------------------------------------- */
int ExportScreenshot(const char* outputPath){
    int w = Screen.gameWidth;
    int h = Screen.gameHeight;
    unsigned char *pixels = malloc(4 * w * h);
    if(!pixels){
        PrintLog(Error,"ExportScreenshot: out of memory\n");
        return 0;
    }

    glReadBuffer(GL_FRONT);
    glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, pixels);

    /* OpenGL y-axis is bottom-up; SDL/PNG is top-down — flip vertically */
    SDL_Surface *surface = SDL_CreateRGBSurfaceFrom(
        pixels, w, h, 32, w * 4,
        0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000);

    SDL_Surface *flipped = SDL_CreateRGBSurface(0, w, h, 32,
        0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000);

    if(!surface || !flipped){
        PrintLog(Error,"ExportScreenshot: SDL surface creation failed: %s\n", SDL_GetError());
        free(pixels);
        return 0;
    }

    for(int row = 0; row < h; row++){
        SDL_Rect srcRect = {0, h - 1 - row, w, 1};
        SDL_Rect dstRect = {0, row, w, 1};
        SDL_BlitSurface(surface, &srcRect, flipped, &dstRect);
    }

    int result = IMG_SavePNG(flipped, outputPath);
    SDL_FreeSurface(surface);
    SDL_FreeSurface(flipped);
    free(pixels);

    if(result != 0){
        PrintLog(Error,"ExportScreenshot: IMG_SavePNG failed: %s\n", IMG_GetError());
        return 0;
    }
    PrintLog(Info,"ExportScreenshot: saved → %s\n", outputPath);
    return 1;
}
