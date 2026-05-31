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


def cmd_model(args: argparse.Namespace) -> None:
    """GGUF model management (download/list/remove/info/recommend)."""
    from forge.local_llm import ModelManager, MODEL_CATALOG

    mgr = ModelManager()

    if args.model_action == "list":
        downloaded = mgr.list_downloaded()
        print(f"Downloaded models ({len(downloaded)}/{len(MODEL_CATALOG)}):")
        if not downloaded:
            print("  None yet. Run: voxelforge model download llama3.2-3b")
        for m in downloaded:
            print(f"  ✓ {m['id']:<22} {m['size_gb']:.1f} GB  {m['path']}")
        print(f"\nAll available models ({len(MODEL_CATALOG)}):")
        for spec in MODEL_CATALOG.values():
            tag  = "✓" if mgr.is_downloaded(spec.id) else " "
            mark = "★" if "recommended" in spec.tags else " "
            print(f" {tag}{mark} {spec.id:<22} ~{spec.size_gb:.1f}GB  {spec.description[:55]}")

    elif args.model_action == "download":
        if not args.model_id:
            print("ERROR: provide a model ID. Run: voxelforge model list")
            sys.exit(1)
        try:
            path = mgr.download(args.model_id, force=getattr(args,'force',False))
            print(f"\nDownloaded: {path}")
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    elif args.model_action == "remove":
        ok = mgr.remove(args.model_id)
        if not ok:
            print(f"Model not found: {args.model_id}")

    elif args.model_action == "info":
        import json
        info = mgr.info(args.model_id)
        print(json.dumps(info, indent=2))

    elif args.model_action == "recommend":
        recs = mgr.recommend_for_hardware()
        print("Models recommended for your hardware:")
        for mid in recs[:6]:
            info = mgr.info(mid)
            mark = "✓" if info.get("downloaded") else " "
            print(f"  {mark} {mid:<22} ~{info['size_gb']:.1f}GB  {info['description'][:50]}")


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the local llama.cpp inference server."""
    from forge.local_llm import (
        InferenceServer, ModelManager,
        detect_gpu_backend, detect_optimal_threads, detect_optimal_gpu_layers,
    )
    mgr   = ModelManager()
    model = args.model

    if not model:
        # Auto-select: recommended + downloaded
        recs = mgr.recommend_for_hardware()
        for mid in recs:
            if mgr.is_downloaded(mid):
                model = mid
                print(f"[serve] Auto-selected model: {model}")
                break
        if not model:
            recs_str = ", ".join(recs[:3])
            print(f"No model downloaded. Download one first:\n  voxelforge model download {recs[:1][0] if recs else 'llama3.2-3b'}")
            sys.exit(1)

    gpu_layers = getattr(args, 'gpu_layers', 0)
    if gpu_layers == -1:
        gpu_layers = detect_optimal_gpu_layers(model)
        print(f"[serve] Auto-detected GPU layers: {gpu_layers}")

    threads = getattr(args, 'threads', 0) or detect_optimal_threads()
    port    = getattr(args, 'port', 8090)
    ctx     = getattr(args, 'ctx', 4096)

    backend = detect_gpu_backend()
    print(f"[serve] GPU backend: {backend}")
    print(f"[serve] Threads: {threads}  Port: {port}  Ctx: {ctx}")

    srv = InferenceServer(
        manager      = mgr,
        port         = port,
        n_gpu_layers = gpu_layers,
        context_size = ctx,
        threads      = threads,
    )
    ok = srv.start(model, wait_secs=90)
    if not ok:
        print("Failed to start inference server.")
        print("Is llama-server installed? Run: voxelforge inference install")
        sys.exit(1)

    print(f"\nInference server running at http://localhost:{port}")
    print(f"  OpenAI-compatible API: http://localhost:{port}/v1")
    print(f"  Use with VoxelForge: LLM_PROVIDER=local LLM_API_BASE=http://localhost:{port}/v1")
    print("\nPress Ctrl+C to stop")
    try:
        while srv.running:
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping inference server...")
        srv.stop()


def cmd_inference(args: argparse.Namespace) -> None:
    """Install llama.cpp for local inference."""
    if args.inf_action == "install":
        from forge.local_llm import install_llama_cpp
        enable_cuda  = not getattr(args, 'no_cuda', False)
        enable_metal = not getattr(args, 'no_metal', False)
        ok = install_llama_cpp(enable_cuda=enable_cuda, enable_metal=enable_metal)
        if ok:
            print("llama.cpp installed successfully.")
            print("Now download a model: voxelforge model download llama3.2-3b")
        else:
            print("Installation failed. Please build llama.cpp manually.")
            sys.exit(1)

    elif args.inf_action == "status":
        from forge.local_llm import find_llama_server, detect_gpu_backend
        binary  = find_llama_server()
        backend = detect_gpu_backend()
        print(f"llama-server : {binary or 'not installed'}")
        print(f"GPU backend  : {backend}")
        if not binary:
            print("\nInstall with: voxelforge inference install")


def cmd_mcp(args: argparse.Namespace) -> None:
    """Start the VoxelForge MCP server for Claude Code / OpenCode / Cline."""
    from forge.mcp_server import main as mcp_main
    transport = getattr(args, "transport", "stdio")
    host      = getattr(args, "host", "0.0.0.0")
    port      = getattr(args, "port", 3100)
    verbose   = getattr(args, "verbose", False)
    if transport == "sse":
        print(f"VoxelForge MCP server (SSE) → http://{host}:{port}")
        print(f"  Tools: 32  |  Add to Cursor: mcp://localhost:{port}/sse")
    else:
        print("VoxelForge MCP server (stdio) — ready for Claude Code / Cline", file=sys.stderr)
    mcp_main(transport=transport, host=host, port=port, verbose=verbose)


def cmd_llm(args: argparse.Namespace) -> None:
    """Send a prompt to the best available free LLM provider."""
    from forge.llm_router import LLMRouter, get_router
    if getattr(args, "providers", False):
        router = LLMRouter(verbose=True)
        avail  = router.available_providers()
        from forge.llm_router import _PROVIDERS
        print(f"Available providers ({len(avail)}/{len(_PROVIDERS)}):")
        for p in _PROVIDERS:
            key   = bool(os.environ.get(p.env_key, ""))
            mark  = "✓" if key else "✗"
            print(f"  {mark} {p.name:<14} {p.free_note}")
        return

    if not args.prompt:
        print("ERROR: provide a --prompt or use --providers to list providers")
        sys.exit(1)

    router = get_router(verbose=args.verbose)
    resp   = router.chat(
        prompt      = args.prompt,
        system      = args.system or None,
        task        = args.task,
        provider    = args.provider or None,
        max_tokens  = args.max_tokens,
        temperature = args.temperature,
    )
    if resp.ok:
        print(resp.text)
        if args.verbose:
            print(f"\n[{resp.provider} / {resp.model} — {resp.latency_ms}ms]", file=sys.stderr)
    else:
        print(f"ERROR: {resp.error}", file=sys.stderr)
        sys.exit(1)


def cmd_html_game(args: argparse.Namespace) -> None:
    """Generate a complete HTML5 game from a text prompt."""
    from forge.gamegen import HTML5GameGenerator
    gen  = HTML5GameGenerator(output_dir=getattr(args, "output_dir", "generated_assets/games/html"))
    game = gen.generate(
        prompt    = args.prompt,
        genre     = getattr(args, "genre", "auto"),
        title     = getattr(args, "title", ""),
        name      = getattr(args, "name", "game"),
    )
    print(f"HTML5 game: {game.html_path}")
    print(f"  Title  : {game.title}")
    print(f"  Genre  : {game.genre}")
    print(f"  Valid  : {game.valid}")
    print(f"  Source : {game.provider}")
    print(f"  URL    : {game.open_url()}")
    if game.issues:
        print(f"  Issues : {', '.join(game.issues)}")


def cmd_sprite_sheet(args: argparse.Namespace) -> None:
    """Generate a character sprite sheet with animation frames."""
    from forge.spritesheet import SpriteSheetForge, GameStyle, AnimationAction
    forge_ss = SpriteSheetForge(
        output_dir = getattr(args, "output_dir", "generated_assets/sprites"),
        remove_bg  = not getattr(args, "no_bg", False),
    )
    style_str = getattr(args, "style", "pixel_art_rpg")
    try:
        style = GameStyle(style_str)
    except ValueError:
        style = GameStyle.PIXEL_ART_RPG

    actions_str = getattr(args, "actions", "idle,walk,attack").split(",")
    valid       = {e.value for e in AnimationAction}
    actions     = [AnimationAction(a.strip()) for a in actions_str if a.strip() in valid]

    result = forge_ss.generate_character_sheet(
        description = args.description,
        style       = style,
        actions     = actions or [AnimationAction.IDLE],
        name        = getattr(args, "name", "character"),
    )
    print(f"Sprite sheet: {result.spritesheet_path}")
    print(f"  Frames : {result.frame_count}")
    print(f"  Alpha  : {result.has_alpha}")
    print(f"  Source : {result.source}")
    if result.gif_path:
        print(f"  GIF    : {result.gif_path}")


def cmd_asset_pipeline(args: argparse.Namespace) -> None:
    """Run the full narrative asset pipeline (storyline → quests → dialogue → items)."""
    from forge.gamegen import AssetPipeline
    pipeline = AssetPipeline(output_dir=getattr(args, "output_dir", "generated_assets/narrative_packs"))
    pack     = pipeline.run(
        theme   = args.theme,
        details = getattr(args, "details", ""),
        genre   = getattr(args, "genre", "dungeon"),
    )
    paths    = pack.save()
    print(f"Asset pack: {pack.output_dir}")
    print(f"  Files      : {len(paths)}")
    print(f"  Characters : {len(pack.characters)}")
    print(f"  Quests     : {len(pack.quests)}")
    print(f"  Items      : {len(pack.items)}")
    print(f"  Lua scripts: {list(pack.lua_scripts.keys())}")
    print(f"  Provider   : {pack.provider}")
    for name, path in paths.items():
        print(f"    {name}: {path}")


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

    # --- model --- GGUF model management
    p_model = sub.add_parser("model", help="Manage local GGUF models")
    model_sub = p_model.add_subparsers(dest="model_action", required=True)

    model_sub.add_parser("list",     help="List downloaded + available models")
    model_sub.add_parser("recommend",help="Show models suited to this machine")

    p_dl = model_sub.add_parser("download", help="Download a GGUF model from HuggingFace")
    p_dl.add_argument("model_id", help="Catalog ID (e.g. llama3.2-3b) or owner/repo:file.gguf")
    p_dl.add_argument("--force", action="store_true", help="Re-download even if present")
    p_dl.add_argument("--url",  dest="custom_url", default="", help="Custom download URL")

    p_rm = model_sub.add_parser("remove",   help="Delete a downloaded model")
    p_rm.add_argument("model_id")

    p_info = model_sub.add_parser("info",   help="Show detailed model info")
    p_info.add_argument("model_id")

    # --- serve --- start local inference server
    p_serve = sub.add_parser("serve", help="Start llama.cpp local inference server")
    p_serve.add_argument("--model",      default="", help="Model ID to load (auto-selects if omitted)")
    p_serve.add_argument("--port",       type=int, default=8090)
    p_serve.add_argument("--gpu-layers", dest="gpu_layers", type=int, default=0,
                          help="-1=full GPU, 0=CPU only, N=partial")
    p_serve.add_argument("--threads",    type=int, default=0, help="CPU threads (0=auto)")
    p_serve.add_argument("--ctx",        type=int, default=4096, help="Context size")

    # --- inference --- manage llama.cpp installation
    p_inf = sub.add_parser("inference", help="Install and check llama.cpp inference")
    inf_sub = p_inf.add_subparsers(dest="inf_action", required=True)

    p_inst = inf_sub.add_parser("install", help="Build llama.cpp from source")
    p_inst.add_argument("--no-cuda",  dest="no_cuda",  action="store_true")
    p_inst.add_argument("--no-metal", dest="no_metal", action="store_true")

    inf_sub.add_parser("status", help="Check if llama-server is installed")

    # --- mcp ---
    p_mcp = sub.add_parser("mcp", help="Start MCP server for Claude Code / OpenCode / Cline")
    p_mcp.add_argument("--transport", default="stdio", choices=["stdio","sse"])
    p_mcp.add_argument("--host",    default="0.0.0.0")
    p_mcp.add_argument("--port",    type=int, default=3100)
    p_mcp.add_argument("--verbose", action="store_true")

    # --- llm ---
    p_llm = sub.add_parser("llm", help="Chat with the best available free LLM provider")
    p_llm.add_argument("prompt",       nargs="?", default="", help="Prompt to send")
    p_llm.add_argument("--system",     default="", help="System prompt")
    p_llm.add_argument("--task",       default="default",
                        choices=["default","fast","code","creative","small"])
    p_llm.add_argument("--provider",   default="", help="Force a specific provider")
    p_llm.add_argument("--max-tokens", dest="max_tokens", type=int, default=2048)
    p_llm.add_argument("--temperature",type=float, default=0.7)
    p_llm.add_argument("--providers",  action="store_true", help="List all providers")
    p_llm.add_argument("--verbose",    action="store_true")

    # --- html-game ---
    p_html = sub.add_parser("html-game", help="Generate a complete HTML5 game from text")
    p_html.add_argument("prompt",       help="Game description")
    p_html.add_argument("--genre",      default="auto")
    p_html.add_argument("--title",      default="")
    p_html.add_argument("--name",       default="game")
    p_html.add_argument("--output-dir", dest="output_dir", default=None)

    # --- sprite-sheet ---
    p_ss = sub.add_parser("sprite-sheet", help="Generate character sprite sheet with animations")
    p_ss.add_argument("description",  help="Character description")
    p_ss.add_argument("--style",      default="pixel_art_rpg",
                      help="stardew_valley|hollow_knight|genshin_impact|pixel_art_rpg|retro_8bit|...")
    p_ss.add_argument("--actions",    default="idle,walk,attack",
                      help="Comma-separated: idle,walk,run,jump,attack,cast,hurt,death")
    p_ss.add_argument("--name",       default="character")
    p_ss.add_argument("--output-dir", dest="output_dir", default=None)
    p_ss.add_argument("--no-bg",      dest="no_bg", action="store_true",
                      help="Skip background removal")

    # --- asset-pipeline ---
    p_ap = sub.add_parser("asset-pipeline",
                          help="Narrative asset pipeline: storyline → quests → dialogue → items")
    p_ap.add_argument("theme",         help="Game world theme (e.g. 'dark ice dungeon')")
    p_ap.add_argument("--details",     default="")
    p_ap.add_argument("--genre",       default="dungeon")
    p_ap.add_argument("--output-dir",  dest="output_dir", default=None)

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
        "api":            cmd_api,
        "generate":       cmd_generate,
        "world":          cmd_world,
        "agent":          cmd_agent,
        "scene":          cmd_scene,
        "game":           cmd_game,
        "gdd":            cmd_gdd,
        "brainstorm":     cmd_brainstorm,
        "mda":            cmd_mda,
        "adr":            cmd_adr,
        "lore":           cmd_lore,
        "sprite":         cmd_sprite,
        "ai-sprite":      cmd_ai_sprite,
        "narrative":      cmd_narrative,
        "pipeline":       cmd_pipeline,
        "project":        cmd_project,
        "mcp":            cmd_mcp,
        "llm":            cmd_llm,
        "html-game":      cmd_html_game,
        "sprite-sheet":   cmd_sprite_sheet,
        "asset-pipeline": cmd_asset_pipeline,
        "model":          cmd_model,
        "serve":          cmd_serve,
        "inference":      cmd_inference,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
