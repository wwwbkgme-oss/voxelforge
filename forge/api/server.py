"""
forge.api.server
================
VoxelForge REST API server.

Exposes all asset generation, scene building, and world construction
operations over HTTP so any client (LLM agent, CI pipeline, game editor)
can call them without touching Python directly.

Start
-----
    uvicorn forge.api.server:app --host 0.0.0.0 --port 8080 --reload

Or via the CLI:
    voxelforge api --port 8080

Environment variables
---------------------
    VOXELFORGE_ASSETS_DIR  Root directory for generated assets
                           Default: ./generated_assets
"""

from __future__ import annotations

import glob
import os
import random
import traceback
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from ..voxel import Palette, VoxelModel
from ..scene import Scene
from ..generators import (
    BuildingGenerator,
    CharacterGenerator,
    PropGenerator,
    TerrainGenerator,
)
from .models import (
    AssetListResponse,
    AssetResponse,
    BuildingRequest,
    CharacterRequest,
    ErrorResponse,
    PropRequest,
    SceneBuildRequest,
    SceneResponse,
    TerrainRequest,
    WorldBuildRequest,
    WorldResponse,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

ASSETS_DIR = os.environ.get("VOXELFORGE_ASSETS_DIR", "generated_assets")

app = FastAPI(
    title="VoxelForge API",
    description=(
        "AI-driven voxel world builder REST API. "
        "Generate terrain, buildings, characters, props, and complete game worlds."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the web dashboard at /
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/ui", StaticFiles(directory=_static_dir, html=True), name="ui")


def _palette() -> Palette:
    return Palette.natural()


def _asset_path(subdir: str, name: str) -> str:
    """Build and ensure the output directory exists, return full file path."""
    d = os.path.join(ASSETS_DIR, subdir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{name}.vox")


def _scene_path(name: str) -> str:
    d = os.path.join(ASSETS_DIR, "scenes")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{name}.scene")


def _engine_rel(full_path: str) -> str:
    """Convert absolute path to an engine-relative path starting with Assets/…"""
    # Return the path as-is relative to cwd so the engine can find it
    try:
        return os.path.relpath(full_path)
    except ValueError:
        return full_path


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"], include_in_schema=False)
async def root():
    """Redirect browser requests to the web dashboard."""
    return RedirectResponse(url="/ui/index.html")


@app.get("/health", tags=["health"])
async def health() -> Dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Asset: Terrain
# ---------------------------------------------------------------------------

@app.post("/asset/terrain", response_model=AssetResponse, tags=["assets"])
async def generate_terrain(req: TerrainRequest) -> AssetResponse:
    """
    Generate procedural voxel terrain.

    Returns the path to the generated `.vox` file and metadata.
    """
    try:
        gen   = TerrainGenerator(_palette(), seed=req.seed)
        model = gen.generate(
            width    = req.width,
            height   = req.height,
            max_depth= req.max_depth,
            biome    = req.biome.value,
            scale    = req.scale,
            octaves  = req.octaves,
        )
        model.name = req.name
        path = _asset_path("terrain", req.name)
        model.save(path)
        return AssetResponse(
            status      = "ok",
            name        = req.name,
            path        = _engine_rel(path),
            voxel_count = model.voxel_count(),
            dimensions  = (model.width, model.height, model.depth),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Asset: Building
# ---------------------------------------------------------------------------

@app.post("/asset/building", response_model=AssetResponse, tags=["assets"])
async def generate_building(req: BuildingRequest) -> AssetResponse:
    """Generate a procedural voxel building."""
    try:
        gen   = BuildingGenerator(_palette(), seed=req.seed)
        model = gen.generate(
            width  = req.width,
            depth  = req.depth,
            floors = req.floors,
            style  = req.style.value,
            name   = req.name,
        )
        path = _asset_path("buildings", req.name)
        model.save(path)
        return AssetResponse(
            status      = "ok",
            name        = req.name,
            path        = _engine_rel(path),
            voxel_count = model.voxel_count(),
            dimensions  = (model.width, model.height, model.depth),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Asset: Character
# ---------------------------------------------------------------------------

@app.post("/asset/character", response_model=AssetResponse, tags=["assets"])
async def generate_character(req: CharacterRequest) -> AssetResponse:
    """Generate a procedural voxel humanoid character."""
    try:
        gen   = CharacterGenerator(_palette(), seed=req.seed)
        model = gen.generate(
            class_type = req.class_type.value,
            skin_tone  = req.skin_tone,
            hair_color = req.hair_color,
            armour     = req.armour,
            weapon     = req.weapon,
            name       = req.name,
        )
        path = _asset_path("characters", req.name)
        model.save(path)
        return AssetResponse(
            status      = "ok",
            name        = req.name,
            path        = _engine_rel(path),
            voxel_count = model.voxel_count(),
            dimensions  = (model.width, model.height, model.depth),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Asset: Prop
# ---------------------------------------------------------------------------

@app.post("/asset/prop", response_model=AssetResponse, tags=["assets"])
async def generate_prop(req: PropRequest) -> AssetResponse:
    """Generate a procedural voxel prop (tree, crate, barrel, etc.)."""
    try:
        gen  = PropGenerator(_palette(), seed=req.seed)
        name = req.name or req.prop_type.value
        kw: Dict[str, Any] = {}
        if req.size:
            kw["size"] = req.size
        model = gen.generate(req.prop_type.value, variant=req.variant, name=name, **kw)
        path  = _asset_path("props", name)
        model.save(path)
        return AssetResponse(
            status      = "ok",
            name        = name,
            path        = _engine_rel(path),
            voxel_count = model.voxel_count(),
            dimensions  = (model.width, model.height, model.depth),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Asset: list existing
# ---------------------------------------------------------------------------

@app.get("/assets", response_model=AssetListResponse, tags=["assets"])
async def list_assets(subdir: str = "") -> AssetListResponse:
    """
    List all generated .vox assets.

    Optionally filter by sub-directory (terrain | buildings | characters | props).
    """
    pattern = os.path.join(ASSETS_DIR, subdir or "**", "*.vox")
    files   = glob.glob(pattern, recursive=True)
    assets  = []
    for fp in sorted(files):
        assets.append({
            "path":    _engine_rel(fp),
            "name":    os.path.splitext(os.path.basename(fp))[0],
            "subdir":  os.path.basename(os.path.dirname(fp)),
            "size_kb": round(os.path.getsize(fp) / 1024, 1),
        })
    return AssetListResponse(assets=assets)


# ---------------------------------------------------------------------------
# Scene builder
# ---------------------------------------------------------------------------

@app.post("/scene/build", response_model=SceneResponse, tags=["scene"])
async def build_scene(req: SceneBuildRequest) -> SceneResponse:
    """
    Construct a VoxelForge scene from a list of entity placements and lights.

    The output JSON is directly loadable by the C engine.
    """
    try:
        scene = Scene(background_color=req.background_color)

        for ent in req.entities:
            scene.add_voxel_model(
                name     = ent.name,
                vox_path = ent.asset,
                position = ent.position,
                rotation = ent.rotation,
            )

        for light in req.lights:
            scene.add_point_light(
                name      = light.name,
                position  = light.position,
                color     = light.color,
                intensity = light.intensity,
                range_    = light.range_,
                hue_shift = light.hue_shift,
            )

        path = _scene_path(req.scene_name)
        scene.save(path)
        return SceneResponse(
            status       = "ok",
            scene_name   = req.scene_name,
            path         = _engine_rel(path),
            entity_count = scene.entity_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/scenes", tags=["scene"])
async def list_scenes() -> Dict[str, Any]:
    """List all generated scene files."""
    pattern = os.path.join(ASSETS_DIR, "scenes", "*.scene")
    files   = glob.glob(pattern)
    return {
        "scenes": [
            {
                "name": os.path.splitext(os.path.basename(f))[0],
                "path": _engine_rel(f),
            }
            for f in sorted(files)
        ]
    }


# ---------------------------------------------------------------------------
# World builder — one-call complete world generation
# ---------------------------------------------------------------------------

@app.post("/world/build", response_model=WorldResponse, tags=["world"])
async def build_world(req: WorldBuildRequest) -> WorldResponse:
    """
    Build a complete game world in one API call.

    This endpoint:
    1. Generates terrain for the given biome/size
    2. Generates the requested number of buildings, characters, and props
    3. Places them on the terrain at random positions
    4. Writes a scene file referencing all generated assets

    Returns paths to the scene and all individual assets.
    """
    try:
        rng         = random.Random(req.seed)
        pal         = _palette()
        asset_paths: List[str] = []
        scene       = Scene(
            background_color = _biome_sky(req.biome.value),
        )

        # --- Terrain ---
        tgen    = TerrainGenerator(pal, seed=req.seed)
        terrain = tgen.generate(
            width    = req.width,
            height   = req.height,
            max_depth= 14,
            biome    = req.biome.value,
        )
        terrain.name = f"{req.name}_terrain"
        t_path = _asset_path("terrain", terrain.name)
        terrain.save(t_path)
        asset_paths.append(_engine_rel(t_path))
        scene.add_voxel_model("terrain", _engine_rel(t_path), position=(0, 0, 0))

        surface_z = 14  # approx top of terrain

        # --- Buildings ---
        bgen = BuildingGenerator(pal, seed=req.seed + 1)
        for i in range(req.buildings):
            b_name  = f"{req.name}_building_{i}"
            bfloors = rng.randint(2, 6)
            bw      = rng.randint(6, 14)
            bd      = rng.randint(6, 14)
            model   = bgen.generate(
                width=bw, depth=bd, floors=bfloors,
                style=req.building_style.value, name=b_name,
            )
            b_path = _asset_path("buildings", b_name)
            model.save(b_path)
            asset_paths.append(_engine_rel(b_path))
            pos_x = rng.randint(0, max(1, req.width  - bw - 2))
            pos_y = rng.randint(0, max(1, req.height - bd - 2))
            scene.add_voxel_model(
                b_name, _engine_rel(b_path),
                position=(float(pos_x), float(pos_y), float(surface_z)),
            )

        # --- Characters ---
        cgen = CharacterGenerator(pal, seed=req.seed + 2)
        classes     = ["warrior", "mage", "archer", "rogue"]
        skin_tones  = ["light", "tan", "dark"]
        hair_colors = ["blonde", "brown", "black", "red"]
        armours     = ["leather", "chainmail", "plate", "mage"]
        weapons     = ["sword", "staff", "bow", "axe"]
        for i in range(req.characters):
            c_name = f"{req.name}_char_{i}"
            model  = cgen.generate(
                class_type = rng.choice(classes),
                skin_tone  = rng.choice(skin_tones),
                hair_color = rng.choice(hair_colors),
                armour     = rng.choice(armours),
                weapon     = rng.choice(weapons),
                name       = c_name,
            )
            c_path = _asset_path("characters", c_name)
            model.save(c_path)
            asset_paths.append(_engine_rel(c_path))
            pos_x = rng.randint(0, max(1, req.width  - 4))
            pos_y = rng.randint(0, max(1, req.height - 4))
            scene.add_voxel_model(
                c_name, _engine_rel(c_path),
                position=(float(pos_x), float(pos_y), float(surface_z)),
            )

        # --- Props ---
        pgen      = PropGenerator(pal, seed=req.seed + 3)
        prop_types = ["tree", "crate", "barrel", "rock", "mushroom", "lamp_post", "chest"]
        for i in range(req.props):
            p_type = rng.choice(prop_types)
            p_name = f"{req.name}_prop_{p_type}_{i}"
            model  = pgen.generate(p_type, name=p_name)
            p_path = _asset_path("props", p_name)
            model.save(p_path)
            asset_paths.append(_engine_rel(p_path))
            pos_x = rng.randint(0, max(1, req.width  - 8))
            pos_y = rng.randint(0, max(1, req.height - 8))
            scene.add_voxel_model(
                p_name, _engine_rel(p_path),
                position=(float(pos_x), float(pos_y), float(surface_z)),
            )

        # --- Ambient light ---
        scene.add_point_light(
            "sun",
            position  = (float(req.width // 2), float(req.height // 2), 40.0),
            color     = (1.0, 0.95, 0.85),
            intensity = 2.0,
            range_    = float(max(req.width, req.height) * 2),
        )

        s_path = _scene_path(req.name)
        scene.save(s_path)

        return WorldResponse(
            status       = "ok",
            world_name   = req.name,
            scene_path   = _engine_rel(s_path),
            asset_paths  = asset_paths,
            entity_count = scene.entity_count,
            seed         = req.seed,
        )
    except Exception as exc:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"{exc}\n{tb}") from exc


# ---------------------------------------------------------------------------
# Download a generated asset
# ---------------------------------------------------------------------------

@app.get("/asset/download", tags=["assets"])
async def download_asset(path: str) -> FileResponse:
    """Download a generated asset file by its relative path."""
    full = os.path.abspath(path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return FileResponse(full, media_type="application/octet-stream",
                        filename=os.path.basename(full))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _biome_sky(biome: str) -> tuple:
    return {
        "grassland": (0.05, 0.15, 0.30),
        "desert":    (0.60, 0.45, 0.20),
        "snow":      (0.75, 0.85, 0.95),
        "ocean":     (0.02, 0.08, 0.25),
        "forest":    (0.03, 0.12, 0.08),
    }.get(biome, (0.0, 0.149, 0.294))
