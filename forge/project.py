"""
forge.project
=============
Project lifecycle manager for VoxelForge.

Inspired by pamirtuna/gamestudio-subagents init_project.py — provides:
  - Full project initialisation with engine-specific folder structures
  - project-config.json management
  - Multi-engine support: VoxelForge, Godot 4, Unity, Unreal Engine 5
  - Status tracking: active | paused | frozen | completed | cancelled
  - Competitor analysis scaffolding
  - Milestone timeline generation
  - Development rules enforcement

Usage
-----
>>> from forge.project import ProjectManager
>>> pm = ProjectManager("projects")
>>> proj = pm.init_project(
...     name        = "Crystal Dungeon",
...     concept     = "A voxel dungeon crawler with AI-generated worlds",
...     genre       = "dungeon",
...     engine      = "voxelforge",
...     mode        = "development",
... )
>>> print(proj.config["project"]["name"])
>>> pm.status("crystal_dungeon")
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Engine-specific directory structures
# ---------------------------------------------------------------------------

def _voxelforge_dirs(folder: str) -> List[str]:
    return [
        f"{folder}/assets/models",
        f"{folder}/assets/sprites",
        f"{folder}/assets/scenes",
        f"{folder}/assets/scripts",
        f"{folder}/generated_assets/terrain",
        f"{folder}/generated_assets/buildings",
        f"{folder}/generated_assets/characters",
        f"{folder}/generated_assets/props",
        f"{folder}/generated_assets/dungeons",
        f"{folder}/generated_assets/sprites",
        f"{folder}/generated_assets/scenes",
        f"{folder}/generated_assets/games",
    ]


def _godot_dirs(folder: str) -> List[str]:
    return [
        f"{folder}/scenes",
        f"{folder}/scripts",
        f"{folder}/assets/sprites",
        f"{folder}/assets/models",
        f"{folder}/assets/audio",
        f"{folder}/assets/ui",
        f"{folder}/assets/shaders",
        f"{folder}/assets/fonts",
        f"{folder}/autoload",
        f"{folder}/addons",
    ]


def _unity_dirs(folder: str) -> List[str]:
    return [
        f"{folder}/Assets/Scripts",
        f"{folder}/Assets/Scenes",
        f"{folder}/Assets/Prefabs",
        f"{folder}/Assets/Materials",
        f"{folder}/Assets/Textures",
        f"{folder}/Assets/Models",
        f"{folder}/Assets/Audio",
        f"{folder}/Assets/Animations",
        f"{folder}/Assets/Shaders",
        f"{folder}/Assets/StreamingAssets",
        f"{folder}/Assets/Editor",
        f"{folder}/Assets/Resources",
        f"{folder}/Packages",
        f"{folder}/ProjectSettings",
    ]


def _unreal_dirs(folder: str) -> List[str]:
    return [
        f"{folder}/Content/Blueprints",
        f"{folder}/Content/Maps",
        f"{folder}/Content/Materials",
        f"{folder}/Content/Meshes",
        f"{folder}/Content/Textures",
        f"{folder}/Content/Audio",
        f"{folder}/Content/Animations",
        f"{folder}/Content/UI",
        f"{folder}/Content/Characters",
        f"{folder}/Source/Public",
        f"{folder}/Source/Private",
        f"{folder}/Plugins",
        f"{folder}/Config",
    ]


COMMON_DIRS = [
    "documentation/design/systems",
    "documentation/design/mechanics",
    "documentation/design/content",
    "documentation/art/concepts",
    "documentation/art/style-guides",
    "documentation/technical/architecture",
    "documentation/technical/api-docs",
    "documentation/production/milestones",
    "documentation/production/reports",
    "documentation/production/retrospectives",
    "resources/market-research",
    "resources/references",
    "qa/test-plans",
    "qa/bug-reports",
    "qa/playtesting",
    "qa/performance-logs",
    "builds/alpha",
    "builds/beta",
    "builds/release",
]

ENGINE_DIRS = {
    "voxelforge":    _voxelforge_dirs,
    "godot":         _godot_dirs,
    "unity":         _unity_dirs,
    "unreal":        _unreal_dirs,
}

ENGINE_VERSIONS = {
    "voxelforge": "1.0",
    "godot":      "4.4.1",
    "unity":      "2023.2",
    "unreal":     "5.3",
}


# ---------------------------------------------------------------------------
# Project config
# ---------------------------------------------------------------------------

@dataclass
class ProjectConfig:
    name:            str
    slug:            str
    concept:         str
    genre:           str
    platform:        str
    audience:        str
    engine:          str
    engine_version:  str
    mode:            str
    timeline:        str
    usp:             str
    competitors:     List[str]
    development_rules: List[str]
    active_agents:   List[str]
    milestones:      List[Dict[str, str]]
    created_at:      str
    updated_at:      str
    status:          str = "active"
    phase:           str = "initialization"
    version:         str = "1.0.0"

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "project": {
                "name":           self.name,
                "slug":           self.slug,
                "concept":        self.concept,
                "genre":          self.genre,
                "platform":       self.platform,
                "audience":       self.audience,
                "engine":         self.engine,
                "engine_version": self.engine_version,
                "mode":           self.mode,
                "timeline":       self.timeline,
                "usp":            self.usp,
                "competitors":    self.competitors,
                "status":         self.status,
                "phase":          self.phase,
                "version":        self.version,
                "created_at":     self.created_at,
                "updated_at":     self.updated_at,
            },
            "development_rules":  self.development_rules,
            "team": {
                "active_agents": self.active_agents,
                "lead_agent":    "producer",
                "orchestrator":  "master_orchestrator",
            },
            "milestones": self.milestones,
            "metrics": {
                "velocity_target":     "10 tasks/week",
                "bug_threshold":       "5 critical, 20 minor",
                "performance_target":  "60 FPS, < 3s load",
            },
        }


# ---------------------------------------------------------------------------
# ProjectManager
# ---------------------------------------------------------------------------

class ProjectManager:
    """
    Full project lifecycle manager for VoxelForge Studio.

    Parameters
    ----------
    base_dir : str
        Root directory where projects are stored.
    """

    def __init__(self, base_dir: str = "projects"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    # ------------------------------------------------------------------
    def init_project(
        self,
        name:              str,
        concept:           str,
        genre:             str  = "dungeon",
        platform:          str  = "PC",
        audience:          str  = "core",
        engine:            str  = "voxelforge",
        engine_version:    str  = "",
        mode:              str  = "development",
        timeline:          str  = "Short",
        usp:               str  = "",
        competitors:       Optional[List[str]] = None,
        development_rules: Optional[List[str]] = None,
    ) -> "Project":
        """
        Initialize a new game project with full folder structure.

        Parameters
        ----------
        name : str
            Human-readable project name.
        concept : str
            One-sentence game description.
        genre : str
            dungeon | village | space | fantasy | horror | arctic
        engine : str
            voxelforge | godot | unity | unreal
        mode : str
            design | prototype | development

        Returns
        -------
        Project
        """
        slug = _slugify(name)
        proj_path = Path(self.base_dir) / slug
        if proj_path.exists():
            print(f"[ProjectManager] Project '{slug}' already exists. Loading...")
            return self.load_project(slug)

        # Resolve engine version
        ev = engine_version or ENGINE_VERSIONS.get(engine.lower(), "latest")

        # Determine agents
        from .pipeline import agents_for_mode
        active_agents = agents_for_mode(mode)

        # Calculate milestones
        from .pipeline import _calculate_milestones
        milestones = _calculate_milestones(timeline, mode)

        # Build config
        now = datetime.utcnow().isoformat()
        config = ProjectConfig(
            name             = name,
            slug             = slug,
            concept          = concept,
            genre            = genre,
            platform         = platform,
            audience         = audience,
            engine           = engine.lower(),
            engine_version   = ev,
            mode             = mode,
            timeline         = timeline,
            usp              = usp,
            competitors      = competitors or [],
            development_rules= development_rules or [
                "Follow engine best practices",
                "Write clean, maintainable code",
                "All commits must pass QA validation",
                "Use semantic versioning for releases",
            ],
            active_agents    = active_agents,
            milestones       = milestones,
            created_at       = now,
            updated_at       = now,
        )

        # Create directory structure
        self._create_dirs(proj_path, engine.lower())

        # Create all initial files
        self._create_config_file(proj_path, config)
        self._create_gdd(proj_path, config)
        self._create_readme(proj_path, config)
        self._create_gitignore(proj_path, config)
        self._create_timeline(proj_path, config)
        self._create_competitor_scaffolding(proj_path, config)
        self._create_engine_files(proj_path, config)
        self._create_claude_md(proj_path, config)

        print(f"[ProjectManager] Initialized '{name}' in {proj_path}")
        return Project(path=str(proj_path), config=config)

    # ------------------------------------------------------------------
    def load_project(self, slug: str) -> "Project":
        """Load an existing project by slug."""
        proj_path = Path(self.base_dir) / slug
        config_path = proj_path / "project-config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"No project-config.json at {config_path}")
        with open(config_path) as f:
            raw = json.load(f)
        p = raw["project"]
        config = ProjectConfig(
            name             = p["name"],
            slug             = p["slug"],
            concept          = p["concept"],
            genre            = p["genre"],
            platform         = p.get("platform", "PC"),
            audience         = p.get("audience", "core"),
            engine           = p.get("engine", "voxelforge"),
            engine_version   = p.get("engine_version", "1.0"),
            mode             = p.get("mode", "development"),
            timeline         = p.get("timeline", "Short"),
            usp              = p.get("usp", ""),
            competitors      = p.get("competitors", []),
            development_rules= raw.get("development_rules", []),
            active_agents    = raw.get("team", {}).get("active_agents", []),
            milestones       = raw.get("milestones", []),
            created_at       = p.get("created_at", ""),
            updated_at       = p.get("updated_at", ""),
            status           = p.get("status", "active"),
            phase            = p.get("phase", "development"),
        )
        return Project(path=str(proj_path), config=config)

    # ------------------------------------------------------------------
    def list_projects(self) -> List[Dict[str, str]]:
        """List all projects in the base directory."""
        projects = []
        for d in sorted(Path(self.base_dir).iterdir()):
            cfg = d / "project-config.json"
            if cfg.exists():
                try:
                    with open(cfg) as f:
                        raw = json.load(f)
                    p = raw.get("project", {})
                    projects.append({
                        "slug":    d.name,
                        "name":    p.get("name", d.name),
                        "genre":   p.get("genre", ""),
                        "engine":  p.get("engine", ""),
                        "mode":    p.get("mode", ""),
                        "status":  p.get("status", "active"),
                        "phase":   p.get("phase", ""),
                        "created": p.get("created_at", "")[:10],
                    })
                except Exception:
                    pass
        return projects

    def update_status(self, slug: str, status: str, phase: Optional[str] = None) -> None:
        """Update project status: active | paused | frozen | completed | cancelled"""
        proj = self.load_project(slug)
        proj.config.status = status
        if phase:
            proj.config.phase = phase
        proj.config.updated_at = datetime.utcnow().isoformat()
        self._create_config_file(Path(self.base_dir) / slug, proj.config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_dirs(self, base: Path, engine: str) -> None:
        source_folder = f"source/project-{base.name}"
        engine_fn = ENGINE_DIRS.get(engine, ENGINE_DIRS["voxelforge"])
        dirs = COMMON_DIRS + engine_fn(source_folder)
        for d in dirs:
            (base / d).mkdir(parents=True, exist_ok=True)

    def _create_config_file(self, base: Path, config: ProjectConfig) -> None:
        with open(base / "project-config.json", "w") as f:
            json.dump(config.to_json_dict(), f, indent=2)

    def _create_gdd(self, base: Path, config: ProjectConfig) -> None:
        from .studio import GameDesignDoc
        gdd  = GameDesignDoc(
            title        = config.name,
            genre        = config.genre,
            player_class = "warrior",
            enemies      = 3,
            level_size   = 48,
        )
        path = base / "documentation" / "design" / "gdd.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        gdd.save(str(path))

    def _create_readme(self, base: Path, config: ProjectConfig) -> None:
        source_folder = f"source/project-{base.name}"
        content = f"""# {config.name}

