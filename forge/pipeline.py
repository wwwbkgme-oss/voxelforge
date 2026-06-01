"""
forge.pipeline
==============
12-agent game development pipeline for VoxelForge.

Inspired by pamirtuna/gamestudio-subagents — implements:
  - 12 specialized agents across market, design, engineering, art, QA
  - 4-phase workflow: Market Validation → Design → Build → Ship
  - Market analysis with Go/No-Go decision
  - Competitor analysis reports
  - Milestone-based project tracking
  - Data scientist with A/B testing recommendations
  - Per-phase quality gates

All agents are LLM-driven when an API key is present.
They fall back to template-based output without an API key.

Usage
-----
>>> from forge.pipeline import GamePipeline
>>> pipeline = GamePipeline()
>>> result = pipeline.run(
...     concept     = "A voxel dungeon crawler where players collect crystals",
...     genre       = "dungeon",
...     platform    = "PC",
...     audience    = "core",
...     mode        = "design",   # design | prototype | development
...     competitors = ["Spelunky", "Rogue Legacy"],
... )
>>> print(result["market"]["recommendation"])  # GO / NO-GO / PIVOT
>>> print(result["gdd_path"])
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

@dataclass
class Agent:
    name:         str
    role:         str
    tier:         str   # director | lead | specialist
    description:  str
    prompt_template: str = ""

    def describe(self) -> str:
        return f"[{self.tier.upper()}] {self.name} — {self.role}"


AGENTS: Dict[str, Agent] = {
    "master_orchestrator": Agent(
        name        = "Master Orchestrator",
        role        = "System coordinator and project initializer",
        tier        = "director",
        description = "Coordinates all agents, manages phase transitions, resolves conflicts.",
    ),
    "producer": Agent(
        name        = "Producer",
        role        = "Project manager ensuring timelines and quality",
        tier        = "director",
        description = "Owns timeline, scope, and team direction. Enforces quality gates.",
    ),
    "market_analyst": Agent(
        name        = "Market Analyst",
        role        = "Competitive analysis and market intelligence",
        tier        = "lead",
        description = "Validates market opportunity, analyzes competitors, gives Go/No-Go.",
    ),
    "data_scientist": Agent(
        name        = "Data Scientist",
        role        = "Analytics, metrics, and predictive modeling",
        tier        = "lead",
        description = "Designs telemetry, plans A/B tests, interprets player data.",
    ),
    "sr_game_designer": Agent(
        name        = "Sr Game Designer",
        role        = "Vision holder and systems architect",
        tier        = "lead",
        description = "Owns GDD, core loop, and game systems. MDA framework expert.",
    ),
    "mid_game_designer": Agent(
        name        = "Mid Game Designer",
        role        = "Content creator and implementation specialist",
        tier        = "specialist",
        description = "Creates content specs, level designs, and progression curves.",
    ),
    "mechanics_developer": Agent(
        name        = "Mechanics Developer",
        role        = "Core gameplay systems engineer",
        tier        = "specialist",
        description = "Implements core mechanics, physics, and engine integrations.",
    ),
    "game_feel_developer": Agent(
        name        = "Game Feel Developer",
        role        = "Polish and game juice specialist",
        tier        = "specialist",
        description = "Screen shake, particles, audio, timing — makes the game feel great.",
    ),
    "sr_game_artist": Agent(
        name        = "Sr Game Artist",
        role        = "Art director defining visual style",
        tier        = "lead",
        description = "Owns art direction, style guide, and visual consistency.",
    ),
    "technical_artist": Agent(
        name        = "Technical Artist",
        role        = "Shaders, VFX, and optimization expert",
        tier        = "specialist",
        description = "Bridges art and code — shaders, render pipelines, asset pipelines.",
    ),
    "ui_ux_agent": Agent(
        name        = "UI/UX Agent",
        role        = "Interface and user experience designer",
        tier        = "specialist",
        description = "Designs all UI flows, menus, HUD, and player feedback systems.",
    ),
    "qa_agent": Agent(
        name        = "QA Agent",
        role        = "Testing, validation, and quality assurance",
        tier        = "specialist",
        description = "Writes test plans, finds bugs, validates quality gates.",
    ),
}


def agents_for_mode(mode: str) -> List[str]:
    """Return agent IDs to activate for a given development mode."""
    base = ["master_orchestrator", "producer", "market_analyst", "data_scientist"]
    if mode == "design":
        return base + ["sr_game_designer", "mid_game_designer", "sr_game_artist"]
    elif mode == "prototype":
        return base + ["sr_game_designer", "mechanics_developer", "qa_agent"]
    else:  # development
        return list(AGENTS.keys())


# ---------------------------------------------------------------------------
# Phase results
# ---------------------------------------------------------------------------

@dataclass
class MarketAnalysisResult:
    concept:           str
    genre:             str
    recommendation:    str   # GO | NO-GO | PIVOT
    confidence:        str   # High | Medium | Low
    opportunity_score: int   # 0–10
    market_size:       str
    growth_rate:       str
    target_audience:   str
    competitors:       List[Dict[str, str]] = field(default_factory=list)
    opportunities:     List[str]            = field(default_factory=list)
    risks:             List[str]            = field(default_factory=list)
    action_items:      List[str]            = field(default_factory=list)
    report_path:       str = ""

    def summary(self) -> str:
        return (
            f"Market Analysis — {self.concept}\n"
            f"Recommendation: {self.recommendation} (confidence: {self.confidence})\n"
            f"Score: {self.opportunity_score}/10  |  Market: {self.market_size}  |  "
            f"Growth: {self.growth_rate}\n"
            f"Audience: {self.target_audience}\n"
            f"Risks: {', '.join(self.risks[:2])}\n"
            f"Actions: {', '.join(self.action_items[:2])}"
        )


@dataclass
class DesignPhaseResult:
    gdd_path:         str
    pillars:          List[str]
    core_loop:        str
    mechanics:        List[str]
    art_style:        str
    tech_stack:       str
    milestones:       List[Dict[str, str]] = field(default_factory=list)
    analytics_plan:   str = ""


@dataclass
class BuildPhaseResult:
    scene_path:     str
    assets:         List[str] = field(default_factory=list)
    scripts:        List[str] = field(default_factory=list)
    entity_count:   int = 0
    run_command:    str = ""


@dataclass
class QAPhaseResult:
    passed:         bool
    test_plan_path: str
    issues:         List[str] = field(default_factory=list)
    metrics:        Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    concept:    str
    mode:       str
    agents:     List[str]
    market:     Optional[MarketAnalysisResult] = None
    design:     Optional[DesignPhaseResult]    = None
    build:      Optional[BuildPhaseResult]     = None
    qa:         Optional[QAPhaseResult]        = None
    project_dir: str = ""
    elapsed_s:   float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "concept":     self.concept,
            "mode":        self.mode,
            "agents":      self.agents,
            "project_dir": self.project_dir,
            "elapsed_s":   self.elapsed_s,
        }
        if self.market:
            d["market"] = {
                "recommendation":    self.market.recommendation,
                "confidence":        self.market.confidence,
                "opportunity_score": self.market.opportunity_score,
                "market_size":       self.market.market_size,
                "growth_rate":       self.market.growth_rate,
                "target_audience":   self.market.target_audience,
                "risks":             self.market.risks,
                "action_items":      self.market.action_items,
                "report_path":       self.market.report_path,
            }
        if self.design:
            d["design"] = {
                "gdd_path":   self.design.gdd_path,
                "pillars":    self.design.pillars,
                "core_loop":  self.design.core_loop,
                "art_style":  self.design.art_style,
                "milestones": self.design.milestones,
            }
        if self.build:
            d["build"] = {
                "scene_path":   self.build.scene_path,
                "assets":       self.build.assets,
                "entity_count": self.build.entity_count,
                "run_command":  self.build.run_command,
            }
        if self.qa:
            d["qa"] = {
                "passed":         self.qa.passed,
                "test_plan_path": self.qa.test_plan_path,
                "issues":         self.qa.issues,
                "metrics":        self.qa.metrics,
            }
        return d


# ---------------------------------------------------------------------------
# LLM helpers (reuse pattern from narrative.py)
# ---------------------------------------------------------------------------

def _llm_call(prompt: str, system: str = "",
               api_key: str = "", model: str = "",
               api_base: str = "") -> str:
    """Single LLM call. Returns empty string if no API key."""
    key  = api_key  or os.environ.get("LLM_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    mdl  = model    or os.environ.get("LLM_MODEL", "gpt-4o-mini")
    base = api_base or os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")

    if not key:
        return ""

    import requests
    msgs: List[Dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": mdl, "messages": msgs, "temperature": 0.7, "max_tokens": 800},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        print(f"[pipeline] LLM call failed: {exc}")
        return ""


# ---------------------------------------------------------------------------
# GamePipeline
# ---------------------------------------------------------------------------

class GamePipeline:
    """
    Orchestrates the full 12-agent game development pipeline.

    Phases:
    1. Market Validation (Market Analyst → Go/No-Go)
    2. Design (Sr Designer → GDD, milestones, art direction)
    3. Build (Generators → voxel assets + scene)
    4. QA (QA Agent → test plan, validation)
    """

    def __init__(
        self,
        output_dir:  str = "projects",
        api_key:     str = "",
        model:       str = "",
        api_base:    str = "",
    ):
        self.output_dir = output_dir
        self._api_key   = api_key
        self._model     = model
        self._api_base  = api_base
        os.makedirs(output_dir, exist_ok=True)

    def _llm(self, prompt: str, system: str = "") -> str:
        return _llm_call(prompt, system,
                         api_key=self._api_key, model=self._model,
                         api_base=self._api_base)

    # ------------------------------------------------------------------
    def run(
        self,
        concept:     str,
        genre:       str       = "dungeon",
        platform:    str       = "PC",
        audience:    str       = "core",
        mode:        str       = "design",
        competitors: List[str] = None,
        timeline:    str       = "Short",
        usp:         str       = "",
        seed:        int       = 42,
        build_game:  bool      = True,
    ) -> PipelineResult:
        """
        Run the full pipeline for a game concept.

        Parameters
        ----------
        concept : str
            One-sentence game description.
        genre : str
            dungeon | village | space | fantasy | horror | arctic
        platform : str
            PC | Mobile | Console | Web
        audience : str
            casual | core | hardcore
        mode : str
            design | prototype | development
        competitors : list[str]
            Known competitor games.
        timeline : str
            Rapid | Short | Medium | Long
        usp : str
            Unique selling proposition.
        build_game : bool
            Whether to run the Build phase (generates actual VoxelForge game).

        Returns
        -------
        PipelineResult
        """
        import time
        t0          = time.time()
        competitors = competitors or []
        slug        = re.sub(r"[^\w]", "_", concept.lower())[:20]
        proj_dir    = os.path.join(self.output_dir, slug)
        active_agents = agents_for_mode(mode)

        print(f"[Pipeline] Starting: {concept!r}")
        print(f"[Pipeline] Mode={mode}  Genre={genre}  Agents={len(active_agents)}")

        result = PipelineResult(
            concept     = concept,
            mode        = mode,
            agents      = active_agents,
            project_dir = proj_dir,
        )

        # --- Phase 1: Market Validation ---
        if "market_analyst" in active_agents:
            print("[Pipeline] Phase 1: Market Validation...")
            result.market = self._phase_market(
                concept, genre, platform, audience, competitors, usp, proj_dir
            )
            print(f"[Pipeline] Market → {result.market.recommendation}")

            if result.market.recommendation == "NO-GO" and mode == "development":
                print("[Pipeline] NO-GO signal — stopping pipeline. Review market report.")
                result.elapsed_s = time.time() - t0
                return result

        # --- Phase 2: Design ---
        if "sr_game_designer" in active_agents:
            print("[Pipeline] Phase 2: Design phase...")
            result.design = self._phase_design(
                concept, genre, platform, audience, timeline, usp,
                competitors, proj_dir, seed
            )
            print(f"[Pipeline] GDD → {result.design.gdd_path}")

        # --- Phase 3: Build ---
        if build_game and mode in ("prototype", "development"):
            print("[Pipeline] Phase 3: Build phase...")
            result.build = self._phase_build(
                concept, genre, result.design, proj_dir, seed
            )
            if result.build:
                print(f"[Pipeline] Build → {result.build.scene_path}")

        # --- Phase 4: QA ---
        if "qa_agent" in active_agents and mode in ("prototype", "development"):
            print("[Pipeline] Phase 4: QA validation...")
            result.qa = self._phase_qa(
                concept, result.build, proj_dir
            )
            print(f"[Pipeline] QA → {'PASS' if result.qa.passed else 'FAIL'}")

        result.elapsed_s = time.time() - t0
        print(f"[Pipeline] Done in {result.elapsed_s:.1f}s")
        return result

    # ------------------------------------------------------------------
    # Phase 1: Market Validation
    # ------------------------------------------------------------------

    def _phase_market(
        self,
        concept:     str,
        genre:       str,
        platform:    str,
        audience:    str,
        competitors: List[str],
        usp:         str,
        proj_dir:    str,
    ) -> MarketAnalysisResult:
        market_dir = os.path.join(proj_dir, "resources", "market-research")
        os.makedirs(market_dir, exist_ok=True)

        # LLM market analysis
        llm_analysis = self._llm(
            f"""Analyze the market for this game concept:
