#!/usr/bin/env python3
"""
VoxelForge CLI
==============
Command-line interface for the VoxelForge AI voxel world builder.

Commands
--------
    voxelforge api          Start the REST API server
    voxelforge generate     Generate assets (terrain/building/character/prop)
    voxelforge world        Build a complete world from a text prompt
    voxelforge agent        Run the autonomous AI agent with a prompt
    voxelforge scene        Scene utilities (list, validate)
"""

from __future__ import annotations

import argparse
import json
import os
import sys


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_api(args: argparse.Namespace) -> None:
    """Start the FastAPI REST server."""
    try:
        import uvicorn  # type: ignore
    except ImportError:
        print("ERROR: uvicorn not installed.  Run: pip install uvicorn")
        sys.exit(1)

    if args.assets_dir:
        os.environ["VOXELFORGE_ASSETS_DIR"] = args.assets_dir

    print(f"Starting VoxelForge API on http://{args.host}:{args.port}")
    print(f"  Assets dir : {os.environ.get('VOXELFORGE_ASSETS_DIR', 'generated_assets')}")
    print(f"  Docs       : http://{args.host}:{args.port}/docs")
    uvicorn.run(
        "forge.api.server:app",
        host   = args.host,
        port   = args.port,
        reload = args.reload,
        log_level = "info",
    )


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate a single asset directly (no API server needed)."""
    from forge.voxel import Palette
    from forge.generators import (
        TerrainGenerator, BuildingGenerator, CharacterGenerator, PropGenerator
    )

    pal = Palette.natural()
    out = args.output or f"{args.type}_{args.name}.vox"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    if args.type == "terrain":
        gen   = TerrainGenerator(pal, seed=args.seed)
        model = gen.generate(
            width=args.width, height=args.height,
            max_depth=args.depth, biome=args.biome,
        )
    elif args.type == "building":
        gen   = BuildingGenerator(pal, seed=args.seed)
        model = gen.generate(
            width=args.width, depth=args.height,
            floors=args.floors, style=args.style, name=args.name,
        )
    elif args.type == "character":
        gen   = CharacterGenerator(pal, seed=args.seed)
        model = gen.generate(
            class_type=args.class_type, skin_tone=args.skin,
            armour=args.armour, weapon=args.weapon, name=args.name,
        )
    elif args.type == "prop":
        gen   = PropGenerator(pal, seed=args.seed)
        model = gen.generate(args.prop_type, name=args.name)
    else:
        print(f"Unknown asset type: {args.type}")
        sys.exit(1)

    model.save(out)
    print(f"Saved: {out}  ({model.voxel_count()} voxels, {model.width}×{model.height}×{model.depth})")


def cmd_world(args: argparse.Namespace) -> None:
    """Build a complete world using the API server."""
    import requests

    api_url = os.environ.get("VOXELFORGE_API_URL", f"http://localhost:{args.port}")
    body = {
        "name":           args.name,
        "biome":          args.biome,
        "width":          args.width,
        "height":         args.height,
        "buildings":      args.buildings,
        "building_style": args.style,
        "characters":     args.characters,
        "props":          args.props,
        "seed":           args.seed,
    }
    try:
        resp = requests.post(f"{api_url}/world/build", json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to API at {api_url}")
        print("Start the server first with:  voxelforge api")
        sys.exit(1)

    print(json.dumps(data, indent=2))


def cmd_agent(args: argparse.Namespace) -> None:
    """Run the autonomous AI agent."""
    from forge.ai.agent import VoxelForgeAgent

    if args.api_url:
        os.environ["VOXELFORGE_API_URL"] = args.api_url

    agent  = VoxelForgeAgent(
        model       = args.model,
        direct_mode = args.direct,
        verbose     = True,
    )
    result = agent.run(args.prompt)
    print("\n--- Result ---")
    print(json.dumps({k: v for k, v in result.items() if k != "tool_results"}, indent=2))
    if result.get("scene_path"):
        print(f"\nRun your world:\n  cd engine && ./voxelforge --scene ../{result['scene_path']}")


def cmd_scene(args: argparse.Namespace) -> None:
    """Scene utilities."""
    from forge.scene import Scene
    import glob

    if args.action == "list":
        assets_dir = os.environ.get("VOXELFORGE_ASSETS_DIR", "generated_assets")
        files = glob.glob(os.path.join(assets_dir, "scenes", "*.scene"))
        if not files:
            print("No scenes found.")
        for f in sorted(files):
            print(f"  {f}")

    elif args.action == "validate":
        if not args.file:
            print("ERROR: --file required for validate")
            sys.exit(1)
        scene = Scene.load(args.file)
        print(f"Scene: {args.file}")
        print(f"  Entities: {len(scene.entities)}")
        missing = []
        for eid, ent in scene.entities.items():
            if ent.voxel_model:
                p = os.path.join(
                    ent.voxel_model.model_path,
                    ent.voxel_model.model_name,
                )
                if not os.path.isfile(p):
                    missing.append(p)
        if missing:
            print(f"  MISSING assets ({len(missing)}):")
            for m in missing:
                print(f"    {m}")
        else:
            print("  All assets present ✓")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog        = "voxelforge",
        description = "VoxelForge — AI-Powered Voxel World Builder",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- api ---
    p_api = sub.add_parser("api", help="Start the REST API server")
    p_api.add_argument("--host",       default="0.0.0.0")
    p_api.add_argument("--port",       type=int, default=8080)
    p_api.add_argument("--reload",     action="store_true")
    p_api.add_argument("--assets-dir", default=None)

    # --- generate ---
    p_gen = sub.add_parser("generate", help="Generate a single asset")
    p_gen.add_argument("type", choices=["terrain","building","character","prop"])
    p_gen.add_argument("--name",       default="asset")
    p_gen.add_argument("--output",     default=None, help="Output .vox path")
    p_gen.add_argument("--seed",       type=int, default=0)
    p_gen.add_argument("--width",      type=int, default=32)
    p_gen.add_argument("--height",     type=int, default=32)
    p_gen.add_argument("--depth",      type=int, default=12)
    p_gen.add_argument("--biome",      default="grassland")
    p_gen.add_argument("--style",      default="modern")
    p_gen.add_argument("--floors",     type=int, default=3)
    p_gen.add_argument("--class-type", dest="class_type", default="warrior")
    p_gen.add_argument("--skin",       default="tan")
    p_gen.add_argument("--armour",     default="chainmail")
    p_gen.add_argument("--weapon",     default="sword")
    p_gen.add_argument("--prop-type",  dest="prop_type", default="tree")

    # --- world ---
    p_world = sub.add_parser("world", help="Build a complete world (requires running API)")
    p_world.add_argument("--name",      default="world")
    p_world.add_argument("--biome",     default="grassland")
    p_world.add_argument("--width",     type=int, default=64)
    p_world.add_argument("--height",    type=int, default=64)
    p_world.add_argument("--buildings", type=int, default=3)
    p_world.add_argument("--style",     default="medieval")
    p_world.add_argument("--characters",type=int, default=2)
    p_world.add_argument("--props",     type=int, default=5)
    p_world.add_argument("--seed",      type=int, default=0)
    p_world.add_argument("--port",      type=int, default=8080)

    # --- agent ---
    p_agent = sub.add_parser("agent", help="Run the autonomous AI agent")
    p_agent.add_argument("prompt", help="Natural language world description")
    p_agent.add_argument("--model",    default="gpt-4o")
    p_agent.add_argument("--direct",   action="store_true",
                         help="Use keyword parser instead of LLM (no API key needed)")
    p_agent.add_argument("--api-url",  default=None, help="VoxelForge API URL")

    # --- scene ---
    p_scene = sub.add_parser("scene", help="Scene utilities")
    p_scene.add_argument("action", choices=["list", "validate"])
    p_scene.add_argument("--file", default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    dispatch = {
        "api":      cmd_api,
        "generate": cmd_generate,
        "world":    cmd_world,
        "agent":    cmd_agent,
        "scene":    cmd_scene,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
