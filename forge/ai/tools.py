"""
forge.ai.tools
==============
OpenAI-compatible function-calling tool definitions for VoxelForge.

Every tool maps 1-to-1 with a REST API endpoint so any LLM that supports
function calling (GPT-4o, Claude, Gemini, Llama-3 tool-use, etc.) can
call them natively.

``call_tool`` first tries the running API server; if it is unreachable it
falls back to calling the Python generators directly — so everything works
offline without a running server too.

Usage (OpenAI SDK)
------------------
>>> import openai
>>> from forge.ai.tools import TOOLS, call_tool
>>>
>>> response = openai.chat.completions.create(
...     model="gpt-4o",
...     messages=[{"role": "user", "content": "Build me a medieval village"}],
...     tools=TOOLS,
... )
>>> for tc in response.choices[0].message.tool_calls or []:
...     result = call_tool(tc.function.name, tc.function.arguments)
"""

from __future__ import annotations

import json
import os
import random
from typing import Any, Dict, List

import requests


# ---------------------------------------------------------------------------
# API base URL — override with VOXELFORGE_API_URL env var
# ---------------------------------------------------------------------------

_API_URL = os.environ.get("VOXELFORGE_API_URL", "http://localhost:8080")
_ASSETS_DIR = os.environ.get("VOXELFORGE_ASSETS_DIR", "generated_assets")


