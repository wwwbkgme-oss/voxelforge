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
        from forge.scene import Scene as VFScene
        scene = VFScene.load(args.file)
        print(f"Scene: {args.file}")
        print(f"  Entities: {scene.entity_count}")
        # Check all VoxelModel assets exist
        missing = []
        for entity in scene._entities:
            vm = entity.get("VoxelModel")
            if vm:
                p = os.path.join(vm.get("modelPath",""), vm.get("modelName",""))
                if p and not os.path.isfile(p):
                    missing.append(p)
        if missing:
            print(f"  MISSING assets ({len(missing)}):")
            for m in missing:
                print(f"    {m}")
        else:
            print("  All assets present ✓")


# ---------------------------------------------------------------------------
# Studio commands (Claude Code Game Studios-inspired)
# ---------------------------------------------------------------------------

def cmd_gdd(args: argparse.Namespace) -> None:
    """Generate a Game Design Document."""
    from forge.studio import GameDesignDoc
    gdd  = GameDesignDoc(
        title        = args.title,
        genre        = args.genre,
        player_class = args.player_class,
        enemies      = args.enemies,
        props        = args.props,
        level_size   = args.level_size,
        seed         = args.seed,
    )
    out = args.output or f"design/gdds/{gdd.slug}.md"
    path = gdd.save(out)
    print(f"GDD written → {path}")
    if args.preview:
        print("\n" + gdd.to_markdown()[:800] + "\n...")


def cmd_brainstorm(args: argparse.Namespace) -> None:
    """Run a creative brainstorming session."""
    from forge.studio import BrainstormSession
    session = BrainstormSession(args.concept, seed=args.seed)
    out     = args.output or f"design/brainstorm_{args.concept[:20].replace(' ','_')}.md"
    path    = session.save(out)
    print(f"Brainstorm saved → {path}")
    if args.preview:
        print("\n" + session.generate()[:600] + "\n...")


def cmd_mda(args: argparse.Namespace) -> None:
    """Analyze a game using the MDA framework."""
    from forge.studio import MDAAnalyzer
    if not os.path.isfile(args.manifest):
        print(f"ERROR: manifest not found: {args.manifest}")
        sys.exit(1)
    analyzer = MDAAnalyzer.from_file(args.manifest)
    text     = analyzer.analyze()
    out      = args.output or "design/mda_analysis.md"
    analyzer.save(out)
    print(f"MDA analysis saved → {out}")
    print(text[:600] + "\n...")


def cmd_adr(args: argparse.Namespace) -> None:
    """Create an Architecture Decision Record."""
    from forge.studio import ADRWriter
    writer = ADRWriter(adr_dir=args.adr_dir)
    path   = writer.create(args.title, context=args.context, decision=args.decision)
    print(f"ADR created → {path}")


def cmd_lore(args: argparse.Namespace) -> None:
    """Generate world lore for a game."""
    from forge.studio import LoreGenerator
    gen  = LoreGenerator(args.world_name, genre=args.genre)
    out  = args.output or f"design/lore_{args.world_name[:20].replace(' ','_')}.md"
    path = gen.save(out)
    print(f"Lore saved → {path}")
    print(gen.generate()[:400] + "\n...")


def cmd_game(args: argparse.Namespace) -> None:
    """Generate a complete mini-game."""
    from forge.voxel import Palette
    from forge.generators.game import GameGenerator
    gen      = GameGenerator(Palette.natural(), seed=args.seed,
                              output_dir=args.output_dir or "generated_assets")
    manifest = gen.generate(
        title        = args.title,
        genre        = args.genre,
        player_class = args.player_class,
        enemies      = args.enemies,
        props        = args.props,
        level_size   = args.level_size,
    )
    print(f"Game generated!")
    print(f"  Scene:    {manifest['scene_path']}")
    print(f"  Assets:   {len(manifest['assets'])}")
    print(f"  Scripts:  {len(manifest['scripts'])}")
    print(f"  Entities: {manifest['entity_count']}")
    print(f"\nRun: {manifest['run_command']}")