## Concept
{config.concept}

## Engine: {config.engine.title()} v{config.engine_version}

## Project Info
- **Genre**: {config.genre}
- **Platform**: {config.platform}
- **Audience**: {config.audience}
- **Mode**: {config.mode}
- **Status**: {config.status}

## Active Agents
{', '.join(config.active_agents)}

## Source Code
Located at `{source_folder}/`

## Development Rules
{chr(10).join(f'- {r}' for r in config.development_rules)}

## Quick Start
```bash
# Generate a complete game
python3 -c "
from forge.generators.game import GameGenerator
from forge.voxel import Palette
gen = GameGenerator(Palette.natural(), output_dir='generated_assets')
manifest = gen.generate(title='{config.name}', genre='{config.genre}')
print(manifest['run_command'])
"
```

## Next Steps
1. Review `documentation/design/gdd.md`
2. Run market analysis: `voxelforge mda projects/{base.name}/project-config.json`
3. Generate game: `voxelforge game --title "{config.name}" --genre {config.genre}`
"""
        (base / "README.md").write_text(content, encoding="utf-8")

    def _create_gitignore(self, base: Path, config: ProjectConfig) -> None:
        content = """# Builds
builds/
*.exe *.app *.apk

# Generated assets (large files)
generated_assets/
*.vox.bak