def _post(endpoint: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """POST to the VoxelForge API and return the parsed JSON response."""
    url = f"{_API_URL}{endpoint}"
    resp = requests.post(url, json=body, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _get(endpoint: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    url = f"{_API_URL}{endpoint}"
    resp = requests.get(url, params=params or {}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _api_available() -> bool:
    """Check if the API server is reachable."""
    try:
        requests.get(f"{_API_URL}/health", timeout=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Local fallback — direct Python generation (no HTTP)
# ---------------------------------------------------------------------------

def _local_asset_path(subdir: str, name: str) -> str:
    d = os.path.join(_ASSETS_DIR, subdir)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{name}.vox")


def _local_scene_path(name: str) -> str:
    d = os.path.join(_ASSETS_DIR, "scenes")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{name}.scene")


def _engine_rel(full_path: str) -> str:
    try:
        return os.path.relpath(full_path)
    except ValueError:
        return full_path


def _local_generate_terrain(biome="grassland", width=32, height=32, max_depth=12,
                              seed=0, name="terrain", **_) -> Dict[str, Any]:
    from ..voxel import Palette
    from ..generators.terrain import TerrainGenerator
    gen   = TerrainGenerator(Palette.natural(), seed=seed)
    model = gen.generate(width=width, height=height, max_depth=max_depth, biome=biome)
    model.name = name
    path = _local_asset_path("terrain", name)
    model.save(path)
    return {"status": "ok", "name": name, "path": _engine_rel(path),
            "voxel_count": model.voxel_count(),
            "dimensions": [model.width, model.height, model.depth]}


def _local_generate_building(style="modern", width=8, depth=8, floors=3,
                               seed=0, name="building", **_) -> Dict[str, Any]:
    from ..voxel import Palette
    from ..generators.buildings import BuildingGenerator
    gen   = BuildingGenerator(Palette.natural(), seed=seed)
    model = gen.generate(width=width, depth=depth, floors=floors, style=style, name=name)
    path  = _local_asset_path("buildings", name)
    model.save(path)
    return {"status": "ok", "name": name, "path": _engine_rel(path),
            "voxel_count": model.voxel_count(),
            "dimensions": [model.width, model.height, model.depth]}


def _local_generate_character(class_type="warrior", skin_tone="tan", hair_color="brown",
                                armour="chainmail", weapon="sword", seed=0,
                                name="character", **_) -> Dict[str, Any]:
    from ..voxel import Palette
    from ..generators.characters import CharacterGenerator
    gen   = CharacterGenerator(Palette.natural(), seed=seed)
    model = gen.generate(class_type=class_type, skin_tone=skin_tone,
                         hair_color=hair_color, armour=armour, weapon=weapon, name=name)
    path  = _local_asset_path("characters", name)
    model.save(path)
    return {"status": "ok", "name": name, "path": _engine_rel(path),
            "voxel_count": model.voxel_count(),
            "dimensions": [model.width, model.height, model.depth]}


def _local_generate_prop(prop_type="tree", variant="", seed=0, name="", **kw) -> Dict[str, Any]:
    from ..voxel import Palette
    from ..generators.props import PropGenerator
    gen  = PropGenerator(Palette.natural(), seed=seed)
    nm   = name or prop_type
    model= gen.generate(prop_type, variant=variant, name=nm)
    path = _local_asset_path("props", nm)
    model.save(path)
    return {"status": "ok", "name": nm, "path": _engine_rel(path),
            "voxel_count": model.voxel_count(),
            "dimensions": [model.width, model.height, model.depth]}


def _local_build_scene(scene_name, entities, lights=None,
                        background_color=None, **_) -> Dict[str, Any]:
    from ..scene import Scene
    scene = Scene(background_color=tuple(background_color) if background_color
                  else (0.0, 0.149, 0.294))
    for ent in entities:
        scene.add_voxel_model(
            ent["name"], ent["asset"],
            position=tuple(ent.get("position", [0, 0, 0])),
            rotation=tuple(ent.get("rotation", [0, 0, 0])),
        )
    for light in (lights or []):
        scene.add_point_light(
            light["name"],
            position=tuple(light.get("position", [0, 10, 0])),
            color=tuple(light.get("color", [1, 1, 1])),
            intensity=float(light.get("intensity", 1.0)),
            range_=float(light.get("range", light.get("range_", 100.0))),
            hue_shift=float(light.get("hueShift", 0.0)),
        )
    path = _local_scene_path(scene_name)
    scene.save(path)
    return {"status": "ok", "scene_name": scene_name, "path": _engine_rel(path),
            "entity_count": scene.entity_count}


def _local_build_world(name="world", biome="grassland", width=64, height=64,
                        buildings=3, building_style="medieval", characters=2,
                        props=5, seed=0, **_) -> Dict[str, Any]:
    from ..voxel import Palette
    from ..generators.terrain import TerrainGenerator
    from ..generators.buildings import BuildingGenerator
    from ..generators.characters import CharacterGenerator
    from ..generators.props import PropGenerator
    from ..scene import Scene

    rng   = random.Random(seed)
    pal   = Palette.natural()
    scene = Scene(background_color=(0.05, 0.15, 0.30))
    asset_paths: List[str] = []

    # Terrain
    terrain = TerrainGenerator(pal, seed=seed).generate(
        width=width, height=height, max_depth=14, biome=biome)
    terrain.name = f"{name}_terrain"
    t_path = _local_asset_path("terrain", terrain.name)
    terrain.save(t_path)
    asset_paths.append(_engine_rel(t_path))
    scene.add_voxel_model("terrain", _engine_rel(t_path))

    surface_z = 14.0
    bgen = BuildingGenerator(pal, seed=seed + 1)
    for i in range(buildings):
        b_name = f"{name}_building_{i}"
        model  = bgen.generate(rng.randint(6, 12), rng.randint(6, 12),
                                rng.randint(2, 6), style=building_style, name=b_name)
        p = _local_asset_path("buildings", b_name)
        model.save(p)
        asset_paths.append(_engine_rel(p))
        scene.add_voxel_model(b_name, _engine_rel(p),
            position=(float(rng.randint(0, max(1, width-10))),
                      float(rng.randint(0, max(1, height-10))),
                      surface_z))

    cgen = CharacterGenerator(pal, seed=seed + 2)
    for i in range(characters):
        c_name = f"{name}_char_{i}"
        model  = cgen.generate(
            rng.choice(["warrior","mage","archer","rogue"]),
            rng.choice(["light","tan","dark"]),
            rng.choice(["blonde","brown","black"]),
            rng.choice(["leather","chainmail","plate"]),
            rng.choice(["sword","staff","bow"]),
            name=c_name)
        p = _local_asset_path("characters", c_name)
        model.save(p)
        asset_paths.append(_engine_rel(p))
        scene.add_voxel_model(c_name, _engine_rel(p),
            position=(float(rng.randint(0, max(1, width-4))),
                      float(rng.randint(0, max(1, height-4))),
                      surface_z))

    pgen = PropGenerator(pal, seed=seed + 3)
    for i in range(props):
        p_type = rng.choice(["tree","crate","barrel","rock","mushroom","chest"])
        p_name = f"{name}_prop_{p_type}_{i}"
        model  = pgen.generate(p_type, name=p_name)
        p      = _local_asset_path("props", p_name)
        model.save(p)
        asset_paths.append(_engine_rel(p))
        scene.add_voxel_model(p_name, _engine_rel(p),
            position=(float(rng.randint(0, max(1, width-8))),
                      float(rng.randint(0, max(1, height-8))),
                      surface_z))

    scene.add_point_light("sun",
        position=(float(width//2), float(height//2), 40.0),
        color=(1.0, 0.95, 0.85), intensity=2.0,
        range_=float(max(width, height) * 2))

    s_path = _local_scene_path(name)
    scene.save(s_path)

    return {"status": "ok", "world_name": name,
            "scene_path": _engine_rel(s_path),
            "asset_paths": asset_paths,
            "entity_count": scene.entity_count,
            "seed": seed}


def _local_list_assets(subdir="", **_) -> Dict[str, Any]:
    import glob
    pattern = os.path.join(_ASSETS_DIR, subdir or "**", "*.vox")
    files   = glob.glob(pattern, recursive=True)
    return {"assets": [{"path": _engine_rel(f), "name": os.path.splitext(os.path.basename(f))[0]}
                       for f in sorted(files)]}


def _local_list_scenes(**_) -> Dict[str, Any]:
    import glob
    files = glob.glob(os.path.join(_ASSETS_DIR, "scenes", "*.scene"))
    return {"scenes": [{"path": _engine_rel(f),
                        "name": os.path.splitext(os.path.basename(f))[0]}
                       for f in sorted(files)]}


_LOCAL_DISPATCH: Dict[str, Any] = {
    "generate_terrain":   _local_generate_terrain,
    "generate_building":  _local_generate_building,
    "generate_character": _local_generate_character,
    "generate_prop":      _local_generate_prop,
    "build_scene":        _local_build_scene,
    "build_world":        _local_build_world,
    "list_assets":        _local_list_assets,
    "list_scenes":        _local_list_scenes,
}


# ---------------------------------------------------------------------------
# HTTP-based tool implementations
# ---------------------------------------------------------------------------

def generate_terrain(biome="grassland", width=32, height=32, max_depth=12,
                      seed=0, name="terrain") -> Dict[str, Any]:
    """Generate procedural voxel terrain and save it as a .vox file."""
    return _post("/asset/terrain", {"biome": biome, "width": width, "height": height,
                                     "max_depth": max_depth, "seed": seed, "name": name})


def generate_building(style="modern", width=8, depth=8, floors=3,
                       seed=0, name="building") -> Dict[str, Any]:
    """Generate a procedural voxel building and save it as a .vox file."""
    return _post("/asset/building", {"style": style, "width": width, "depth": depth,
                                      "floors": floors, "seed": seed, "name": name})


def generate_character(class_type="warrior", skin_tone="tan", hair_color="brown",
                        armour="chainmail", weapon="sword", seed=0,
                        name="character") -> Dict[str, Any]:
    """Generate a procedural voxel humanoid character and save it as a .vox file."""
    return _post("/asset/character", {"class_type": class_type, "skin_tone": skin_tone,
                                       "hair_color": hair_color, "armour": armour,
                                       "weapon": weapon, "seed": seed, "name": name})


def generate_prop(prop_type="tree", variant="", seed=0, name="") -> Dict[str, Any]:
    """Generate a procedural voxel prop and save it as a .vox file."""
    return _post("/asset/prop", {"prop_type": prop_type, "variant": variant,
                                  "seed": seed, "name": name})


def build_scene(scene_name, entities, lights=None,
                 background_color=None) -> Dict[str, Any]:
    """Construct a VoxelForge scene from entity and light placements."""
    body: Dict[str, Any] = {"scene_name": scene_name, "entities": entities,
                             "lights": lights or []}
    if background_color:
        body["background_color"] = background_color
    return _post("/scene/build", body)


def build_world(name, biome="grassland", width=64, height=64, buildings=3,
                 building_style="medieval", characters=2, props=5,
                 seed=0) -> Dict[str, Any]:
    """Build a complete game world in one call."""
    return _post("/world/build", {"name": name, "biome": biome, "width": width,
                                   "height": height, "buildings": buildings,
                                   "building_style": building_style,
                                   "characters": characters, "props": props, "seed": seed})


def list_assets(subdir="") -> Dict[str, Any]:
    """List all generated .vox assets."""
    return _get("/assets", {"subdir": subdir} if subdir else {})


def list_scenes() -> Dict[str, Any]:
    """List all generated scene files."""
    return _get("/scenes")


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

_HTTP_MAP = {
    "generate_terrain":   generate_terrain,
    "generate_building":  generate_building,
    "generate_character": generate_character,
    "generate_prop":      generate_prop,
    "build_scene":        build_scene,
    "build_world":        build_world,
    "list_assets":        list_assets,
    "list_scenes":        list_scenes,
}


def call_tool(name: str, arguments: str | Dict[str, Any]) -> Any:
    """
    Execute a VoxelForge tool by name with JSON arguments.

    Tries the HTTP API server first; falls back to direct Python execution
    if the server is not reachable.

    Parameters
    ----------
    name : str
        Tool function name (e.g. "generate_terrain").
    arguments : str | dict
        JSON string or dict of arguments.
    """
    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    # Try HTTP API first
    http_fn = _HTTP_MAP.get(name)
    if http_fn is None:
        return {"error": f"Unknown tool: {name}"}

    try:
        return http_fn(**arguments)
    except (requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
            requests.exceptions.Timeout):
        pass  # API not running or unhealthy — fall back to local
    except Exception as exc:
        # Non-HTTP error — still try local before giving up
        pass

    # Local fallback
    local_fn = _LOCAL_DISPATCH.get(name)
    if local_fn:
        try:
            return local_fn(**arguments)
        except Exception as exc:
            return {"error": f"Local execution failed: {exc}"}

    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# OpenAI-compatible tool definitions
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "generate_terrain",
            "description": "Generate procedural voxel terrain for a game world and save it as a .vox file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "biome":     {"type": "string",  "enum": ["grassland","desert","snow","ocean","forest"]},
                    "width":     {"type": "integer", "default": 32},
                    "height":    {"type": "integer", "default": 32},
                    "max_depth": {"type": "integer", "default": 12},
                    "seed":      {"type": "integer", "default": 0},
                    "name":      {"type": "string",  "default": "terrain"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_building",
            "description": "Generate a procedural voxel building and save it as a .vox file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style":  {"type": "string",  "enum": ["modern","medieval","sci-fi","rustic","fantasy"]},
                    "width":  {"type": "integer", "default": 8},
                    "depth":  {"type": "integer", "default": 8},
                    "floors": {"type": "integer", "default": 3},
                    "seed":   {"type": "integer", "default": 0},
                    "name":   {"type": "string",  "default": "building"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_character",
            "description": "Generate a procedural voxel humanoid character and save it as a .vox file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "class_type": {"type": "string", "enum": ["warrior","mage","archer","rogue"]},
                    "skin_tone":  {"type": "string", "enum": ["light","tan","dark","fantasy"]},
                    "hair_color": {"type": "string", "enum": ["blonde","brown","black","red","white","blue"]},
                    "armour":     {"type": "string", "enum": ["none","leather","chainmail","plate","mage"]},
                    "weapon":     {"type": "string", "enum": ["none","sword","staff","bow","axe"]},
                    "seed":       {"type": "integer", "default": 0},
                    "name":       {"type": "string",  "default": "character"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_prop",
            "description": "Generate a small voxel prop (tree, crate, barrel, lamp_post, rock, chest, mushroom).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prop_type": {"type": "string", "enum": ["tree","crate","barrel","lamp_post","rock","chest","mushroom"]},
                    "variant":   {"type": "string", "default": ""},
                    "seed":      {"type": "integer", "default": 0},
                    "name":      {"type": "string",  "default": ""},
                },
                "required": ["prop_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_scene",
            "description": "Construct a VoxelForge scene file from entity placements and lights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_name": {"type": "string"},
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name":     {"type": "string"},
                                "asset":    {"type": "string"},
                                "position": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                                "rotation": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                            },
                            "required": ["name", "asset"],
                        },
                    },
                    "lights": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name":      {"type": "string"},
                                "position":  {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                                "color":     {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                                "intensity": {"type": "number"},
                                "radius":    {"type": "number"},
                            },
                            "required": ["name"],
                        },
                    },
                    "background_color": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                },
                "required": ["scene_name", "entities"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_world",
            "description": (
                "Build a COMPLETE game world: terrain + buildings + characters + props + scene. "
                "Use this for full autonomous game creation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name":           {"type": "string"},
                    "biome":          {"type": "string",  "enum": ["grassland","desert","snow","ocean","forest"]},
                    "width":          {"type": "integer", "default": 64},
                    "height":         {"type": "integer", "default": 64},
                    "buildings":      {"type": "integer", "default": 3},
                    "building_style": {"type": "string",  "default": "medieval"},
                    "characters":     {"type": "integer", "default": 2},
                    "props":          {"type": "integer", "default": 5},
                    "seed":           {"type": "integer", "default": 0},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_assets",
            "description": "List all generated .vox asset files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subdir": {"type": "string", "default": ""},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_scenes",
            "description": "List all generated scene files.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
