cmake_minimum_required(VERSION 3.18)
project(VoxelForgeEngine VERSION 1.0.0 LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# ── Build options ──────────────────────────────────────────────────────
option(VFE_HEADLESS_ONLY "Build without SDL window (EGL offscreen only)" OFF)
option(VFE_NO_AUDIO      "Disable SDL_mixer audio"                       OFF)
option(VFE_ENABLE_ASAN   "Enable AddressSanitizer (debug)"               OFF)

# ── Fetch cJSON (MIT) ─────────────────────────────────────────────────
include(FetchContent)
FetchContent_Declare(cjson
    GIT_REPOSITORY https://github.com/DaveGamble/cJSON.git
    GIT_TAG        v1.7.18
)
set(ENABLE_CJSON_TEST OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(cjson)

# ── Find system dependencies ──────────────────────────────────────────
find_package(SDL2   REQUIRED)
find_package(OpenGL REQUIRED)
find_package(GLEW   REQUIRED)

# Lua 5.4
find_package(PkgConfig QUIET)
if(PKG_CONFIG_FOUND)
    pkg_check_modules(LUA54 lua5.4)
endif()
if(NOT LUA54_FOUND)
    find_library(LUA54_LIBRARIES NAMES lua5.4 lua54 lua)
    find_path   (LUA54_INCLUDE_DIRS lua.h PATH_SUFFIXES lua5.4 lua54 lua)
endif()

# SDL_mixer (optional)
if(NOT VFE_NO_AUDIO)
    find_library(SDL2_MIXER_LIB SDL2_mixer)
    find_path   (SDL2_MIXER_INC SDL_mixer.h PATH_SUFFIXES SDL2)
endif()

# SDL2_image
find_library(SDL2_IMAGE_LIB SDL2_image)
find_path   (SDL2_IMAGE_INC SDL_image.h PATH_SUFFIXES SDL2)

# ── Sources ───────────────────────────────────────────────────────────
file(GLOB_RECURSE VFE_SOURCES
    src/core/*.c
    src/renderer/*.c
    src/voxel/*.c
    src/physics/*.c
    src/scripting/*.c
    src/scene/*.c
    src/audio/*.c
    src/ipc/*.c
    src/main.c
)

add_executable(voxelforge ${VFE_SOURCES})

# ── Include paths ─────────────────────────────────────────────────────
target_include_directories(voxelforge PRIVATE
    src
    ${SDL2_INCLUDE_DIRS}
    ${OPENGL_INCLUDE_DIRS}
    ${GLEW_INCLUDE_DIRS}
    ${LUA54_INCLUDE_DIRS}
    ${SDL2_IMAGE_INC}
    ${cjson_SOURCE_DIR}
)
if(NOT VFE_NO_AUDIO AND SDL2_MIXER_INC)
    target_include_directories(voxelforge PRIVATE ${SDL2_MIXER_INC})
endif()

# ── Link ──────────────────────────────────────────────────────────────
target_link_libraries(voxelforge PRIVATE
    ${SDL2_LIBRARIES}
    ${OPENGL_LIBRARIES}
    GLEW::GLEW
    ${LUA54_LIBRARIES}
    ${SDL2_IMAGE_LIB}
    cjson
    m
)
if(NOT VFE_NO_AUDIO AND SDL2_MIXER_LIB)
    target_link_libraries(voxelforge PRIVATE ${SDL2_MIXER_LIB})
else()
    target_compile_definitions(voxelforge PRIVATE VFE_NO_AUDIO)
endif()

# ── Compile definitions ───────────────────────────────────────────────
if(VFE_HEADLESS_ONLY)
    target_compile_definitions(voxelforge PRIVATE VFE_HEADLESS_ONLY)
endif()

# ── Compiler flags ────────────────────────────────────────────────────
if(MSVC)
    target_compile_options(voxelforge PRIVATE /W3 /O2)
else()
    target_compile_options(voxelforge PRIVATE
        -Wall -Wextra -Wno-unused-result
        -O2 -ffast-math
        $<$<BOOL:${VFE_ENABLE_ASAN}>:-fsanitize=address>
    )
    if(VFE_ENABLE_ASAN)
        target_link_options(voxelforge PRIVATE -fsanitize=address)
    endif()
endif()

# ── Install ───────────────────────────────────────────────────────────
install(TARGETS voxelforge RUNTIME DESTINATION bin)
install(DIRECTORY assets/ DESTINATION share/voxelforge)
