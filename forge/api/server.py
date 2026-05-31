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
    DungeonGenerator,
    PropGenerator,
    TerrainGenerator,
)
from .models import (
    AgentRunRequest,
    AgentRunResponse,
    AssetListResponse,
    AssetPipelineRequest,
    AssetPipelineResponse,
    AssetResponse,
    BatchSpriteRequest,
    BatchSpriteSheetRequest,
    BuildingRequest,
    CharacterRequest,
    DungeonRequest,
    ErrorResponse,
    GameGenerateRequest,
    GameGenerateResponse,
    HTML5GameRequest,
    HTML5GameResponse,
    LLMChatRequest,
    LLMChatResponse,
    LLMProvidersResponse,
    NarrativeMessageRequest,
    NarrativeMessageResponse,
    NarrativeSessionRequest,
    NarrativeSessionResponse,
    PipelineRequest,
    PipelineResponse,
    ProjectInitRequest,
    ProjectStatusResponse,
    PropRequest,
    SceneBuildRequest,
    SceneResponse,
    SpriteGenerateRequest,
    SpriteGenerateResponse,
    SpriteSheetRequest,
    SpriteSheetResponse,
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

# Serve the web dashboard at /ui
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/ui", StaticFiles(directory=_static_dir, html=True), name="ui")

# Serve demo sprites at /demo (repo docs/demo/)
_demo_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "demo")
_demo_dir = os.path.normpath(_demo_dir)
if os.path.isdir(_demo_dir):
    app.mount("/demo", StaticFiles(directory=_demo_dir), name="demo")


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
# Asset: Dungeon
# ---------------------------------------------------------------------------

@app.post("/asset/dungeon", response_model=AssetResponse, tags=["assets"])
async def generate_dungeon(req: DungeonRequest) -> AssetResponse:
    """Generate a BSP dungeon / cave level as a .vox file."""
    try:
        gen   = DungeonGenerator(_palette(), seed=req.seed)
        model = gen.generate(
            width       = req.width,
            height      = req.height,
            wall_height = req.wall_height,
            style       = req.style.value,
        )
        model.name = req.name
        path = _asset_path("dungeons", req.name)
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
# Image / Sprite generation  (acatovic/ai-game-studio pattern)
# ---------------------------------------------------------------------------