# Engine temp
.godot/ .import/ Library/ Temp/ Build/

# Python
__pycache__/ *.pyc .venv/

# IDE
.vscode/ .idea/ *.suo *.user

# OS
.DS_Store Thumbs.db

# Logs
*.log
"""
        (base / ".gitignore").write_text(content, encoding="utf-8")

    def _create_timeline(self, base: Path, config: ProjectConfig) -> None:
        lines = [f"# {config.name} — Production Timeline\n\n"]
        lines.append(f"## Timeline: {config.timeline}\n\n## Milestones\n\n")
        for m in config.milestones:
            lines.append(
                f"### {m['name']} — {m['date']}\n"
                f"**Deliverables**: {m.get('deliverables', '')}\n\n"
            )
        path = base / "documentation" / "production" / "timeline.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(lines), encoding="utf-8")

    def _create_competitor_scaffolding(self, base: Path, config: ProjectConfig) -> None:
        market_dir = base / "resources" / "market-research"
        market_dir.mkdir(parents=True, exist_ok=True)
        for comp in config.competitors:
            comp_path = market_dir / f"competitor_{_slugify(comp)}.md"
            comp_path.write_text(f"""# Competitor Analysis: {comp}

**Date**: {date.today()}

## Overview
- **Name**: {comp}
- **Genre**: {config.genre}