def cmd_ai_sprite(args: argparse.Namespace) -> None:
    """Generate AI sprite from text prompt."""
    from forge.imagegen import SpriteGenerator
    gen = SpriteGenerator(output_dir=args.output_dir)
    if args.animated:
        result = gen.generate_animated(
            prompt      = args.prompt,
            name        = args.name,
            frame_count = args.frames,
        )
        print(f"Animated sprite saved:")
        print(f"  Spritesheet : {result.spritesheet}")
        print(f"  GIF         : {result.gif_path}")
        print(f"  Frames      : {result.frame_count}")
        print(f"  Model       : {result.model_used}")
    else:
        result = gen.generate(
            prompt    = args.prompt,
            name      = args.name,
            remove_bg = not args.no_bg,
        )
        print(f"Sprite saved: {result.image_path}")
        print(f"  Size   : {result.width}×{result.height}")
        print(f"  Model  : {result.model_used}")
        print(f"  Source : {result.source}")
        print(f"  Alpha  : {result.has_alpha}")


def cmd_narrative(args: argparse.Namespace) -> None:
    """Interactive LLM narrative game session in the terminal."""
    from forge.narrative import NarrativeEngine
    import readline  # noqa: F401 — enables better terminal input

    engine  = NarrativeEngine(db_path="generated_assets/narrative.db")
    session_id = getattr(args, "session", None)

    if session_id:
        status = engine.get_session_status(session_id)
        if "error" in status:
            print(f"Session not found: {session_id}")
            return
        print(f"Resuming session {session_id[:8]}...")
    else:
        session = engine.start_session(
            player_name = args.player_name,
            genre       = args.genre,
        )
        session_id = session.id
        print(f"\nWelcome, {args.player_name}! Session: {session_id[:8]}")
        print(f"Genre: {args.genre}  |  Type 'quit' to exit\n")

    print("="*60)
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGame ended.")
            break
        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        response = engine.send_message(session_id, user_input)
        print()
        text = response.text()
        if text:
            print(text)
        for block in response.blocks:
            if block.type == "combat":
                print(f"\n⚔️  {block.data.get('result', '')}")
            elif block.type == "item":
                print(f"\n🎒 {block.data.get('action','').title()}: {block.data.get('item','')}")
            elif block.type == "game_over":
                won = block.data.get("won", False)
                msg = block.data.get("message", "")
                print(f"\n{'🏆 YOU WIN!' if won else '💀 GAME OVER'} {msg}")
                return
        choices = response.choices()
        if choices:
            print("\nOptions:")
            for i, c in enumerate(choices, 1):
                print(f"  {i}. {c}")

    status = engine.get_session_status(session_id)
    print(f"\nSession ended. Score: {status.get('score', 0)}  HP: {status.get('hp', 0)}")


def cmd_pipeline(args: argparse.Namespace) -> None:
    """Run the 12-agent game development pipeline."""
    from forge.pipeline import GamePipeline
    competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]
    pipeline    = GamePipeline(output_dir=args.output_dir)
    result      = pipeline.run(
        concept    = args.concept,
        genre      = args.genre,
        mode       = args.mode,
        timeline   = args.timeline,
        competitors= competitors,
        build_game = args.build,
    )
    d = result.to_dict()
    print(f"\nPipeline complete — {result.elapsed_s:.1f}s")
    print(f"  Agents:  {len(d['agents'])}")
    if d.get("market"):
        print(f"  Market:  {d['market']['recommendation']} (score {d['market']['opportunity_score']}/10)")
    if d.get("design"):
        print(f"  GDD:     {d['design']['gdd_path']}")
    if d.get("build"):
        print(f"  Build:   {d['build']['scene_path']}")
        print(f"\nRun: {d['build']['run_command']}")
    print(f"  Project: {result.project_dir}")