@app.post("/sprite/generate", response_model=SpriteGenerateResponse, tags=["sprites"])
async def generate_sprite(req: SpriteGenerateRequest) -> SpriteGenerateResponse:
    """
    Generate an AI sprite from a text prompt.

    Uses OpenRouter (Grok Imagine, FLUX, DALL-E) when OPENROUTER_API_KEY or
    OPENAI_API_KEY is set.  Falls back to procedural pixel art without an API key.
    Chroma-key (#00b140) background removal is applied automatically.
    """
    try:
        from ..imagegen import SpriteGenerator
        gen = SpriteGenerator(output_dir=os.path.join(ASSETS_DIR, "sprites"))

        if req.animated:
            result = gen.generate_animated(
                prompt      = req.prompt,
                name        = req.name,
                style_hint  = req.style,
                frame_count = req.frames,
            )
            return SpriteGenerateResponse(
                status      = "ok",
                name        = req.name,
                image_path  = _engine_rel(result.spritesheet),
                image_b64   = "",
                model_used  = result.model_used,
                width       = 0,
                height      = 0,
                has_alpha   = True,
                source      = "ai",
                spritesheet = _engine_rel(result.spritesheet),
                gif_path    = _engine_rel(result.gif_path),
                frame_count = result.frame_count,
            )
        else:
            result = gen.generate(
                prompt     = req.prompt,
                name       = req.name,
                size       = req.size,
                remove_bg  = req.remove_bg,
                style_hint = req.style,
            )
            return SpriteGenerateResponse(
                status     = "ok",
                name       = req.name,
                image_path = _engine_rel(result.image_path),
                image_b64  = result.image_b64,
                model_used = result.model_used,
                width      = result.width,
                height     = result.height,
                has_alpha  = result.has_alpha,
                source     = result.source,
                frame_count= 1,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/sprite/batch", tags=["sprites"])
async def generate_sprite_batch(req: BatchSpriteRequest) -> Dict[str, Any]:
    """Generate multiple sprites from a list of prompts."""
    try:
        from ..imagegen import SpriteGenerator
        gen     = SpriteGenerator(output_dir=os.path.join(ASSETS_DIR, "sprites"))
        results = gen.generate_batch(req.prompts, names=req.names, remove_bg=req.remove_bg)
        return {
            "status": "ok",
            "count":  len(results),
            "sprites": [
                {"name": r.image_path, "model": r.model_used, "source": r.source}
                for r in results
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/sprite/remove-bg", tags=["sprites"])
async def remove_background(path: str) -> Dict[str, Any]:
    """Apply chroma-key background removal to an existing image."""
    try:
        from ..imagegen import remove_background as _rb
        full = os.path.abspath(path)
        if not os.path.isfile(full):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        out = _rb(full)
        return {"status": "ok", "path": _engine_rel(out)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Narrative Engine  (ackness/ai-gamestudio pattern)
# ---------------------------------------------------------------------------

_narrative_engines: Dict[str, Any] = {}   # session_id → NarrativeEngine

def _get_narrative_engine(api_key: str = "", model: str = "") -> Any:
    from ..narrative import NarrativeEngine
    return NarrativeEngine(
        llm_model   = model or os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        llm_api_key = api_key or os.environ.get("LLM_API_KEY", "")
                              or os.environ.get("OPENAI_API_KEY", ""),
        db_path     = os.path.join(ASSETS_DIR, "narrative.db"),
    )


@app.post("/narrative/session", response_model=NarrativeSessionResponse, tags=["narrative"])
async def start_narrative_session(req: NarrativeSessionRequest) -> NarrativeSessionResponse:
    """
    Start a new LLM-driven interactive game session.

    The narrative engine uses a dual-model architecture: a primary LLM for
    storytelling and a plugin agent for game mechanics (combat, inventory, social).
    Game state is persisted in SQLite.
    """
    try:
        engine  = _get_narrative_engine(req.api_key, req.model)
        session = engine.start_session(
            player_name = req.player_name,
            genre       = req.genre,
            world_text  = req.world_text or "",
        )
        return NarrativeSessionResponse(
            status     = "ok",
            session_id = session.id,
            genre      = session.genre,
            player     = session.player_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/narrative/chat", response_model=NarrativeMessageResponse, tags=["narrative"])
async def narrative_chat(req: NarrativeMessageRequest) -> NarrativeMessageResponse:
    """
    Send a player message and receive narrative response with game mechanics.

    Returns structured blocks: narrative text, choices, combat results, items, etc.
    """
    try:
        engine   = _get_narrative_engine()
        response = engine.send_message(req.session_id, req.message)
        session  = engine.get_session_status(req.session_id)
        return NarrativeMessageResponse(
            status     = "ok",
            session_id = req.session_id,
            turn_id    = response.turn_id,
            blocks     = [b.to_dict() for b in response.blocks],
            text       = response.text(),
            choices    = response.choices(),
            hp         = session.get("hp", 100),
            score      = session.get("score", 0),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/narrative/sessions", tags=["narrative"])
async def list_narrative_sessions() -> Dict[str, Any]:
    """List all active narrative game sessions."""
    try:
        engine = _get_narrative_engine()
        return {"status": "ok", "sessions": engine.list_sessions()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/narrative/status/{session_id}", tags=["narrative"])
async def narrative_session_status(session_id: str) -> Dict[str, Any]:
    """Get current status of a narrative session (HP, score, inventory, etc.)."""
    try:
        engine = _get_narrative_engine()
        return {"status": "ok", **engine.get_session_status(session_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# 12-Agent Pipeline  (pamirtuna/gamestudio-subagents pattern)
# ---------------------------------------------------------------------------

@app.post("/pipeline/run", response_model=PipelineResponse, tags=["pipeline"])
async def run_pipeline(req: PipelineRequest) -> PipelineResponse:
    """
    Run the full 12-agent game development pipeline.

    Phases:
    1. Market Validation — LLM market analyst gives Go/No-Go
    2. Design — GDD, pillars, milestones, analytics plan
    3. Build — VoxelForge game generation (if build_game=true)
    4. QA — Test plan, asset validation

    Works with or without an LLM API key (template fallbacks when no key is set).
    """
    try:
        from ..pipeline import GamePipeline
        pipeline = GamePipeline(output_dir=os.path.join(ASSETS_DIR, "pipeline_projects"))
        result   = pipeline.run(
            concept    = req.concept,
            genre      = req.genre,
            platform   = req.platform,
            audience   = req.audience,
            mode       = req.mode,
            timeline   = req.timeline,
            competitors= req.competitors,
            usp        = req.usp,
            seed       = req.seed,
            build_game = req.build_game,
        )
        return PipelineResponse(
            status                 = "ok",
            concept                = result.concept,
            mode                   = result.mode,
            agents_used            = len(result.agents),
            market_recommendation  = result.market.recommendation if result.market else None,
            market_score           = result.market.opportunity_score if result.market else None,
            gdd_path               = result.design.gdd_path if result.design else None,
            build_path             = result.build.scene_path if result.build else None,
            run_command            = result.build.run_command if result.build else None,
            qa_passed              = result.qa.passed if result.qa else None,
            elapsed_s              = result.elapsed_s,
            project_dir            = result.project_dir,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Project lifecycle  (full project management)
# ---------------------------------------------------------------------------

@app.post("/project/init", response_model=ProjectStatusResponse, tags=["project"])
async def init_project(req: ProjectInitRequest) -> ProjectStatusResponse:
    """
    Initialize a new game project with full folder structure and agent config.

    Creates project directories, GDD, market research scaffolding,
    timeline, engine-specific files, and CLAUDE.md agent configuration.
    Supports: voxelforge | godot | unity | unreal
    """
    try:
        from ..project import ProjectManager
        pm   = ProjectManager(os.path.join(ASSETS_DIR, "projects"))
        proj = pm.init_project(
            name              = req.name,
            concept           = req.concept,
            genre             = req.genre,
            platform          = req.platform,
            audience          = req.audience,
            engine            = req.engine,
            mode              = req.mode,
            timeline          = req.timeline,
            usp               = req.usp,
            competitors       = req.competitors,
            development_rules = req.development_rules,
        )
        return ProjectStatusResponse(
            status  = "ok",
            project = {
                "name":    proj.config.name,
                "slug":    proj.config.slug,
                "path":    proj.path,
                "engine":  proj.config.engine,
                "agents":  len(proj.config.active_agents),
                "milestone": proj.next_milestone(),
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/project/list", tags=["project"])
async def list_projects() -> Dict[str, Any]:
    """List all initialized projects."""
    try:
        from ..project import ProjectManager
        pm = ProjectManager(os.path.join(ASSETS_DIR, "projects"))
        return {"status": "ok", "projects": pm.list_projects()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/project/{slug}", tags=["project"])
async def get_project(slug: str) -> Dict[str, Any]:
    """Get project details by slug."""
    try:
        from ..project import ProjectManager
        pm   = ProjectManager(os.path.join(ASSETS_DIR, "projects"))
        proj = pm.load_project(slug)
        return {
            "status":  "ok",
            "summary": proj.status_summary(),
            "config":  proj.config.to_json_dict(),
            "next_milestone": proj.next_milestone(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Game generator endpoint
# ---------------------------------------------------------------------------

@app.post("/game/generate", response_model=GameGenerateResponse, tags=["game"])
async def generate_game(req: GameGenerateRequest) -> GameGenerateResponse:
    """
    Generate a **complete, playable mini-game** in one API call.

    Creates all voxel assets (level/terrain, player, enemies, props),
    Lua game scripts (player controller, enemy AI, objective system),
    and a scene file that ties everything together.

    The result is immediately playable with:
        ``cd engine && ./voxelforge --scene ../<scene_path>``
    """
    try:
        from ..generators.game import GameGenerator
        gen      = GameGenerator(_palette(), seed=req.seed,
                                  output_dir=ASSETS_DIR)
        manifest = gen.generate(
            title        = req.title,
            genre        = req.genre.value,
            theme        = req.theme,
            player_class = req.player_class,
            enemies      = req.enemies,
            props        = req.props,
            level_size   = req.level_size,
        )
        return GameGenerateResponse(
            status        = "ok",
            title         = req.title,
            genre         = req.genre.value,
            scene_path    = _engine_rel(manifest["scene_path"]),
            manifest_path = _engine_rel(manifest["manifest_path"]),
            run_command   = manifest["run_command"],
            entity_count  = manifest["entity_count"],
            asset_count   = len(manifest["assets"]),
            script_count  = len(manifest["scripts"]),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# HTML5 Game Generator
# ---------------------------------------------------------------------------

@app.post("/html/generate", response_model=HTML5GameResponse, tags=["html-games"])
async def generate_html5_game(req: HTML5GameRequest) -> HTML5GameResponse:
    """
    Generate a complete, immediately-playable single-file HTML5 game.
    Uses free LLMs (Groq, Cerebras, Gemini, OpenRouter) automatically.
    Falls back to a procedural canvas game if no API key is configured.
    Open the returned html_path directly in any browser — no setup needed.
    """
    try:
        from ..gamegen import HTML5GameGenerator
        gen  = HTML5GameGenerator(output_dir=os.path.join(ASSETS_DIR, "games", "html"))
        game = gen.generate(
            prompt     = req.prompt,
            genre      = req.genre,
            title      = req.title,
            name       = req.name,
            max_tokens = req.max_tokens,
        )
        return HTML5GameResponse(
            status    = "ok",
            title     = game.title,
            genre     = game.genre,
            html_path = _engine_rel(game.html_path),
            open_url  = game.open_url(),
            valid     = game.valid,
            provider  = game.provider,
            model     = game.model,
            issues    = game.issues,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Sprite Sheet Generator (advanced styles + animation actions)
# ---------------------------------------------------------------------------

@app.post("/sprite/sheet", response_model=SpriteSheetResponse, tags=["sprites"])
async def generate_sprite_sheet(req: SpriteSheetRequest) -> SpriteSheetResponse:
    """
    Generate a full character sprite sheet with multiple animation actions.
    Supports 11 game art styles (Stardew Valley, Hollow Knight, Genshin Impact, etc.)
    and 12 animation actions (idle, walk, run, jump, attack, cast, hurt, death...).
    """
    try:
        from ..spritesheet import SpriteSheetForge, GameStyle, AnimationAction
        forge_ss = SpriteSheetForge(output_dir=os.path.join(ASSETS_DIR, "sprites"))
        style    = GameStyle(req.style) if req.style in [e.value for e in GameStyle] else GameStyle.PIXEL_ART_RPG
        valid_actions = {e.value for e in AnimationAction}
        actions  = [AnimationAction(a) for a in req.actions if a in valid_actions]
        if not actions:
            actions = [AnimationAction.IDLE, AnimationAction.WALK]
        result   = forge_ss.generate_character_sheet(
            description = req.description,
            style       = style,
            actions     = actions,
            name        = req.name,
        )
        return SpriteSheetResponse(
            status           = "ok",
            spritesheet_path = _engine_rel(result.spritesheet_path),
            frame_count      = result.frame_count,
            gif_path         = _engine_rel(result.gif_path) if result.gif_path else None,
            has_alpha        = result.has_alpha,
            source           = result.source,
            style            = req.style,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/sprite/batch-sheet", tags=["sprites"])
async def generate_batch_sprite_sheet(req: BatchSpriteSheetRequest) -> Dict[str, Any]:
    """
    Generate a batch of props/items using grid-based generation.
    25 items per API call — approximately 30x cheaper than individual generation.
    """
    try:
        from ..spritesheet import SpriteSheetForge, GameStyle
        forge_ss = SpriteSheetForge(output_dir=os.path.join(ASSETS_DIR, "sprites"))
        style    = GameStyle(req.style) if req.style in [e.value for e in GameStyle] else GameStyle.PIXEL_ART_RPG
        result   = forge_ss.generate_prop_batch(
            prompts   = req.prompts,
            style     = style,
            grid_size = req.grid_size,
            name      = req.name,
        )
        return {
            "status":  "ok",
            "count":   len(result.image_paths),
            "images":  result.image_paths,
            "source":  result.source,
            "style":   req.style,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Asset Pipeline (storyline → NPCs → quests → dialogue → items)
# ---------------------------------------------------------------------------

@app.post("/pipeline/assets", response_model=AssetPipelineResponse, tags=["pipeline"])
async def run_asset_pipeline(req: AssetPipelineRequest) -> AssetPipelineResponse:
    """
    Run the full narrative asset pipeline using free LLMs.

    Generates: storyline → 2 NPC characters → backstories → quests →
    branching dialogue trees (JSON) → game items with visual descriptions →
    world elements → Lua scripts ready for VoxelForge.

    Works with Groq/Gemini/Cerebras/OpenRouter free tier or no API key at all
    (template fallbacks ensure output is always produced).
    """
    try:
        from ..gamegen import AssetPipeline
        pipeline = AssetPipeline(output_dir=os.path.join(ASSETS_DIR, "narrative_packs"))
        pack     = pipeline.run(
            theme   = req.theme,
            details = req.details,
            genre   = req.genre,
            seed    = req.seed,
        )
        paths = pack.save()
        return AssetPipelineResponse(
            status      = "ok",
            output_dir  = _engine_rel(pack.output_dir),
            files_saved = len(paths),
            characters  = len(pack.characters),
            quests      = len(pack.quests),
            items       = len(pack.items),
            lua_scripts = list(pack.lua_scripts.keys()),
            model       = pack.model,
            provider    = pack.provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Free LLM Router
# ---------------------------------------------------------------------------

@app.post("/llm/chat", response_model=LLMChatResponse, tags=["llm"])
async def llm_chat(req: LLMChatRequest) -> LLMChatResponse:
    """
    Send a prompt to the best available free LLM provider.

    Auto-routes through: Groq → Cerebras → SambaNova → NVIDIA NIM →
    Gemini → OpenRouter free → LLM7 → Together AI → Ollama (local).

    Task hints select the best model for the job:
    - fast: 8B models for quick responses
    - code: coding-optimized models
    - creative: larger models for story/design generation
    """
    try:
        from ..llm_router import get_router
        router = get_router()
        resp   = router.chat(
            prompt      = req.prompt,
            system      = req.system or None,
            task        = req.task,
            provider    = req.provider or None,
            max_tokens  = req.max_tokens,
            temperature = req.temperature,
        )
        return LLMChatResponse(
            status     = "ok",
            text       = resp.text,
            provider   = resp.provider,
            model      = resp.model,
            latency_ms = resp.latency_ms,
            ok         = resp.ok,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/llm/providers", response_model=LLMProvidersResponse, tags=["llm"])
async def list_llm_providers() -> LLMProvidersResponse:
    """
    List all LLM providers and which ones have an API key configured.
    Shows free tier info for each provider.
    """
    try:
        from ..llm_router import LLMRouter, _PROVIDERS
        router = LLMRouter()
        avail  = router.available_providers()
        all_p  = [
            {
                "name":      p.name,
                "priority":  p.priority,
                "free_note": p.free_note,
                "has_key":   bool(os.environ.get(p.env_key, "")),
                "models":    list(p.models.values())[:3],
            }
            for p in _PROVIDERS
        ]
        return LLMProvidersResponse(
            available     = avail,
            all_providers = all_p,
            count         = len(avail),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Agent endpoint — run the autonomous AI agent server-side
# ---------------------------------------------------------------------------

@app.post("/agent/run", response_model=AgentRunResponse, tags=["agent"])
async def run_agent(req: AgentRunRequest) -> AgentRunResponse:
    """
    Run the VoxelForge autonomous agent with a text prompt.

    The agent plans and generates a complete game world (terrain, buildings,
    characters, props, scene file) from the given description.

    Set ``direct_mode=true`` (default) for instant generation with the
    keyword parser — no LLM or API key needed.

    Set ``direct_mode=false`` to use an LLM (requires ``OPENAI_API_KEY``
    to be set in the server environment).
    """
    try:
        from ..ai.agent import VoxelForgeAgent
        agent  = VoxelForgeAgent(
            model       = req.model,
            direct_mode = req.direct_mode,
            verbose     = False,
        )
        result = agent.run(req.prompt)
        return AgentRunResponse(
            status          = "ok",
            scene_path      = result.get("scene_path", ""),
            asset_paths     = result.get("asset_paths", []),
            entity_count    = result.get("entity_count", 0),
            elapsed_seconds = result.get("elapsed_seconds", 0.0),
            mode            = result.get("mode", "direct"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