## Strengths
- [To be researched]

## Weaknesses
- [To be researched]

## Opportunities for Us
- [To be researched]
""", encoding="utf-8")

        (market_dir / "market_overview.md").write_text(
            f"# Market Overview: {config.genre.title()} Games\n\n"
            f"**Project**: {config.name}\n"
            f"**Competitors**: {', '.join(config.competitors) or 'TBD'}\n\n"
            "## Status\nMarket analysis pending. Run: `voxelforge pipeline analyze`\n",
            encoding="utf-8",
        )

    def _create_engine_files(self, base: Path, config: ProjectConfig) -> None:
        """Create engine-specific configuration files."""
        source_folder = base / f"source/project-{base.name}"
        source_folder.mkdir(parents=True, exist_ok=True)

        eng = config.engine.lower()
        if eng == "godot":
            v = config.engine_version
            feat = f'PackedStringArray("{v}", "Forward Plus")'
            (source_folder / "project.godot").write_text(
                f'[application]\nconfig/name="{config.name}"\n'
                f'config/features={feat}\nconfig/icon="res://icon.svg"\n',
                encoding="utf-8"
            )
        elif eng == "unity":
            pkg_dir = source_folder / "Packages"
            pkg_dir.mkdir(parents=True, exist_ok=True)
            (pkg_dir / "manifest.json").write_text(
                '{"dependencies":{"com.unity.inputsystem":"1.7.0",'
                '"com.unity.textmeshpro":"3.0.6"}}',
                encoding="utf-8"
            )
        elif eng == "unreal":
            proj_name = config.name.replace(" ", "")
            (source_folder / f"{proj_name}.uproject").write_text(
                json.dumps({
                    "FileVersion": 3,
                    "EngineAssociation": config.engine_version,
                    "Category": "", "Description": "",
                    "Modules": [{"Name": proj_name, "Type": "Runtime", "LoadingPhase": "Default"}],
                }, indent="\t"),
                encoding="utf-8"
            )
        elif eng == "voxelforge":
            (source_folder / "README.md").write_text(
                f"# {config.name} — VoxelForge Source\n\n"
                "Use the `forge` Python package to generate assets:\n"
                "```python\nfrom forge.generators.game import GameGenerator\n```\n",
                encoding="utf-8"
            )

    def _create_claude_md(self, base: Path, config: ProjectConfig) -> None:
        """Create project-level CLAUDE.md for agent context."""
        content = f"""# {config.name} — Agent Configuration

**Engine**: {config.engine.title()} v{config.engine_version}
**Genre**: {config.genre}  **Mode**: {config.mode}  **Audience**: {config.audience}

## Active Agents
{', '.join(config.active_agents)}

## Development Rules
{chr(10).join(f'- {r}' for r in config.development_rules)}

## Quick Commands
```bash
# Generate assets
voxelforge generate terrain --biome {config.genre if config.genre in ('desert','forest') else 'grassland'}
voxelforge game --title "{config.name}" --genre {config.genre}
# Market analysis
voxelforge pipeline analyze "{config.concept}" --genre {config.genre}
```
"""
        (base / "CLAUDE.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Project object
# ---------------------------------------------------------------------------

@dataclass
class Project:
    path:   str
    config: ProjectConfig

    def status_summary(self) -> str:
        c = self.config
        return (
            f"Project: {c.name}\n"
            f"  Status:  {c.status}  |  Phase: {c.phase}\n"
            f"  Engine:  {c.engine} v{c.engine_version}\n"
            f"  Genre:   {c.genre}  |  Mode: {c.mode}\n"
            f"  Agents:  {len(c.active_agents)}\n"
            f"  Path:    {self.path}"
        )

    def next_milestone(self) -> Optional[Dict[str, str]]:
        today = date.today().isoformat()
        for m in self.config.milestones:
            if m.get("date", "") >= today:
                return m
        return None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    import re
    return re.sub(r"[^\w]", "-", name.lower()).strip("-")[:40]