def cmd_project(args: argparse.Namespace) -> None:
    """Project lifecycle management."""
    from forge.project import ProjectManager
    pm = ProjectManager("projects")

    if args.proj_action == "init":
        competitors = [c.strip() for c in args.competitors.split(",") if c.strip()]
        proj = pm.init_project(
            name        = args.name,
            concept     = args.concept,
            genre       = args.genre,
            engine      = args.engine,
            mode        = args.mode,
            competitors = competitors,
        )
        print(proj.status_summary())
        m = proj.next_milestone()
        if m:
            print(f"\nNext milestone: {m['name']} — {m['date']}")

    elif args.proj_action == "list":
        projects = pm.list_projects()
        if not projects:
            print("No projects found.")
        for p in projects:
            print(f"  {p['slug']:<30} {p['status']:<10} {p['genre']:<10} {p['engine']}")

    elif args.proj_action == "status":
        proj = pm.load_project(args.slug)
        print(proj.status_summary())
        m = proj.next_milestone()
        if m:
            print(f"\nNext milestone: {m['name']} — {m['date']}")


def cmd_sprite(args: argparse.Namespace) -> None:
    """Render a .vox file to an isometric PNG sprite."""
    try:
        from forge.export.sprite_renderer import render_vox_to_png, render_all_assets
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    if args.input:
        out  = args.output or os.path.splitext(args.input)[0] + "_preview.png"
        path = render_vox_to_png(args.input, out,
                                  tile_w=args.tile_w, tile_h=args.tile_h)
        print(f"Sprite saved → {path}")
    elif args.all:
        assets_dir = os.environ.get("VOXELFORGE_ASSETS_DIR", "generated_assets")
        count = render_all_assets(assets_dir, args.thumbs_dir or "generated_assets/thumbnails")
        print(f"Rendered {count} sprites to {args.thumbs_dir or 'generated_assets/thumbnails'}/")
    else:
        print("ERROR: provide --input <path.vox> or --all")
        sys.exit(1)


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

    # --- game ---
    p_game = sub.add_parser("game", help="Generate a complete mini-game")
    p_game.add_argument("--title",        default="VoxelForge Game")
    p_game.add_argument("--genre",        default="village",
                        choices=["village","dungeon","space","fantasy","horror","arctic"])
    p_game.add_argument("--player-class", dest="player_class", default="warrior",
                        choices=["warrior","mage","archer","rogue"])
    p_game.add_argument("--enemies",      type=int, default=3)
    p_game.add_argument("--props",        type=int, default=6)
    p_game.add_argument("--level-size",   dest="level_size", type=int, default=48)
    p_game.add_argument("--seed",         type=int, default=0)
    p_game.add_argument("--output-dir",   dest="output_dir", default=None)

    # --- gdd ---
    p_gdd = sub.add_parser("gdd", help="Generate a Game Design Document")
    p_gdd.add_argument("title")
    p_gdd.add_argument("--genre",        default="village",
                       choices=["village","dungeon","space","fantasy","horror","arctic"])
    p_gdd.add_argument("--player-class", dest="player_class", default="warrior")
    p_gdd.add_argument("--enemies",      type=int, default=3)
    p_gdd.add_argument("--props",        type=int, default=6)
    p_gdd.add_argument("--level-size",   dest="level_size", type=int, default=48)
    p_gdd.add_argument("--seed",         type=int, default=0)
    p_gdd.add_argument("--output",       default=None)
    p_gdd.add_argument("--preview",      action="store_true")

    # --- brainstorm ---
    p_bs = sub.add_parser("brainstorm", help="Creative brainstorming session")
    p_bs.add_argument("concept", help="Game concept to brainstorm")
    p_bs.add_argument("--seed",    type=int, default=0)
    p_bs.add_argument("--output",  default=None)
    p_bs.add_argument("--preview", action="store_true")

    # --- mda ---
    p_mda = sub.add_parser("mda", help="MDA framework analysis of a game manifest")
    p_mda.add_argument("manifest", help="Path to manifest.json from game generation")
    p_mda.add_argument("--output", default=None)

    # --- adr ---
    p_adr = sub.add_parser("adr", help="Create an Architecture Decision Record")
    p_adr.add_argument("title",      help="ADR title")
    p_adr.add_argument("--context",  default="", help="Context for the decision")
    p_adr.add_argument("--decision", default="", help="The decision made")
    p_adr.add_argument("--adr-dir",  dest="adr_dir", default="design/adrs")

    # --- lore ---
    p_lore = sub.add_parser("lore", help="Generate world lore / narrative")
    p_lore.add_argument("world_name", help="World or game name")
    p_lore.add_argument("--genre",  default="village",
                        choices=["village","dungeon","space","fantasy","horror","arctic"])
    p_lore.add_argument("--output", default=None)

    # --- sprite ---
    p_sprite = sub.add_parser("sprite", help="Render .vox to isometric PNG sprite")
    p_sprite.add_argument("--input",      default=None, help=".vox file to render")
    p_sprite.add_argument("--output",     default=None, help="Output PNG path")
    p_sprite.add_argument("--all",        action="store_true",
                          help="Render all assets in VOXELFORGE_ASSETS_DIR")
    p_sprite.add_argument("--thumbs-dir", dest="thumbs_dir", default=None)
    p_sprite.add_argument("--tile-w",     dest="tile_w", type=int, default=8)
    p_sprite.add_argument("--tile-h",     dest="tile_h", type=int, default=4)

    # --- ai-sprite --- AI-powered sprite generation
    p_aisprite = sub.add_parser("ai-sprite", help="Generate AI sprite from text prompt")
    p_aisprite.add_argument("prompt",      help="Text description of the sprite")
    p_aisprite.add_argument("--name",      default="sprite")
    p_aisprite.add_argument("--output-dir",dest="output_dir", default="generated_assets/sprites")
    p_aisprite.add_argument("--animated",  action="store_true", help="Generate animated spritesheet")
    p_aisprite.add_argument("--frames",    type=int, default=8)
    p_aisprite.add_argument("--no-bg",     dest="no_bg", action="store_true",
                            help="Skip background removal")

    # --- narrative --- Interactive narrative game session
    p_narr = sub.add_parser("narrative", help="Start interactive LLM narrative game")
    p_narr.add_argument("--player",  default="Hero", dest="player_name")
    p_narr.add_argument("--genre",   default="dungeon")
    p_narr.add_argument("--session", default=None, help="Resume existing session ID")

    # --- pipeline --- 12-agent game development pipeline
    p_pipe = sub.add_parser("pipeline", help="Run 12-agent game development pipeline")
    p_pipe.add_argument("concept",   help="One-sentence game concept")
    p_pipe.add_argument("--genre",   default="dungeon")
    p_pipe.add_argument("--mode",    default="design",
                        choices=["design","prototype","development"])
    p_pipe.add_argument("--timeline",default="Short")
    p_pipe.add_argument("--competitors", default="", help="Comma-separated competitor names")
    p_pipe.add_argument("--build",   action="store_true", help="Also build VoxelForge game")
    p_pipe.add_argument("--output-dir", dest="output_dir", default="projects")

    # --- project --- Project lifecycle management
    p_proj = sub.add_parser("project", help="Project lifecycle management")
    proj_sub = p_proj.add_subparsers(dest="proj_action", required=True)

    p_proj_init = proj_sub.add_parser("init", help="Initialize a new project")
    p_proj_init.add_argument("name")
    p_proj_init.add_argument("concept")
    p_proj_init.add_argument("--genre",   default="dungeon")
    p_proj_init.add_argument("--engine",  default="voxelforge",
                             choices=["voxelforge","godot","unity","unreal"])
    p_proj_init.add_argument("--mode",    default="development")
    p_proj_init.add_argument("--competitors", default="")

    proj_sub.add_parser("list", help="List all projects")

    p_proj_status = proj_sub.add_parser("status", help="Show project status")
    p_proj_status.add_argument("slug")

    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    dispatch = {
        "api":        cmd_api,
        "generate":   cmd_generate,
        "world":      cmd_world,
        "agent":      cmd_agent,
        "scene":      cmd_scene,
        "game":       cmd_game,
        "gdd":        cmd_gdd,
        "brainstorm": cmd_brainstorm,
        "mda":        cmd_mda,
        "adr":        cmd_adr,
        "lore":       cmd_lore,
        "sprite":     cmd_sprite,
        "ai-sprite":  cmd_ai_sprite,
        "narrative":  cmd_narrative,
        "pipeline":   cmd_pipeline,
        "project":    cmd_project,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
