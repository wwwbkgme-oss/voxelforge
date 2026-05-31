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


# ---------------------------------------------------------------------------
# Asset generation requests
# ---------------------------------------------------------------------------

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
