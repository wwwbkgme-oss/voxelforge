/*
 * VoxelForge Engine — main entry point
 *
 * Rebranded and extended from Vopix Engine (original: KellerMartins/PixelVoxels)
 *
 * Usage:
 *   voxelforge [options] [scene_path]
 *
 * Options:
 *   --headless          Run without a display window (offscreen SDL driver)
 *   --screenshot <path> Export one frame to <path>.png then exit
 *   --scene <path>      Load scene file at <path> (default: Assets/default.scene)
 *   --width <n>         Window/framebuffer width  (default: 1280)
 *   --height <n>        Window/framebuffer height (default: 720)
 *   --scale <n>         Pixel scale divisor       (default: 1)
 *   --fps <n>           Max FPS cap               (default: 60)
 */

#include "Engine.h"
#include "utils.h"

#include "Components/VoxelModel.h"
#include "Components/Transform.h"
#include "Components/RigidBody.h"
#include "Components/PointLight.h"
#include "Components/LuaScript.h"

#include "Systems/VoxelRenderer.h"
#include "Systems/PointLighting.h"
#include "Systems/Shadows.h"
#include "Systems/VoxelModification.h"
#include "Systems/VoxelPhysics.h"
#include "Systems/Editor.h"
#include "Systems/UIRenderer.h"
#include "Systems/LuaSystem.h"

#include <string.h>
#include <stdio.h>

extern engineTime Time;
extern engineCore Core;
extern engineScreen Screen;
extern engineRendering Rendering;
extern engineECS ECS;
extern engineScene Scene;

TTF_Font* font = NULL;

/* Parse a command-line flag that expects a string value after it.
 * Returns the pointer to the value or NULL if not found / out of range. */
static const char* getFlagValue(int argc, char *argv[], const char* flag){
    for(int i = 1; i < argc - 1; i++){
        if(strcmp(argv[i], flag) == 0) return argv[i+1];
    }
    return NULL;
}

static int hasFlag(int argc, char *argv[], const char* flag){
    for(int i = 1; i < argc; i++){
        if(strcmp(argv[i], flag) == 0) return 1;
    }
    return 0;
}

