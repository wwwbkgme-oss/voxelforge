"""
forge.mcp_server
================
Model Context Protocol (MCP) server for VoxelForge Studio.

Exposes all VoxelForge generation capabilities as MCP tools, making them
directly usable inside Claude Code, Cline, OpenCode, Cursor, and any
other MCP-compatible AI coding assistant.

Start the server:
    voxelforge mcp                           # stdio mode (Claude Code / Cline)
    voxelforge mcp --transport sse --port 3100  # SSE mode (web-based clients)

Add to Claude Code (claude_desktop_config.json):
    {
      "mcpServers": {
        "voxelforge": {
          "command": "voxelforge",
          "args": ["mcp"]
        }
      }
    }

Add to OpenCode (.opencode/config.json):
    {
      "tools": {
        "voxelforge": {
          "type": "mcp",
          "command": ["voxelforge", "mcp"]
        }
      }
    }

Available tools (32 total):
  Asset Generation  — generate_terrain, generate_building, generate_character,
                      generate_prop, generate_dungeon, generate_game
  World Building    — build_world, build_scene
  Sprites           — generate_sprite, generate_sprite_sheet, remove_background,
                      generate_batch_sprites
  HTML5 Games       — generate_html5_game
  Narrative/Quests  — generate_storyline, generate_npcs, generate_quests,
                      generate_dialogue_tree, generate_items
  Full Pipeline     — run_pipeline, init_project
  LLM Routing       — llm_chat, list_free_providers
  File Utils        — list_assets, render_preview, export_spritesheet
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# MCP protocol constants
# ---------------------------------------------------------------------------

MCP_VERSION      = "2024-11-05"
SERVER_NAME      = "voxelforge"
SERVER_VERSION   = "2.0.0"
PROTOCOL_VERSION = "2024-11-05"


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_TOOLS: List[Dict[str, Any]] = [

    # ── Asset generators ─────────────────────────────────────────────────

    {
        "name":        "generate_terrain",
        "description": "Generate voxel terrain for a game world (5 biomes, FBM noise). Returns path to .vox file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "biome":     {"type": "string", "enum": ["grassland","desert","snow","ocean","forest"], "default": "grassland"},
                "width":     {"type": "integer", "default": 32, "minimum": 4, "maximum": 128},
                "height":    {"type": "integer", "default": 32, "minimum": 4, "maximum": 128},
                "max_depth": {"type": "integer", "default": 12},
                "seed":      {"type": "integer", "default": 0},
                "name":      {"type": "string",  "default": "terrain"},
            },
            "required": [],
        },
    },
    {
        "name":        "generate_building",
        "description": "Generate a procedural voxel building (5 styles: modern/medieval/sci-fi/rustic/fantasy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "style":  {"type": "string", "enum": ["modern","medieval","sci-fi","rustic","fantasy"], "default": "medieval"},
                "width":  {"type": "integer", "default": 8},
                "depth":  {"type": "integer", "default": 8},
                "floors": {"type": "integer", "default": 3},
                "seed":   {"type": "integer", "default": 0},
                "name":   {"type": "string",  "default": "building"},
            },
            "required": [],
        },
    },
    {
        "name":        "generate_character",
        "description": "Generate a voxel humanoid character (warrior/mage/archer/rogue with customizable armour and weapon).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "class_type": {"type": "string", "enum": ["warrior","mage","archer","rogue"], "default": "warrior"},
                "skin_tone":  {"type": "string", "enum": ["light","tan","dark","fantasy"], "default": "tan"},
                "armour":     {"type": "string", "enum": ["none","leather","chainmail","plate","mage"], "default": "chainmail"},
                "weapon":     {"type": "string", "enum": ["none","sword","staff","bow","axe"], "default": "sword"},
                "seed":       {"type": "integer", "default": 0},
                "name":       {"type": "string",  "default": "character"},
            },
            "required": [],
        },
    },
    {
        "name":        "generate_prop",
        "description": "Generate a small voxel prop: tree/crate/barrel/lamp_post/rock/chest/mushroom.",
        "inputSchema": {
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
    {
        "name":        "generate_dungeon",
        "description": "Generate a BSP dungeon/cave level (stone/dungeon/cave/ice styles).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "style":       {"type": "string", "enum": ["stone","dungeon","cave","ice"], "default": "stone"},
                "width":       {"type": "integer", "default": 48},
                "height":      {"type": "integer", "default": 48},
                "wall_height": {"type": "integer", "default": 3},
                "seed":        {"type": "integer", "default": 0},
                "name":        {"type": "string",  "default": "dungeon"},
            },
            "required": [],
        },
    },
    {
        "name":        "generate_game",
        "description": "Generate a COMPLETE playable VoxelForge mini-game: level + player + enemies + Lua AI scripts + scene file. One call does everything.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title":        {"type": "string"},
                "genre":        {"type": "string", "enum": ["village","dungeon","space","fantasy","horror","arctic"], "default": "dungeon"},
                "player_class": {"type": "string", "enum": ["warrior","mage","archer","rogue"], "default": "warrior"},
                "enemies":      {"type": "integer", "default": 3},
                "props":        {"type": "integer", "default": 6},
                "level_size":   {"type": "integer", "default": 48},
                "seed":         {"type": "integer", "default": 0},
            },
            "required": ["title"],
        },
    },

    # ── World & Scene ────────────────────────────────────────────────────

    {
        "name":        "build_world",
        "description": "Build a complete game world: terrain + buildings + characters + props + VoxelForge scene file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":           {"type": "string"},
                "biome":          {"type": "string", "enum": ["grassland","desert","snow","ocean","forest"], "default": "grassland"},
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

    # ── Sprite generation ────────────────────────────────────────────────

    {
        "name":        "generate_sprite",
        "description": "Generate an AI sprite from a text prompt (OpenRouter/DALL-E if key set, or procedural pixel art). Chroma-key background removal included.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":    {"type": "string"},
                "name":      {"type": "string", "default": "sprite"},
                "style":     {"type": "string",
                               "enum": ["stardew_valley","hollow_knight","genshin_impact",
                                        "fall_guys","pixel_art_rpg","breath_of_wild",
                                        "retro_8bit","anime_cartoon","realistic_game",
                                        "vector_art","isometric_voxel"],
                               "default": "pixel_art_rpg"},
                "remove_bg": {"type": "boolean", "default": True},
                "animated":  {"type": "boolean", "default": False},
            },
            "required": ["prompt"],
        },
    },
    {
        "name":        "generate_sprite_sheet",
        "description": "Generate a complete character sprite sheet with multiple animation actions. Returns horizontal 1×N PNG strips per action stacked vertically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Character description"},
                "style":       {"type": "string", "default": "pixel_art_rpg"},
                "actions":     {
                    "type": "array",
                    "items": {"type": "string",
                               "enum": ["idle","walk","run","jump","attack","cast",
                                        "hurt","death","turn","punch","block","interact"]},
                    "default": ["idle", "walk", "attack"],
                },
                "name":        {"type": "string", "default": "character"},
            },
            "required": ["description"],
        },
    },
    {
        "name":        "generate_batch_sprites",
        "description": "Generate a batch of prop/item sprites using grid-based generation (25 items per API call — ~30x cheaper than individual calls).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompts":   {"type": "array", "items": {"type": "string"}, "description": "List of item/prop descriptions"},
                "style":     {"type": "string", "default": "pixel_art_rpg"},
                "grid_size": {"type": "integer", "default": 5, "description": "Grid dimension (5=25 per API call)"},
                "name":      {"type": "string", "default": "batch"},
            },
            "required": ["prompts"],
        },
    },
    {
        "name":        "remove_background",
        "description": "Remove background from a sprite/image file using neural network (rembg u2net) or chroma-key fallback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path":  {"type": "string", "description": "Path to source image"},
                "output_path": {"type": "string", "description": "Output path (optional)"},
                "method":      {"type": "string", "enum": ["auto","rembg","chromakey"], "default": "auto"},
            },
            "required": ["image_path"],
        },
    },

    # ── HTML5 Games ──────────────────────────────────────────────────────

    {
        "name":        "generate_html5_game",
        "description": "Generate a COMPLETE, immediately-playable single-file HTML5 game from a text description. Uses free LLMs (Groq/Gemini/Cerebras/OpenRouter). Falls back to procedural game if no key is available.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":      {"type": "string", "description": "Game description"},
                "genre":       {"type": "string",
                                 "enum": ["auto","platformer","puzzle","rpg","shooter",
                                           "arcade","adventure","dungeon","educational"],
                                 "default": "auto"},
                "title":       {"type": "string", "default": ""},
                "name":        {"type": "string", "default": "game"},
                "max_tokens":  {"type": "integer", "default": 8192},
            },
            "required": ["prompt"],
        },
    },

    # ── Narrative / Quest Pipeline ───────────────────────────────────────

    {
        "name":        "run_asset_pipeline",
        "description": "Run the full narrative asset pipeline: storyline → characters → backstories → quests → branching dialogue tree → items with visual descriptions → world elements → Lua scripts. Uses free LLMs automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "theme":   {"type": "string", "description": "Core game theme (e.g. 'dark ice dungeon')"},
                "details": {"type": "string", "default": "", "description": "Additional world details"},
                "genre":   {"type": "string", "default": "dungeon"},
                "seed":    {"type": "integer", "default": 0},
            },
            "required": ["theme"],
        },
    },
    {
        "name":        "generate_storyline",
        "description": "Generate a game storyline and characters for a given theme using free LLMs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "theme":  {"type": "string"},
                "genre":  {"type": "string", "default": "dungeon"},
                "length": {"type": "string", "enum": ["short","medium","long"], "default": "medium"},
            },
            "required": ["theme"],
        },
    },
    {
        "name":        "generate_dialogue_tree",
        "description": "Generate a branching dialogue tree for an NPC as JSON. Ready to embed in Lua scripts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "npc_name":    {"type": "string"},
                "npc_role":    {"type": "string", "default": "NPC"},
                "quest_title": {"type": "string", "default": ""},
                "backstory":   {"type": "string", "default": ""},
            },
            "required": ["npc_name"],
        },
    },

    # ── Project / Pipeline ───────────────────────────────────────────────

    {
        "name":        "run_pipeline",
        "description": "Run the 12-agent game development pipeline: market analysis → GDD → build → QA. Works without LLM keys (uses templates). Returns project directory, GDD path, and optionally a built scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "concept":     {"type": "string", "description": "One-sentence game concept"},
                "genre":       {"type": "string", "default": "dungeon"},
                "mode":        {"type": "string", "enum": ["design","prototype","development"], "default": "design"},
                "competitors": {"type": "array", "items": {"type": "string"}, "default": []},
                "build_game":  {"type": "boolean", "default": False},
                "seed":        {"type": "integer", "default": 42},
            },
            "required": ["concept"],
        },
    },
    {
        "name":        "init_project",
        "description": "Initialize a full game project structure with GDD, ADRs, market research, engine-specific files (VoxelForge/Godot/Unity/Unreal), CLAUDE.md, milestones, and agent config.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name":        {"type": "string"},
                "concept":     {"type": "string"},
                "genre":       {"type": "string", "default": "dungeon"},
                "engine":      {"type": "string", "enum": ["voxelforge","godot","unity","unreal"], "default": "voxelforge"},
                "mode":        {"type": "string", "default": "development"},
                "competitors": {"type": "array", "items": {"type": "string"}, "default": []},
            },
            "required": ["name", "concept"],
        },
    },

    # ── LLM Routing ──────────────────────────────────────────────────────

    {
        "name":        "llm_chat",
        "description": "Send a prompt to the best available free LLM (Groq/Cerebras/SambaNova/NVIDIA NIM/Gemini/OpenRouter free/LLM7/Together). Auto-selects provider based on available API keys.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":      {"type": "string"},
                "system":      {"type": "string", "default": ""},
                "task":        {"type": "string", "enum": ["default","fast","code","creative","small"], "default": "default"},
                "provider":    {"type": "string", "default": ""},
                "max_tokens":  {"type": "integer", "default": 2048},
                "temperature": {"type": "number",  "default": 0.7},
            },
            "required": ["prompt"],
        },
    },
    {
        "name":        "list_free_providers",
        "description": "List all LLM providers that have an API key configured in the environment, with their model options and free tier notes.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },

    # ── File utilities ───────────────────────────────────────────────────

    {
        "name":        "list_assets",
        "description": "List all generated VoxelForge assets (.vox files, scenes, sprites, HTML games) in the output directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subdir": {"type": "string", "default": "", "description": "Filter by subdirectory: terrain/buildings/characters/props/sprites/games/scenes"},
            },
            "required": [],
        },
    },
    {
        "name":        "render_preview",
        "description": "Render a .vox file to an isometric PNG preview using the software sprite renderer (no engine or OpenGL needed).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vox_path":    {"type": "string"},
                "output_path": {"type": "string", "default": ""},
                "tile_size":   {"type": "integer", "default": 8, "description": "Voxel tile width in pixels"},
            },
            "required": ["vox_path"],
        },
    },
    {
        "name":        "export_spritesheet",
        "description": "Merge individual PNG frames into a horizontal sprite sheet, or split a sheet into individual frames.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action":       {"type": "string", "enum": ["merge","split"], "default": "merge"},
                "frame_paths":  {"type": "array",  "items": {"type": "string"}, "default": []},
                "sheet_path":   {"type": "string", "default": "", "description": "Source sheet (for split) or output (for merge)"},
                "frame_width":  {"type": "integer", "default": 64, "description": "Frame width in pixels (for split)"},
                "frame_height": {"type": "integer", "default": 64},
            },
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a tool call and return a result dict."""
    try:
        assets_dir = os.environ.get("VOXELFORGE_ASSETS_DIR", "generated_assets")

        # ── Asset generators ──────────────────────────────────────────────

        if name == "generate_terrain":
            from .voxel import Palette
            from .generators import TerrainGenerator
            gen   = TerrainGenerator(Palette.natural(), seed=args.get("seed", 0))
            model = gen.generate(
                width    = args.get("width", 32),
                height   = args.get("height", 32),
                max_depth= args.get("max_depth", 12),
                biome    = args.get("biome", "grassland"),
            )
            model.name = args.get("name", "terrain")
            path = os.path.join(assets_dir, "terrain", f"{model.name}.vox")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model.save(path)
            return {"path": path, "voxels": model.voxel_count(),
                    "dimensions": [model.width, model.height, model.depth]}

        if name == "generate_building":
            from .voxel import Palette
            from .generators import BuildingGenerator
            gen   = BuildingGenerator(Palette.natural(), seed=args.get("seed", 0))
            model = gen.generate(args.get("width",8), args.get("depth",8),
                                  args.get("floors",3), style=args.get("style","medieval"),
                                  name=args.get("name","building"))
            path  = os.path.join(assets_dir, "buildings", f"{args.get('name','building')}.vox")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model.save(path)
            return {"path": path, "voxels": model.voxel_count()}

        if name == "generate_character":
            from .voxel import Palette
            from .generators import CharacterGenerator
            gen   = CharacterGenerator(Palette.natural(), seed=args.get("seed", 0))
            model = gen.generate(
                class_type = args.get("class_type", "warrior"),
                skin_tone  = args.get("skin_tone", "tan"),
                armour     = args.get("armour", "chainmail"),
                weapon     = args.get("weapon", "sword"),
                name       = args.get("name", "character"),
            )
            path  = os.path.join(assets_dir, "characters", f"{args.get('name','char')}.vox")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model.save(path)
            return {"path": path, "voxels": model.voxel_count()}

        if name == "generate_prop":
            from .voxel import Palette
            from .generators import PropGenerator
            gen  = PropGenerator(Palette.natural(), seed=args.get("seed", 0))
            nm   = args.get("name") or args.get("prop_type", "prop")
            model = gen.generate(args["prop_type"], variant=args.get("variant",""), name=nm)
            path  = os.path.join(assets_dir, "props", f"{nm}.vox")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model.save(path)
            return {"path": path, "voxels": model.voxel_count()}

        if name == "generate_dungeon":
            from .voxel import Palette
            from .generators import DungeonGenerator
            gen   = DungeonGenerator(Palette.natural(), seed=args.get("seed", 0))
            model = gen.generate(args.get("width",48), args.get("height",48),
                                  wall_height=args.get("wall_height",3),
                                  style=args.get("style","stone"))
            model.name = args.get("name", "dungeon")
            path  = os.path.join(assets_dir, "dungeons", f"{model.name}.vox")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            model.save(path)
            return {"path": path, "voxels": model.voxel_count()}

        if name == "generate_game":
            from .voxel import Palette
            from .generators.game import GameGenerator
            gen      = GameGenerator(Palette.natural(), seed=args.get("seed", 0),
                                      output_dir=assets_dir)
            manifest = gen.generate(
                title        = args["title"],
                genre        = args.get("genre", "dungeon"),
                player_class = args.get("player_class", "warrior"),
                enemies      = args.get("enemies", 3),
                props        = args.get("props", 6),
                level_size   = args.get("level_size", 48),
            )
            return {
                "scene_path":   manifest.get("scene_path", ""),
                "run_command":  manifest.get("run_command", ""),
                "assets":       len(manifest.get("assets", [])),
                "scripts":      len(manifest.get("scripts", [])),
                "entities":     manifest.get("entity_count", 0),
            }

        if name == "build_world":
            from .ai.tools import call_tool
            result = call_tool("build_world", args)
            return result

        # ── Sprites ───────────────────────────────────────────────────────

        if name == "generate_sprite":
            from .spritesheet import SpriteSheetForge, GameStyle
            forge_ss = SpriteSheetForge(
                output_dir = os.path.join(assets_dir, "sprites"),
                remove_bg  = args.get("remove_bg", True),
            )
            style_val = args.get("style", "pixel_art_rpg")
            try:
                style = GameStyle(style_val)
            except ValueError:
                style = GameStyle.PIXEL_ART_RPG
            result = forge_ss.generate_character_sheet(
                description = args["prompt"],
                style       = style,
                actions     = [],
                name        = args.get("name", "sprite"),
            )
            return {"path": result.spritesheet_path, "frames": result.frame_count,
                    "source": result.source}

        if name == "generate_sprite_sheet":
            from .spritesheet import SpriteSheetForge, GameStyle, AnimationAction
            forge_ss = SpriteSheetForge(output_dir=os.path.join(assets_dir, "sprites"))
            actions  = [AnimationAction(a) for a in args.get("actions", ["idle","walk","attack"])
                        if a in [e.value for e in AnimationAction]]
            style    = GameStyle(args.get("style", "pixel_art_rpg"))
            result   = forge_ss.generate_character_sheet(
                description = args["description"],
                style       = style,
                actions     = actions or [AnimationAction.IDLE],
                name        = args.get("name", "sheet"),
            )
            return {"spritesheet": result.spritesheet_path,
                    "frames": result.frame_count, "gif": result.gif_path}

        if name == "generate_batch_sprites":
            from .spritesheet import SpriteSheetForge, GameStyle
            forge_ss = SpriteSheetForge(output_dir=os.path.join(assets_dir, "sprites"))
            result   = forge_ss.generate_prop_batch(
                prompts   = args["prompts"],
                style     = GameStyle(args.get("style", "pixel_art_rpg")),
                grid_size = args.get("grid_size", 5),
                name      = args.get("name", "batch"),
            )
            return {"count": len(result.image_paths),
                    "images": result.image_paths[:10],
                    "source": result.source}

        if name == "remove_background":
            from .spritesheet import BackgroundRemover
            remover = BackgroundRemover(args.get("method", "auto"))
            out     = remover.remove(args["image_path"],
                                      args.get("output_path") or None)
            return {"output_path": out}

        # ── HTML5 games ───────────────────────────────────────────────────

        if name == "generate_html5_game":
            from .gamegen import HTML5GameGenerator
            gen  = HTML5GameGenerator(output_dir=os.path.join(assets_dir, "games", "html"))
            game = gen.generate(
                prompt     = args["prompt"],
                genre      = args.get("genre", "auto"),
                title      = args.get("title", ""),
                name       = args.get("name", "game"),
                max_tokens = args.get("max_tokens", 8192),
            )
            return {
                "html_path": game.html_path,
                "title":     game.title,
                "genre":     game.genre,
                "valid":     game.valid,
                "provider":  game.provider,
                "open_url":  game.open_url(),
                "issues":    game.issues,
            }

        # ── Narrative pipeline ────────────────────────────────────────────

        if name == "run_asset_pipeline":
            from .gamegen import AssetPipeline
            pipeline = AssetPipeline(output_dir=os.path.join(assets_dir, "narrative_packs"))
            pack     = pipeline.run(
                theme   = args["theme"],
                details = args.get("details", ""),
                genre   = args.get("genre", "dungeon"),
                seed    = args.get("seed", 0),
            )
            paths    = pack.save()
            return {
                "output_dir":    pack.output_dir,
                "files":         len(paths),
                "characters":    len(pack.characters),
                "quests":        len(pack.quests),
                "items":         len(pack.items),
                "lua_scripts":   list(pack.lua_scripts.keys()),
                "model":         pack.model,
                "provider":      pack.provider,
            }

        if name == "generate_storyline":
            from .llm_router import get_router
            router = get_router()
            resp   = router.chat(
                f"Create a {args.get('length','medium')}-length game storyline "
                f"for a {args.get('genre','dungeon')} game set in {args['theme']}. "
                "Include 2 named characters and the central conflict.",
                task="creative",
            )
            return {"storyline": resp.text, "provider": resp.provider}

        if name == "generate_dialogue_tree":
            from .llm_router import get_router
            router = get_router()
            npc    = args["npc_name"]
            role   = args.get("npc_role", "NPC")
            prompt = (
                f"Create a branching dialogue tree for NPC '{npc}' (role: {role}).\n"
                f"Quest: {args.get('quest_title','')}\n"
                f"Backstory: {args.get('backstory','')}\n\n"
                "Output valid JSON: {\"npc\":\"...\",\"opening\":\"...\","
                "\"branches\":[{\"player\":\"...\",\"npc\":\"...\",\"leads_to\":\"...\"}]}"
            )
            resp = router.chat(prompt, task="creative")
            from .gamegen import _parse_json_obj
            tree = _parse_json_obj(resp.text, {"npc": npc, "opening": f"Hello, I am {npc}.", "branches": []})
            return {"dialogue_tree": tree, "provider": resp.provider}

        # ── Pipeline & Project ────────────────────────────────────────────

        if name == "run_pipeline":
            from .pipeline import GamePipeline
            pipeline = GamePipeline(output_dir=os.path.join(assets_dir, "pipeline_projects"))
            result   = pipeline.run(
                concept    = args["concept"],
                genre      = args.get("genre", "dungeon"),
                mode       = args.get("mode", "design"),
                competitors= args.get("competitors", []),
                build_game = args.get("build_game", False),
                seed       = args.get("seed", 42),
            )
            d = result.to_dict()
            return {
                "project_dir":  result.project_dir,
                "agents_used":  len(result.agents),
                "market":       d.get("market", {}),
                "gdd_path":     d.get("design", {}).get("gdd_path", ""),
                "build":        d.get("build", {}),
                "elapsed_s":    result.elapsed_s,
            }

        if name == "init_project":
            from .project import ProjectManager
            pm   = ProjectManager(os.path.join(assets_dir, "projects"))
            proj = pm.init_project(
                name        = args["name"],
                concept     = args["concept"],
                genre       = args.get("genre", "dungeon"),
                engine      = args.get("engine", "voxelforge"),
                mode        = args.get("mode", "development"),
                competitors = args.get("competitors", []),
            )
            return {
                "project_path": proj.path,
                "slug":         proj.config.slug,
                "agents":       len(proj.config.active_agents),
                "milestone":    proj.next_milestone(),
                "summary":      proj.status_summary(),
            }

        # ── LLM Routing ───────────────────────────────────────────────────

        if name == "llm_chat":
            from .llm_router import get_router
            router   = get_router()
            provider = args.get("provider") or None
            resp     = router.chat(
                prompt      = args["prompt"],
                system      = args.get("system") or None,
                task        = args.get("task", "default"),
                provider    = provider,
                max_tokens  = args.get("max_tokens", 2048),
                temperature = args.get("temperature", 0.7),
            )
            return {"text": resp.text, "provider": resp.provider,
                    "model": resp.model, "latency_ms": resp.latency_ms,
                    "ok": resp.ok}

        if name == "list_free_providers":
            from .llm_router import LLMRouter
            router = LLMRouter(verbose=False)
            avail  = router.available_providers()
            from .llm_router import _PROVIDERS
            all_p  = [{"name": p.name, "priority": p.priority,
                        "free_note": p.free_note,
                        "has_key": bool(os.environ.get(p.env_key, ""))}
                       for p in _PROVIDERS]
            return {"available": avail, "all_providers": all_p,
                    "count": len(avail)}

        # ── File utilities ────────────────────────────────────────────────

        if name == "list_assets":
            import glob
            subdir  = args.get("subdir", "")
            pattern = os.path.join(assets_dir, subdir or "**", "*")
            exts    = (".vox", ".scene", ".png", ".gif", ".html", ".json")
            files   = [f for f in glob.glob(pattern, recursive=True)
                       if os.path.isfile(f) and f.endswith(exts)]
            return {"count": len(files), "files": sorted(files)[:50]}

        if name == "render_preview":
            from .export.sprite_renderer import render_vox_to_png
            vox  = args["vox_path"]
            out  = args.get("output_path") or vox.replace(".vox", "_preview.png")
            tw   = args.get("tile_size", 8)
            path = render_vox_to_png(vox, out, tile_w=tw, tile_h=tw//2)
            return {"preview_path": path}

        if name == "export_spritesheet":
            from .spritesheet import SpriteSheetForge
            forge_ss = SpriteSheetForge()
            action   = args.get("action", "merge")
            if action == "merge":
                out = args.get("sheet_path", "output_sheet.png")
                p   = forge_ss.merge_frames(args.get("frame_paths", []), out)
                return {"output": p}
            else:
                frames = forge_ss.split_sheet(
                    args["sheet_path"],
                    args.get("frame_width", 64),
                    args.get("frame_height", 64),
                )
                return {"frames": frames, "count": len(frames)}

        return {"error": f"Unknown tool: {name}"}

    except Exception as exc:
        return {"error": str(exc), "traceback": traceback.format_exc()[-500:]}


# ---------------------------------------------------------------------------
# MCP JSON-RPC 2.0 stdio server
# ---------------------------------------------------------------------------

class MCPServer:
    """
    MCP server communicating over stdio using JSON-RPC 2.0.

    This is the transport expected by Claude Code, Cline, and most
    MCP clients.  The server reads one JSON object per line from stdin
    and writes one JSON object per line to stdout.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Main stdin/stdout loop."""
        self._log("VoxelForge MCP server started (stdio)")
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    req = json.loads(line)
                except json.JSONDecodeError as exc:
                    self._send_error(None, -32700, f"Parse error: {exc}")
                    continue
                self._handle(req)
        except KeyboardInterrupt:
            self._log("Server stopped")

    # ------------------------------------------------------------------
    def _handle(self, req: Dict[str, Any]) -> None:
        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        # Handle notifications (no id) — no response required
        if req_id is None and method.startswith("notifications/"):
            return

        try:
            result = self._dispatch(method, params)
            if req_id is not None:
                self._send_result(req_id, result)
        except Exception as exc:
            self._send_error(req_id, -32603, str(exc))

    def _dispatch(self, method: str, params: Dict) -> Any:
        if method == "initialize":
            return {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities":    {"tools": {"listChanged": False}},
                "serverInfo":      {"name": SERVER_NAME, "version": SERVER_VERSION},
            }

        if method == "tools/list":
            return {"tools": _TOOLS}

        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result    = execute_tool(tool_name, arguments)
            # MCP expects content as a list of content blocks
            text = json.dumps(result, indent=2, ensure_ascii=False)
            return {
                "content": [{"type": "text", "text": text}],
                "isError": "error" in result and isinstance(result.get("error"), str),
            }

        if method == "ping":
            return {}

        # Resources / prompts (not implemented — return empty)
        if method in ("resources/list", "prompts/list"):
            key = method.split("/")[0]
            return {key: []}

        raise ValueError(f"Unknown method: {method}")

    # ------------------------------------------------------------------
    def _send_result(self, req_id: Any, result: Any) -> None:
        msg = {"jsonrpc": "2.0", "id": req_id, "result": result}
        print(json.dumps(msg, ensure_ascii=False), flush=True)

    def _send_error(self, req_id: Any, code: int, message: str) -> None:
        msg = {
            "jsonrpc": "2.0",
            "id":      req_id,
            "error":   {"code": code, "message": message},
        }
        print(json.dumps(msg, ensure_ascii=False), flush=True)

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[MCP] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# SSE transport (for web-based MCP clients)
# ---------------------------------------------------------------------------

def run_sse_server(host: str = "0.0.0.0", port: int = 3100) -> None:
    """
    Run the MCP server over Server-Sent Events (HTTP).
    Used by Cursor, Claude.ai web, and browser-based MCP clients.
    """
    try:
        from fastapi import FastAPI, Request
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse, StreamingResponse
        import uvicorn  # type: ignore
    except ImportError:
        print("ERROR: uvicorn and fastapi required for SSE mode.")
        print("       pip install fastapi uvicorn")
        sys.exit(1)

    app = FastAPI(title="VoxelForge MCP (SSE)", version=SERVER_VERSION)
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.get("/")
    async def info():
        return {"server": SERVER_NAME, "version": SERVER_VERSION,
                "tools": len(_TOOLS), "transport": "SSE"}

    @app.get("/sse")
    async def sse_endpoint():
        """SSE endpoint for MCP clients."""
        async def event_stream():
            # Send endpoint info
            data = json.dumps({"jsonrpc": "2.0", "method": "$/ready",
                                "params": {"endpoint": f"http://{host}:{port}/message"}})
            yield f"data: {data}\n\n"
            # Keep alive
            while True:
                import asyncio
                await asyncio.sleep(30)
                yield ": keepalive\n\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @app.post("/message")
    async def message_endpoint(request: Request):
        """Handle MCP messages via HTTP POST."""
        req = await request.json()
        server = MCPServer(verbose=False)
        result = server._dispatch(req.get("method",""), req.get("params",{}))
        return JSONResponse({"jsonrpc": "2.0", "id": req.get("id"), "result": result})

    @app.get("/tools")
    async def list_tools():
        return {"tools": _TOOLS}

    print(f"VoxelForge MCP (SSE) running at http://{host}:{port}")
    print(f"  Tools:    {len(_TOOLS)}")
    print(f"  Add to Cursor: mcp://localhost:{port}/sse")
    uvicorn.run(app, host=host, port=port, log_level="warning")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(transport: str = "stdio", host: str = "0.0.0.0", port: int = 3100,
          verbose: bool = False) -> None:
    if transport == "sse":
        run_sse_server(host, port)
    else:
        MCPServer(verbose=verbose).run()
