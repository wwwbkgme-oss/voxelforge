PD = C:
#CC specifies which compiler we're using
CC = gcc

#SRC specifies which files to compile as part of the project
SRC = $(wildcard *.c) $(wildcard Engine/*.c) $(wildcard Components/*.c) $(wildcard Systems/*.c) $(wildcard Systems/Editor/*.c) $(wildcard Libs/*.c)
OBJS = $(SRC:%.c=Build/%.o)

#FOLDERS specifies the folders structure needed to put the .o files
ifeq ($(OS),Windows_NT)
FOLDERS = Build Build\Engine Build\Components Build\Systems Build\Systems\Editor Build\Libs
else
FOLDERS = Build Build/Engine Build/Components Build/Systems Build/Systems/Editor Build/Libs
endif

#COMPILER_FLAGS specifies the additional compilation options we're using
COMPILER_FLAGS += -Wall -Wno-unused-result -Wno-missing-braces -ffast-math -O3 -g

#LINKER_FLAGS specifies the libraries we're linking against
ifeq ($(OS),Windows_NT)
INCLUDE_PATHS = -I $(PD) -I $(PD)\SDL2\include -I $(PD)\glew\include -I $(PD)\lua5.3\include
LIBRARY_PATHS = -L $(PD)\SDL2\lib -L $(PD)\glew\lib -L $(PD)\lua5.3\lib
LINKER_FLAGS = -lmingw32 -lSDL2main -lSDL2 -lSDL2_image -lSDL2_ttf -lglew32.dll -llua53 -lopengl32 resource.res

FixPath = $(subst /,\,$1)
MakeDir = if not exist "$(call FixPath,$1)" mkdir $(call FixPath,$1)
RemoveDir = rd /s /q $(call FixPath,$1)
RemoveFile = del /q $(call FixPath,$1)
EchoNewline = @echo. && echo.$1

else
LINKER_FLAGS = -lSDL2 -lSDL2_image -lSDL2_ttf -lGLEW -lGL -llua5.3 -lm

FixPath = $1
MakeDir = mkdir -p $1
RemoveDir = rm -f -r $1
RemoveFile = rm -f $1
EchoNewline = @echo ""; echo "$1"

endif

# Name of the binary — VoxelForge engine executable
OBJ_NAME = voxelforge

#Compilation Targets
all : $(OBJ_NAME)
	@echo VoxelForge Engine build finished!

$(OBJ_NAME): $(FOLDERS)/ $(OBJS)
	$(call EchoNewline,+ Linking "$(OBJ_NAME)")
ifeq ($(OS),Windows_NT)
	@$(CC) $(OBJS) $(INCLUDE_PATHS) $(LIBRARY_PATHS) $(COMPILER_FLAGS) $(LINKER_FLAGS) -o $(OBJ_NAME)
else
	@$(CC) $(OBJS) $(COMPILER_FLAGS) $(LINKER_FLAGS) -o $(OBJ_NAME)
endif

Build/%.o: %.c %.h
	$(call EchoNewline,- Compiling "$@")
ifeq ($(OS),Windows_NT)
	@$(CC) -c $(INCLUDE_PATHS) $(COMPILER_FLAGS) $< -o $@
else
	@$(CC) -c $(COMPILER_FLAGS) $< -o $@
endif

Build/%.o: %.c
	$(call EchoNewline,- Compiling "$@")
ifeq ($(OS),Windows_NT)
	@$(CC) -c $(INCLUDE_PATHS) $(COMPILER_FLAGS) $< -o $@
else
	@$(CC) -c $(COMPILER_FLAGS) $< -o $@
endif

$(FOLDERS)/:
	$(call EchoNewline,+ Creating build folders "$@")
	$(call MakeDir,$@)

clean:
	-$(call RemoveDir,Build)
	-$(call RemoveFile,$(OBJ_NAME))