Title: {concept}
Genre: {genre}  Platform: {platform}  Audience: {audience}
USP: {usp or "Not defined"}
Competitors: {', '.join(competitors) or "None specified"}

Respond with JSON only:
{{
  "recommendation": "GO|NO-GO|PIVOT",
  "confidence": "High|Medium|Low",
  "opportunity_score": <0-10>,
  "market_size": "$X billion",
  "growth_rate": "X% annually",
  "target_audience": "description",
  "opportunities": ["gap 1", "gap 2"],
  "risks": ["risk 1", "risk 2", "risk 3"],
  "action_items": ["action 1", "action 2"]
}}""",
            system = "You are a game market analyst. Be specific and data-driven.",
        )

        # Parse LLM response or use defaults
        market_data = _parse_json_safe(llm_analysis) or self._default_market_data(
            concept, genre, audience
        )

        # Write competitor analysis files
        for comp in competitors:
            comp_path = os.path.join(market_dir, f"competitor_{_slug(comp)}.md")
            self._write_competitor_analysis(comp, genre, comp_path)

        # Write market overview
        report_path = os.path.join(market_dir, "market_overview.md")
        self._write_market_overview(concept, genre, platform, audience, competitors,
                                     market_data, report_path)

        return MarketAnalysisResult(
            concept           = concept,
            genre             = genre,
            recommendation    = market_data.get("recommendation", "GO"),
            confidence        = market_data.get("confidence", "Medium"),
            opportunity_score = int(market_data.get("opportunity_score", 6)),
            market_size       = market_data.get("market_size", "$2B"),
            growth_rate       = market_data.get("growth_rate", "8% annually"),
            target_audience   = market_data.get("target_audience", audience),
            competitors       = [{"name": c} for c in competitors],
            opportunities     = market_data.get("opportunities", []),
            risks             = market_data.get("risks", []),
            action_items      = market_data.get("action_items", []),
            report_path       = report_path,
        )

    def _default_market_data(self, concept: str, genre: str, audience: str) -> Dict[str, Any]:
        market_sizes = {
            "dungeon": "$3.2B", "village": "$1.8B", "space": "$2.5B",
            "fantasy": "$5.1B", "horror": "$1.2B", "arctic": "$0.8B",
        }
        return {
            "recommendation":    "GO",
            "confidence":        "Medium",
            "opportunity_score": 7,
            "market_size":       market_sizes.get(genre, "$2B"),
            "growth_rate":       "8% annually",
            "target_audience":   f"{audience.title()} {genre} game players, 16–35",
            "opportunities":     [
                f"Underserved AI-generated voxel {genre} niche",
                "Procedural content reduces development cost",
            ],
            "risks":             [
                "Market saturation in indie games",
                "Player retention challenge without live service",
                "Art direction may not stand out",
            ],
            "action_items":      [
                "Validate core loop with 5 test players",
                "Define unique selling point clearly in marketing",
                "Establish metrics: D1/D7/D30 retention targets",
            ],
        }

    def _write_competitor_analysis(self, competitor: str, genre: str, path: str) -> None:
        llm_content = self._llm(
            f"Write a 300-word competitive analysis of '{competitor}' as a {genre} game. "
            "Include: market position, strengths, weaknesses, lessons for us.",
            system = "You are a game market analyst. Be specific.",
        )
        content = f"""# Competitor Analysis: {competitor}

