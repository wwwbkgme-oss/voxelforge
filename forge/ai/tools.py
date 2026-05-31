"""
forge.ai.tools
==============
OpenAI-compatible function-calling tool definitions for VoxelForge.

Every tool maps 1-to-1 with a REST API endpoint so any LLM that supports
function calling (GPT-4o, Claude, Gemini, Llama-3 tool-use, etc.) can
call them natively.

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
>>> # Execute tool calls:
>>> for tc in response.choices[0].message.tool_calls or []:
...     result = call_tool(tc.function.name, tc.function.arguments)

Using without the API server (direct Python calls)
---------------------------------------------------
>>> result = call_tool("generate_terrain", '{"biome": "grassland", "width": 48}')
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import requests


# ---------------------------------------------------------------------------
# API base URL — override with VOXELFORGE_API_URL env var
# ---------------------------------------------------------------------------

_API_URL = os.environ.get("VOXELFORGE_API_URL", "http://localhost:8080")


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


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def generate_terrain(
    biome: str = "grassland",
    width: int = 32,
    height: int = 32,
    max_depth: int = 12,
    seed: int = 0,
    name: str = "terrain",
) -> Dict[str, Any]:
    """Generate procedural voxel terrain and save it as a .vox file."""
    return _post("/asset/terrain", {
        "biome": biome, "width": width, "height": height,
        "max_depth": max_depth, "seed": seed, "name": name,
    })


def generate_building(
    style: str = "modern",
    width: int = 8,
    depth: int = 8,
    floors: int = 3,
    seed: int = 0,
    name: str = "building",
) -> Dict[str, Any]:
    """Generate a procedural voxel building and save it as a .vox file."""
    return _post("/asset/building", {
        "style": style, "width": width, "depth": depth,
        "floors": floors, "seed": seed, "name": name,
    })


def generate_character(
    class_type: str = "warrior",
    skin_tone: str = "tan",
    hair_color: str = "brown",
    armour: str = "chainmail",
    weapon: str = "sword",
    seed: int = 0,
    name: str = "character",
) -> Dict[str, Any]:
    """Generate a procedural voxel humanoid character and save it as a .vox file."""
    return _post("/asset/character", {
        "class_type": class_type, "skin_tone": skin_tone,
        "hair_color": hair_color, "armour": armour, "weapon": weapon,
        "seed": seed, "name": name,
    })


def generate_prop(
    prop_type: str = "tree",
    variant: str = "",
    seed: int = 0,
    name: str = "",
) -> Dict[str, Any]:
    """
    Generate a procedural voxel prop (tree/crate/barrel/lamp_post/rock/chest/mushroom)
    and save it as a .vox file.
    """
    return _post("/asset/prop", {
        "prop_type": prop_type, "variant": variant,
        "seed": seed, "name": name,
    })


def build_scene(
    scene_name: str,
    entities: List[Dict[str, Any]],
    lights: List[Dict[str, Any]] | None = None,
    background_color: List[float] | None = None,
) -> Dict[str, Any]:
    """
    Construct a VoxelForge scene from entity and light placements.

    Each entity has: name, asset (path), position [x,y,z], rotation [x,y,z].
    Each light  has: name, position [x,y,z], color [r,g,b], intensity, radius.
    """
    body: Dict[str, Any] = {
        "scene_name": scene_name,
        "entities": entities,
        "lights":   lights or [],
    }
    if background_color:
        body["background_color"] = background_color
    return _post("/scene/build", body)


def build_world(
    name: str,
    biome: str = "grassland",
    width: int = 64,
    height: int = 64,
    buildings: int = 3,
    building_style: str = "medieval",
    characters: int = 2,
    props: int = 5,
    seed: int = 0,
) -> Dict[str, Any]:
    """
    Build a complete game world in one call: terrain + buildings + characters
    + props + a scene file that ties them all together.
    Returns paths to the scene file and all individual assets.
    """
    return _post("/world/build", {
        "name": name, "biome": biome, "width": width, "height": height,
        "buildings": buildings, "building_style": building_style,
        "characters": characters, "props": props, "seed": seed,
    })


def list_assets(subdir: str = "") -> Dict[str, Any]:
    """List all generated .vox assets.  Optionally filter by subdir."""
    return _get("/assets", {"subdir": subdir} if subdir else {})


def list_scenes() -> Dict[str, Any]:
    """List all generated scene files."""
    return _get("/scenes")


# ---------------------------------------------------------------------------
# Tool dispatcher — maps function name → Python function
# ---------------------------------------------------------------------------

_TOOL_MAP = {
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

    Parameters
    ----------
    name : str
        Tool function name (e.g. "generate_terrain").
    arguments : str | dict
        JSON string or dict of arguments.

    Returns
    -------
    Any
        The tool's return value (dict from API or error dict).
    """
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    try:
        return fn(**arguments)
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# OpenAI-compatible tool definitions (function-calling JSON schema)
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
                    "biome":     {"type": "string",  "enum": ["grassland","desert","snow","ocean","forest"], "description": "Terrain biome"},
                    "width":     {"type": "integer", "default": 32, "description": "X size in voxels (4–128)"},
                    "height":    {"type": "integer", "default": 32, "description": "Y size in voxels (4–128)"},
                    "max_depth": {"type": "integer", "default": 12, "description": "Max terrain height (2–64)"},
                    "seed":      {"type": "integer", "default": 0,  "description": "RNG seed for deterministic output"},
                    "name":      {"type": "string",  "default": "terrain", "description": "Asset filename (no extension)"},
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
                    "width":  {"type": "integer", "default": 8,   "description": "Building X footprint (4–32)"},
                    "depth":  {"type": "integer", "default": 8,   "description": "Building Y footprint (4–32)"},
                    "floors": {"type": "integer", "default": 3,   "description": "Number of floors (1–20)"},
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
            "description": "Construct a VoxelForge scene file from a list of entity placements and lights.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_name": {"type": "string", "description": "Name for the output scene file"},
                    "entities": {
                        "type": "array",
                        "description": "List of entity placements",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name":     {"type": "string"},
                                "asset":    {"type": "string", "description": "Relative path to .vox file"},
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
                "Build a COMPLETE game world in one call: generates terrain, buildings, "
                "characters, props, and a fully assembled scene file. Use this for full game creation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name":           {"type": "string",  "description": "World name"},
                    "biome":          {"type": "string",  "enum": ["grassland","desert","snow","ocean","forest"]},
                    "width":          {"type": "integer", "default": 64, "description": "World X size (16–256)"},
                    "height":         {"type": "integer", "default": 64, "description": "World Y size (16–256)"},
                    "buildings":      {"type": "integer", "default": 3,  "description": "Number of buildings (0–20)"},
                    "building_style": {"type": "string",  "default": "medieval"},
                    "characters":     {"type": "integer", "default": 2,  "description": "Number of characters (0–20)"},
                    "props":          {"type": "integer", "default": 5,  "description": "Number of random props (0–50)"},
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
            "description": "List all generated .vox asset files. Optionally filter by subdir (terrain/buildings/characters/props).",
            "parameters": {
                "type": "object",
                "properties": {
                    "subdir": {"type": "string", "default": "", "enum": ["","terrain","buildings","characters","props"]},
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