int main(int argc, char *argv[]){

    OpenLogFile("voxelforge.log");

    /* -----------------------------------------------------------------
     * Parse command-line arguments
     * ----------------------------------------------------------------- */
    int  isHeadless   = hasFlag(argc, argv, "--headless");
    const char *screenshotPath = getFlagValue(argc, argv, "--screenshot");
    const char *sceneArg       = getFlagValue(argc, argv, "--scene");
    const char *widthStr       = getFlagValue(argc, argv, "--width");
    const char *heightStr      = getFlagValue(argc, argv, "--height");
    const char *scaleStr       = getFlagValue(argc, argv, "--scale");
    const char *fpsStr         = getFlagValue(argc, argv, "--fps");

    int winW  = widthStr  ? atoi(widthStr)  : 1280;
    int winH  = heightStr ? atoi(heightStr) : 720;
    int scale = scaleStr  ? atoi(scaleStr)  : 1;
    int fps   = fpsStr    ? atoi(fpsStr)    : 60;

    /* Screenshot implies headless */
    if(screenshotPath) isHeadless = 1;

    /* -----------------------------------------------------------------
     * ECS setup
     * ----------------------------------------------------------------- */
    InitECS(110);

    ComponentID transformComponent  = RegisterNewComponent("Transform",  &TransformConstructor,  &TransformDestructor,  &TransformCopy,  &TransformEncode,  &TransformDecode);
    ComponentID voxelModelComponent = RegisterNewComponent("VoxelModel", &VoxelModelConstructor, &VoxelModelDestructor, &VoxelModelCopy, &VoxelModelEncode, &VoxelModelDecode);
    ComponentID rigidBodyComponent  = RegisterNewComponent("RigidBody",  &RigidBodyConstructor,  &RigidBodyDestructor,  &RigidBodyCopy,  &RigidBodyEncode,  &RigidBodyDecode);
    ComponentID pointLightComponent = RegisterNewComponent("PointLight", &PointLightConstructor, &PointLightDestructor, &PointLightCopy, &PointLightEncode, &PointLightDecode);
    ComponentID luaScriptComponent  = RegisterNewComponent("LuaScript",  &LuaScriptConstructor,  &LuaScriptDestructor,  &LuaScriptCopy,  &LuaScriptEncode,  &LuaScriptDecode);

    if(RegisterNewSystem("VoxelPhysics",  3, CreateComponentMaskByID(3, transformComponent, voxelModelComponent, rigidBodyComponent), (ComponentMask){0}, &VoxelPhysicsInit,    &VoxelPhysicsUpdate,    &VoxelPhysicsFree)    < 0) PrintLog(Error,"Main: Failed to register VoxelPhysics\n");
    if(RegisterNewSystem("PointLighting", 2, CreateComponentMaskByID(2, transformComponent, pointLightComponent),                     (ComponentMask){0}, &PointLightingInit,   &PointLightingUpdate,   &PointLightingFree)   < 0) PrintLog(Error,"Main: Failed to register PointLighting\n");
    if(RegisterNewSystem("Shadows",       2, CreateComponentMaskByID(2, transformComponent, voxelModelComponent),                     (ComponentMask){0}, &ShadowsInit,         &ShadowsUpdate,         &ShadowsFree)         < 0) PrintLog(Error,"Main: Failed to register Shadows\n");
    if(RegisterNewSystem("VoxelRenderer", 0, CreateComponentMaskByID(2, transformComponent, voxelModelComponent),                     (ComponentMask){0}, &VoxelRendererInit,   &VoxelRendererUpdate,   &VoxelRendererFree)   < 0) PrintLog(Error,"Main: Failed to register VoxelRenderer\n");
    if(RegisterNewSystem("VoxelModification",4,CreateComponentMaskByID(2, voxelModelComponent, transformComponent),                   (ComponentMask){0}, &VoxelModificationInit,&VoxelModificationUpdate,&VoxelModificationFree)< 0) PrintLog(Error,"Main: Failed to register VoxelModification\n");

    /* Skip Editor and UIRenderer in headless mode */
    if(!isHeadless){
        if(RegisterNewSystem("Editor",     -1, CreateComponentMaskByID(0), (ComponentMask){0}, &EditorInit,     &EditorUpdate,     &EditorFree)     < 0) PrintLog(Error,"Main: Failed to register Editor\n");
        if(RegisterNewSystem("UIRenderer", -2, CreateComponentMaskByID(0), (ComponentMask){0}, &UIRendererInit, &UIRendererUpdate, &UIRendererFree) < 0) PrintLog(Error,"Main: Failed to register UIRenderer\n");
    }

    if(RegisterNewSystem("LuaSystem", 1, CreateComponentMaskByID(1, luaScriptComponent), (ComponentMask){0}, &LuaSystemInit, &LuaSystemUpdate, &LuaSystemFree) < 0)
        PrintLog(Error,"Main: Failed to register LuaSystem\n");

    /* -----------------------------------------------------------------
     * Engine init
     * ----------------------------------------------------------------- */
    Core.isHeadless = isHeadless;

    /* InitScreen must be called before InitEngine so the window size is set */
    InitScreen(winW, winH, scale, fps);

    if(!InitEngine()) return 1;

    InitFPS();

    /* Font is only needed for debug overlay in windowed mode */
    if(!isHeadless){
        font = TTF_OpenFont("Assets/Interface/Fonts/Visitor.ttf", 18);
        if(!font) PrintLog(Error,"Main: Error loading font!\n");
    }

    /* -----------------------------------------------------------------
     * Scene loading
     * ----------------------------------------------------------------- */
    if(sceneArg){
        /* Allow full path or just name */
        LoadScene(".", sceneArg);
    } else {
        LoadScene("Assets", "default.scene");
    }

    PrintLog(Info,"GameLoop Initialized\n");

    /* -----------------------------------------------------------------
     * Game loop
     * ----------------------------------------------------------------- */
    while (!GameExited())
    {
        EngineUpdate();

        if(!isHeadless){
            /* Keyboard shortcuts (windowed mode only) */
            if(GetKey(SDL_SCANCODE_ESCAPE)) ExitGame();

            if(GetKeyDown(SDL_SCANCODE_R)){
                if(ReloadAllScripts())
                    PrintLog(Info,"Reloaded Lua scripts without errors!\n");
            }
            if(GetKeyDown(SDL_SCANCODE_T)) ReloadShaders();

            /* Debug shadow view toggle */
            if(!GetKey(SDL_SCANCODE_V)) RenderToScreen();

            static char fpsInfo[20], msInfo[20], dtInfo[20];
            sprintf(fpsInfo,"FPS: %4.2f", GetFPS());
            sprintf(msInfo, "MS : %3u",   Time.msTime);
            sprintf(dtInfo, "DT : %5.4lf",Time.deltaTime);
            SDL_Color fontColor = {255,255,255,255};
            if(font){
                RenderTextDebug(fpsInfo, fontColor, 110, TTF_FontHeight(font)*2+10, font);
                RenderTextDebug(msInfo,  fontColor, 110, TTF_FontHeight(font)  +10, font);
                RenderTextDebug(dtInfo,  fontColor, 110, 10, font);
            }
        } else {
            /* Headless mode: render scene to offscreen buffer */
            RenderToScreen();

            /* If screenshot was requested, export frame and exit */
            if(screenshotPath){
                ExportScreenshot(screenshotPath);
                ExitGame();
            } else {
                /* Headless steady-state: exit after one frame unless a Lua
                 * script calls ExitGame().  Change to a loop if you need
                 * multi-frame headless simulation. */
                ExitGame();
            }
        }

        EngineUpdateEnd();
        if(!isHeadless) ProcessFPS();
    }

    /* -----------------------------------------------------------------
     * Cleanup
     * ----------------------------------------------------------------- */
    if(font) TTF_CloseFont(font);

    EndEngine(0);
    CloseLogFile();
    return 0;
}