**Genre**: {genre}
**Date**: {date.today()}
**Analyst**: Market Analyst Agent

{llm_content or f'''## Overview
**Game Name**: {competitor}
**Genre**: {genre}

## Strengths
- Established player base
- Polished gameplay loop
- Strong marketing

## Weaknesses
- High development cost
- Limited replayability
- Dated visual style

## Opportunities for Us
- AI-generated content for faster iteration
- Unique voxel aesthetic
- Lower price point
'''}
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _write_market_overview(
        self, concept: str, genre: str, platform: str, audience: str,
        competitors: List[str], data: Dict[str, Any], path: str
    ) -> None:
        content = f"""# Market Overview: {genre.title()} Games
**Date**: {date.today()}  **Analyst**: Market Analyst Agent

## Executive Summary
**Recommendation**: {data.get('recommendation', 'GO')}
**Confidence**: {data.get('confidence', 'Medium')}
**Opportunity Score**: {data.get('opportunity_score', 7)}/10

## Project Context
**Game**: {concept}
**Genre**: {genre}  **Platform**: {platform}  **Audience**: {audience}
**Competitors**: {', '.join(competitors) or 'None analyzed'}

## Market Size & Growth
- **Market Size**: {data.get('market_size', '$2B')}
- **Growth Rate**: {data.get('growth_rate', '8%/year')}
- **Target Audience**: {data.get('target_audience', audience)}

## Opportunities
{chr(10).join(f'- {o}' for o in data.get('opportunities', []))}

## Risks
{chr(10).join(f'- {r}' for r in data.get('risks', []))}

## Action Items
{chr(10).join(f'- [ ] {a}' for a in data.get('action_items', []))}

---
*Generated by VoxelForge Market Analyst Agent*
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # ------------------------------------------------------------------
    # Phase 2: Design
    # ------------------------------------------------------------------

    def _phase_design(
        self,
        concept:     str,
        genre:       str,
        platform:    str,
        audience:    str,
        timeline:    str,
        usp:         str,
        competitors: List[str],
        proj_dir:    str,
        seed:        int,
    ) -> DesignPhaseResult:
        design_dir = os.path.join(proj_dir, "documentation", "design")
        os.makedirs(design_dir, exist_ok=True)

        from .studio import GameDesignDoc
        gdd = GameDesignDoc(
            title        = concept,
            genre        = genre,
            player_class = "warrior",
            enemies      = 3,
            props        = 6,
            level_size   = 48,
            seed         = seed,
        )
        gdd_path = os.path.join(design_dir, "gdd.md")
        gdd.save(gdd_path)

        # LLM-enhanced pillars
        llm_pillars = self._llm(
            f"Give 3 one-line design pillars for: {concept}. Format as JSON list.",
            system = "You are a senior game designer. Be concise.",
        )
        pillars = _parse_json_safe(llm_pillars) or [
            "Challenge — meaningful difficulty curve",
            "Discovery — reward exploration",
            "Expression — meaningful player choices",
        ]
        if not isinstance(pillars, list):
            pillars = [str(pillars)]

        # Milestones
        milestones = _calculate_milestones(timeline, mode="design")

        # Data scientist analytics plan
        analytics_plan = self._llm(
            f"Design a telemetry plan for a {genre} game targeting {audience} players. "
            "List 5 key metrics to track. Format as JSON list of objects with 'metric' and 'why'.",
            system = "You are a game data scientist.",
        ) or json.dumps([
            {"metric": "D1/D7/D30 retention", "why": "Primary health indicator"},
            {"metric": "Session length", "why": "Engagement quality"},
            {"metric": "Level completion rate", "why": "Difficulty calibration"},
            {"metric": "Enemy encounter outcome", "why": "Balance tracking"},
            {"metric": "Chest collection rate", "why": "Objective clarity"},
        ])

        return DesignPhaseResult(
            gdd_path       = gdd_path,
            pillars        = pillars[:3],
            core_loop      = "Explore → Encounter → Overcome → Reward (30-second loop)",
            mechanics      = ["WASD movement", "E interact", "WASD+Space combat"],
            art_style      = "Isometric voxel pixel art (VoxelForge engine)",
            tech_stack     = "VoxelForge C engine + Python forge package",
            milestones     = milestones,
            analytics_plan = analytics_plan,
        )

    # ------------------------------------------------------------------
    # Phase 3: Build
    # ------------------------------------------------------------------

    def _phase_build(
        self,
        concept:    str,
        genre:      str,
        design:     Optional[DesignPhaseResult],
        proj_dir:   str,
        seed:       int,
    ) -> Optional[BuildPhaseResult]:
        try:
            from .voxel import Palette
            from .generators.game import GameGenerator

            gen_dir = os.path.join(proj_dir, "game")
            gen     = GameGenerator(Palette.natural(), seed=seed, output_dir=gen_dir)
            manifest = gen.generate(
                title        = concept,
                genre        = genre,
                player_class = "warrior",
                enemies      = 3,
                props        = 6,
                level_size   = 40,
            )
            return BuildPhaseResult(
                scene_path   = manifest.get("scene_path", ""),
                assets       = [a["path"] for a in manifest.get("assets", [])],
                scripts      = [s["path"] for s in manifest.get("scripts", [])],
                entity_count = manifest.get("entity_count", 0),
                run_command  = manifest.get("run_command", ""),
            )
        except Exception as exc:
            print(f"[Pipeline] Build phase failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Phase 4: QA
    # ------------------------------------------------------------------

    def _phase_qa(
        self,
        concept:  str,
        build:    Optional[BuildPhaseResult],
        proj_dir: str,
    ) -> QAPhaseResult:
        qa_dir = os.path.join(proj_dir, "qa", "test-plans")
        os.makedirs(qa_dir, exist_ok=True)

        issues: List[str] = []
        passed = True

        # Validate build
        if build:
            import os as _os
            if not _os.path.isfile(build.scene_path):
                issues.append(f"Scene file missing: {build.scene_path}")
                passed = False
            for asset in build.assets:
                if not _os.path.isfile(asset):
                    issues.append(f"Missing asset: {asset}")
            if build.entity_count < 3:
                issues.append(f"Too few entities: {build.entity_count}")
        else:
            issues.append("Build phase produced no output")
            passed = False

        # Write test plan
        plan_path = os.path.join(qa_dir, "test_plan.md")
        self._write_test_plan(concept, build, issues, plan_path)

        metrics = {
            "assets_validated":  len(build.assets) if build else 0,
            "scripts_present":   len(build.scripts) if build else 0,
            "entities":          build.entity_count if build else 0,
            "issues_found":      len(issues),
        }

        return QAPhaseResult(
            passed         = passed and len(issues) == 0,
            test_plan_path = plan_path,
            issues         = issues,
            metrics        = metrics,
        )

    def _write_test_plan(
        self, concept: str, build: Optional[BuildPhaseResult],
        issues: List[str], path: str
    ) -> None:
        content = f"""# QA Test Plan: {concept}
