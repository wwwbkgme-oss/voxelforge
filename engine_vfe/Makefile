# VoxelForge Engine (VFE) — Makefile (Linux / macOS fallback for non-CMake builds)
CC      = gcc
CFLAGS  = -std=c99 -O2 -ffast-math -Wall -Wno-unused-result \
          $(shell pkg-config --cflags sdl2 glew lua5.4 2>/dev/null)
LDFLAGS = $(shell pkg-config --libs   sdl2 glew lua5.4 2>/dev/null) \
          -lSDL2_image -lSDL2_mixer -lGL -lm

SRC     = $(shell find src -name '*.c')
OBJ     = $(SRC:src/%.c=build/%.o)
BIN     = voxelforge

# cJSON — fetched automatically on first build
CJSON_URL = https://raw.githubusercontent.com/DaveGamble/cJSON/v1.7.18
CJSON_H   = src/libs/cjson.h
CJSON_C   = src/libs/cjson.c

.PHONY: all clean fetch_cjson

all: fetch_cjson $(BIN)
	@echo "Build complete: ./$(BIN)"

$(BIN): $(OBJ)
	$(CC) $(OBJ) $(LDFLAGS) -o $@

build/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -Isrc -Isrc/libs -c $< -o $@

fetch_cjson:
	@if [ ! -f $(CJSON_C) ]; then \
	  echo "Fetching cJSON (MIT license)..."; \
	  curl -sSL $(CJSON_URL)/cJSON.h -o $(CJSON_H); \
	  curl -sSL $(CJSON_URL)/cJSON.c -o $(CJSON_C); \
	fi

clean:
	rm -rf build $(BIN)

# Docker build (inference + engine)
docker-build:
	docker compose -f ../docker/docker-compose.full.yml build

docker-up:
	docker compose -f ../docker/docker-compose.full.yml up -d
