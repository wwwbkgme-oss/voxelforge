"""
forge.api.models
================
Pydantic request / response models for the VoxelForge REST API.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

Vec3 = Tuple[float, float, float]


class BiomeEnum(str, Enum):
    grassland = "grassland"
    desert    = "desert"
    snow      = "snow"
    ocean     = "ocean"
    forest    = "forest"


class BuildingStyleEnum(str, Enum):
    modern   = "modern"
    medieval = "medieval"
    sci_fi   = "sci-fi"
    rustic   = "rustic"
    fantasy  = "fantasy"


class CharacterClassEnum(str, Enum):
    warrior = "warrior"
    mage    = "mage"
    archer  = "archer"
    rogue   = "rogue"


class PropTypeEnum(str, Enum):
    tree      = "tree"
    crate     = "crate"
    barrel    = "barrel"
    lamp_post = "lamp_post"
    rock      = "rock"
    chest     = "chest"
    mushroom  = "mushroom"


class DungeonStyleEnum(str, Enum):
    stone   = "stone"
    dungeon = "dungeon"
    cave    = "cave"
    ice     = "ice"


# ---------------------------------------------------------------------------
# Asset generation requests
# ---------------------------------------------------------------------------

class DungeonRequest(BaseModel):
    width:       int   = Field(48, ge=16, le=128)
    height:      int   = Field(48, ge=16, le=128)
    wall_height: int   = Field(3,  ge=1,  le=8)
    style:       DungeonStyleEnum = DungeonStyleEnum.stone
    seed:        int   = Field(0)
    name:        str   = Field("dungeon")

class TerrainRequest(BaseModel):
    width:    int   = Field(32, ge=4, le=128, description="Terrain X footprint in voxels")
    height:   int   = Field(32, ge=4, le=128, description="Terrain Y footprint in voxels")
    max_depth: int  = Field(12, ge=2, le=64,  description="Maximum terrain height in voxels")
    biome:    BiomeEnum = BiomeEnum.grassland
    scale:    float = Field(0.08, gt=0.0, le=1.0, description="Noise frequency")
    octaves:  int   = Field(5, ge=1, le=8, description="FBM octave count")
    seed:     int   = Field(0, description="RNG seed for deterministic output")
    name:     str   = Field("terrain", description="Asset name (used in filename)")


class BuildingRequest(BaseModel):
    width:  int = Field(8,  ge=4,  le=32, description="Building X footprint")
    depth:  int = Field(8,  ge=4,  le=32, description="Building Y footprint")
    floors: int = Field(3,  ge=1,  le=20, description="Number of floors")
    style:  BuildingStyleEnum = BuildingStyleEnum.modern
    seed:   int = Field(0,  description="RNG seed")
    name:   str = Field("building", description="Asset name")


class CharacterRequest(BaseModel):
    class_type:  CharacterClassEnum = CharacterClassEnum.warrior
    skin_tone:   str = Field("tan", description="light | tan | dark | fantasy")
    hair_color:  str = Field("brown", description="blonde | brown | black | red | white | blue")
    armour:      str = Field("chainmail", description="none | leather | chainmail | plate | mage")
    weapon:      str = Field("sword", description="none | sword | staff | bow | axe")
    seed:        int = Field(0)
    name:        str = Field("character", description="Asset name")


class PropRequest(BaseModel):
    prop_type: PropTypeEnum = PropTypeEnum.tree
    variant:   str = Field("", description="Sub-variant (e.g. 'oak' for tree)")
    seed:      int = Field(0)
    name:      str = Field("", description="Asset name (defaults to prop_type)")
    size:      int = Field(4, ge=2, le=16, description="Size hint for scalable props")


# ---------------------------------------------------------------------------
# Scene building
# ---------------------------------------------------------------------------

class EntityPlacement(BaseModel):
    name:     str
    asset:    str    = Field(..., description="Path to the .vox file (relative to engine/)")
    position: Vec3   = (0.0, 0.0, 0.0)
    rotation: Vec3   = (0.0, 0.0, 0.0)
    scale:    Vec3   = (1.0, 1.0, 1.0)


class PointLightPlacement(BaseModel):
    name:      str
    position:  Vec3  = (0.0, 10.0, 0.0)
    color:     Vec3  = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    range_:    float = Field(100.0, alias="range", description="Light range in world units")
    hue_shift: float = 0.0

    model_config = {"populate_by_name": True}


class SceneBuildRequest(BaseModel):
    scene_name:         str = Field(..., description="Output scene name (no extension)")
    background_color:   Vec3 = (0.0, 0.149, 0.294)
    ambient_intensity:  float = 0.3
    entities:           List[EntityPlacement] = Field(default_factory=list)
    lights:             List[PointLightPlacement] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# World build — high-level request to generate full world in one call
# ---------------------------------------------------------------------------

class WorldBuildRequest(BaseModel):
    name:         str   = Field("world", description="World / scene name")
    width:        int   = Field(64, ge=16, le=256, description="World X size in voxels")
    height:       int   = Field(64, ge=16, le=256, description="World Y size in voxels")
    biome:        BiomeEnum = BiomeEnum.grassland
    buildings:    int   = Field(3,  ge=0,  le=20,  description="Number of buildings to place")
    building_style: BuildingStyleEnum = BuildingStyleEnum.medieval
    characters:   int   = Field(2,  ge=0,  le=20,  description="Number of characters to place")
    props:        int   = Field(5,  ge=0,  le=50,  description="Number of random props")
    seed:         int   = Field(0)


# ---------------------------------------------------------------------------
# Image generation requests (from acatovic/ai-game-studio pattern)
# ---------------------------------------------------------------------------

class SpriteGenerateRequest(BaseModel):
    prompt:    str   = Field(..., description="Text description of the sprite")
    name:      str   = Field("sprite", description="Output filename stem")
    size:      int   = Field(512, ge=64, le=1024, description="Image size in pixels")
    remove_bg: bool  = Field(True, description="Apply chroma-key background removal")
    style:     str   = Field("pixel art isometric game sprite", description="Style hint")
    animated:  bool  = Field(False, description="Generate animated spritesheet")
    frames:    int   = Field(8, ge=2, le=32, description="Animation frame count (animated only)")


class SpriteGenerateResponse(BaseModel):
    status:       str
    name:         str
    image_path:   str
    image_b64:    str = Field("", description="Base64 PNG (omitted if animated)")
    model_used:   str
    width:        int
    height:       int
    has_alpha:    bool
    source:       str
    spritesheet:  Optional[str] = None
    gif_path:     Optional[str] = None
    frame_count:  int = 1


class BatchSpriteRequest(BaseModel):
    prompts:    List[str] = Field(..., description="List of sprite prompts")
    names:      Optional[List[str]] = Field(None)
    remove_bg:  bool = Field(True)


# ---------------------------------------------------------------------------
# Narrative engine requests
# ---------------------------------------------------------------------------

class NarrativeSessionRequest(BaseModel):
    player_name: str  = Field(..., description="Player character name")
    genre:       str  = Field("dungeon", description="Game genre")
    world_text:  str  = Field("", description="World lore / setting description")
    model:       str  = Field("", description="LLM model override")
    api_key:     str  = Field("", description="LLM API key override")


class NarrativeSessionResponse(BaseModel):
    status:     str
    session_id: str
    genre:      str
    player:     str


class NarrativeMessageRequest(BaseModel):
    session_id: str   = Field(..., description="Session ID from start_session")
    message:    str   = Field(..., description="Player input/action")


class NarrativeMessageResponse(BaseModel):
    status:     str
    session_id: str
    turn_id:    str
    blocks:     List[Dict[str, Any]]
    text:       str
    choices:    List[str]
    hp:         int = 100
    score:      int = 0


# ---------------------------------------------------------------------------
# Pipeline requests
# ---------------------------------------------------------------------------

class PipelineRequest(BaseModel):
    concept:      str   = Field(..., description="One-sentence game concept")
    genre:        str   = Field("dungeon")
    platform:     str   = Field("PC")
    audience:     str   = Field("core")
    mode:         str   = Field("design", description="design | prototype | development")
    timeline:     str   = Field("Short", description="Rapid | Short | Medium | Long")
    competitors:  List[str] = Field(default_factory=list)
    usp:          str   = Field("", description="Unique selling proposition")
    build_game:   bool  = Field(False, description="Run Build phase (generates VoxelForge game)")
    seed:         int   = Field(42)


class PipelineResponse(BaseModel):
    status:      str
    concept:     str
    mode:        str
    agents_used: int
    market_recommendation: Optional[str] = None
    market_score:          Optional[int] = None
    gdd_path:    Optional[str] = None
    build_path:  Optional[str] = None
    run_command: Optional[str] = None
    qa_passed:   Optional[bool] = None
    elapsed_s:   float = 0.0
    project_dir: str = ""


# ---------------------------------------------------------------------------
# Project lifecycle requests
# ---------------------------------------------------------------------------

class ProjectInitRequest(BaseModel):
    name:               str   = Field(..., description="Project name")
    concept:            str   = Field(..., description="One-sentence game concept")
    genre:              str   = Field("dungeon")
    platform:           str   = Field("PC")
    audience:           str   = Field("core")
    engine:             str   = Field("voxelforge", description="voxelforge | godot | unity | unreal")
    mode:               str   = Field("development")
    timeline:           str   = Field("Short")
    usp:                str   = Field("")
    competitors:        List[str] = Field(default_factory=list)
    development_rules:  List[str] = Field(default_factory=list)


class ProjectStatusResponse(BaseModel):
    status:   str
    project:  Dict[str, Any]


# ---------------------------------------------------------------------------
# HTML5 game + sprite sheet + asset pipeline requests
# ---------------------------------------------------------------------------

class HTML5GameRequest(BaseModel):
    prompt:     str   = Field(..., description="Game description in plain English")
    genre:      str   = Field("auto", description="auto|platformer|puzzle|rpg|shooter|arcade|dungeon|educational")
    title:      str   = Field("", description="Game title (auto-generated if empty)")
    name:       str   = Field("game", description="Output filename stem")
    max_tokens: int   = Field(8192, ge=1024, le=16384)


class HTML5GameResponse(BaseModel):
    status:     str
    title:      str
    genre:      str
    html_path:  str
    open_url:   str
    valid:      bool
    provider:   str
    model:      str
    issues:     List[str]


class SpriteSheetRequest(BaseModel):
    description: str   = Field(..., description="Character or asset description")
    style:       str   = Field("pixel_art_rpg",
                                description="stardew_valley|hollow_knight|genshin_impact|fall_guys|pixel_art_rpg|breath_of_wild|retro_8bit|anime_cartoon|realistic_game|vector_art|isometric_voxel")
    actions:     List[str] = Field(["idle","walk","attack"],
                                   description="Animation actions to generate")
    name:        str   = Field("character")


class SpriteSheetResponse(BaseModel):
    status:          str
    spritesheet_path: str
    frame_count:     int
    gif_path:        Optional[str]
    has_alpha:       bool
    source:          str
    style:           str


class BatchSpriteSheetRequest(BaseModel):
    prompts:   List[str] = Field(..., description="List of prop/item descriptions")
    style:     str       = Field("pixel_art_rpg")
    grid_size: int       = Field(5, ge=2, le=8, description="Grid dimension (5 = 25 items/call)")
    name:      str       = Field("batch")


class AssetPipelineRequest(BaseModel):
    theme:   str  = Field(..., description="Game world theme (e.g. 'dark ice dungeon')")
    details: str  = Field("", description="Additional world details")
    genre:   str  = Field("dungeon")
    seed:    int  = Field(0)


class AssetPipelineResponse(BaseModel):
    status:       str
    output_dir:   str
    files_saved:  int
    characters:   int
    quests:       int
    items:        int
    lua_scripts:  List[str]
    model:        str
    provider:     str


class LLMChatRequest(BaseModel):
    prompt:      str   = Field(..., description="User prompt")
    system:      str   = Field("", description="System prompt (optional)")
    task:        str   = Field("default", description="default|fast|code|creative|small")
    provider:    str   = Field("", description="Force a specific provider (optional)")
    max_tokens:  int   = Field(2048, ge=64, le=8192)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class LLMChatResponse(BaseModel):
    status:     str
    text:       str
    provider:   str
    model:      str
    latency_ms: int
    ok:         bool


class LLMProvidersResponse(BaseModel):
    available:      List[Dict[str, Any]]
    all_providers:  List[Dict[str, Any]]
    count:          int


# ---------------------------------------------------------------------------
# Local inference / model management requests
# ---------------------------------------------------------------------------

class ModelDownloadRequest(BaseModel):
    model_id:   str  = Field(..., description="Model catalog ID, e.g. 'llama3.2-3b'")
    force:      bool = Field(False, description="Re-download even if already present")
    custom_url: str  = Field("", description="Override HuggingFace URL")


class ModelDownloadResponse(BaseModel):
    status:     str
    model_id:   str
    local_path: str
    size_gb:    float


class InferenceStartRequest(BaseModel):
    model_id:     str   = Field(..., description="Model catalog ID to serve")
    n_gpu_layers: int   = Field(0, description="-1 = all GPU, 0 = CPU only, N = partial")
    context_size: int   = Field(4096)
    threads:      int   = Field(0, description="0 = auto-detect")


class InferenceStartResponse(BaseModel):
    status:   str
    model_id: str
    base_url: str
    port:     int


class InferenceStatusResponse(BaseModel):
    running:  bool
    model_id: str
    base_url: str
    port:     int


class InferenceChatRequest(BaseModel):
    prompt:      str   = Field(...)
    system:      str   = Field("")
    max_tokens:  int   = Field(2048)
    temperature: float = Field(0.7)


class InferenceChatResponse(BaseModel):
    status:    str
    text:      str
    model_id:  str
    provider:  str


# ---------------------------------------------------------------------------
# Game generation request
# ---------------------------------------------------------------------------

class GameGenreEnum(str, Enum):
    village = "village"
    dungeon = "dungeon"
    space   = "space"
    fantasy = "fantasy"
    horror  = "horror"
    arctic  = "arctic"


class GameGenerateRequest(BaseModel):
    title:        str  = Field("VoxelForge Game", description="Game title")
    genre:        GameGenreEnum = GameGenreEnum.village
    theme:        str  = Field("", description="Optional sub-theme override")
    player_class: str  = Field("warrior", description="warrior | mage | archer | rogue")
    enemies:      int  = Field(3,  ge=0, le=10)
    props:        int  = Field(6,  ge=0, le=20)
    level_size:   int  = Field(48, ge=16, le=96)
    seed:         int  = Field(0)


class GameGenerateResponse(BaseModel):
    status:        str
    title:         str
    genre:         str
    scene_path:    str
    manifest_path: str
    run_command:   str
    entity_count:  int
    asset_count:   int
    script_count:  int


# ---------------------------------------------------------------------------
# Agent request
# ---------------------------------------------------------------------------

class AgentRunRequest(BaseModel):
    prompt:      str  = Field(..., description="Natural language world description")
    direct_mode: bool = Field(True, description="Use keyword parser (no LLM). Set False to use OPENAI_API_KEY.")
    model:       str  = Field("gpt-4o", description="LLM model (only used when direct_mode=False)")


class AgentRunResponse(BaseModel):
    status:        str
    scene_path:    str
    asset_paths:   List[str]
    entity_count:  int
    elapsed_seconds: float
    mode:          str


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class AssetResponse(BaseModel):
    status:      str
    name:        str
    path:        str              = Field(..., description="Engine-relative path to the .vox file")
    voxel_count: int
    dimensions:  Tuple[int, int, int]


class SceneResponse(BaseModel):
    status:     str
    scene_name: str
    path:       str
    entity_count: int


class WorldResponse(BaseModel):
    status:        str
    world_name:    str
    scene_path:    str
    asset_paths:   List[str]
    entity_count:  int
    seed:          int


class AssetListResponse(BaseModel):
    assets: List[Dict[str, Any]]


class ErrorResponse(BaseModel):
    status:  str = "error"
    message: str