**Date**: {date.today()}  **Agent**: QA Agent

## Smoke Tests
- [{'x' if build and build.scene_path else ' '}] Scene file generated
- [{'x' if build and build.entity_count > 3 else ' '}] Entity count > 3
- [{'x' if build and build.run_command else ' '}] Run command present

## Asset Validation
{f"Assets: {len(build.assets)}" if build else "No build output"}
{f"Scripts: {len(build.scripts)}" if build else ""}

## Issues Found
{chr(10).join(f'- ❌ {i}' for i in issues) if issues else '- ✅ No issues found'}

## Run Command
```bash
{build.run_command if build else "N/A"}
```

## Metrics
{json.dumps({"assets": len(build.assets) if build else 0, "scripts": len(build.scripts) if build else 0, "entities": build.entity_count if build else 0}, indent=2)}

---
*Generated by VoxelForge QA Agent*
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(s: str) -> str:
    return re.sub(r"[^\w]", "_", s.lower())[:30]


def _parse_json_safe(text: str) -> Optional[Any]:
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        start = text.find("[")
    end_brace = text.rfind("}")
    end_bracket = text.rfind("]")
    end = max(end_brace, end_bracket)
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _calculate_milestones(timeline: str, mode: str) -> List[Dict[str, str]]:
    today = datetime.now()
    if timeline == "Rapid":
        return [
            {"name": "Concept", "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
             "deliverables": "Game concept, pillars, audience definition"},
            {"name": "Design Docs", "date": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
             "deliverables": "GDD, art style guide, technical spec"},
        ]
    elif timeline == "Short":
        return [
            {"name": "Concept & Market", "date": (today + timedelta(weeks=1)).strftime("%Y-%m-%d"),
             "deliverables": "Validated concept, market research"},
            {"name": "Core Design",      "date": (today + timedelta(weeks=2)).strftime("%Y-%m-%d"),
             "deliverables": "GDD, system designs, content specs"},
            {"name": "Prototype",        "date": (today + timedelta(weeks=3)).strftime("%Y-%m-%d"),
             "deliverables": "Playable prototype, telemetry hooks"},
            {"name": "Release",          "date": (today + timedelta(weeks=4)).strftime("%Y-%m-%d"),
             "deliverables": "Final build, marketing materials"},
        ]
    else:
        return [
            {"name": "Pre-Production", "date": (today + timedelta(weeks=2)).strftime("%Y-%m-%d"),
             "deliverables": "GDD, architecture, asset pipeline"},
            {"name": "Alpha",          "date": (today + timedelta(weeks=6)).strftime("%Y-%m-%d"),
             "deliverables": "Feature-complete build"},
            {"name": "Beta",           "date": (today + timedelta(weeks=10)).strftime("%Y-%m-%d"),
             "deliverables": "Polished build, performance tuned"},
            {"name": "Release",        "date": (today + timedelta(weeks=12)).strftime("%Y-%m-%d"),
             "deliverables": "Ship-ready build"},
        ]
