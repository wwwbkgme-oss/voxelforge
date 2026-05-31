"""
forge.ai.agent
==============
VoxelForge Autonomous Game-Creation Agent.

Given a plain-English prompt, the agent plans and executes a complete
game-world generation loop — terrain, assets, scene assembly — without
human intervention.

It works with **any** OpenAI-compatible API (GPT-4o, Claude via OpenRouter,
local Ollama tool-use models, etc.).

Quickstart
----------
    export OPENAI_API_KEY=sk-...
    python -m forge.ai.agent "a snowy mountain village with 5 medieval buildings"

Or from Python:
    from forge.ai.agent import VoxelForgeAgent
    agent = VoxelForgeAgent()
    result = agent.run("a haunted forest dungeon with ruins and mushrooms")
    print(result)

No API key? Use direct mode (no LLM, purely procedural from description):
    agent = VoxelForgeAgent(direct_mode=True)
    result = agent.run("desert town, 3 buildings, archer hero")
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from .tools import TOOLS, call_tool


# ---------------------------------------------------------------------------
# Keyword-based intent parser (used in direct_mode and as fallback)
# ---------------------------------------------------------------------------

_BIOMES      = ["grassland", "desert", "snow", "ocean", "forest"]
_STYLES      = ["modern", "medieval", "sci-fi", "rustic", "fantasy"]
_CLASSES     = ["warrior", "mage", "archer", "rogue"]
_PROP_TYPES  = ["tree", "crate", "barrel", "lamp_post", "rock", "chest", "mushroom"]
_SKIN_TONES  = ["light", "tan", "dark", "fantasy"]
_HAIR_COLORS = ["blonde", "brown", "black", "red", "white", "blue"]
_ARMOURS     = ["none", "leather", "chainmail", "plate", "mage"]
_WEAPONS     = ["none", "sword", "staff", "bow", "axe"]


def _extract_int(text: str, keywords: List[str], default: int) -> int:
    """Return first integer found after any of the keywords."""
    t = text.lower()
    for kw in keywords:
        m = re.search(rf"{kw}\s*(\d+)", t)
        if m:
            return int(m.group(1))
    # Generic number extraction near keyword
    for kw in keywords:
        pos = t.find(kw)
        if pos != -1:
            surrounding = t[max(0, pos-10):pos+30]
            m = re.search(r"(\d+)", surrounding)
            if m:
                return int(m.group(1))
    return default


def _extract_choice(text: str, options: List[str], default: str) -> str:
    t = text.lower()
    for opt in options:
        if opt in t:
            return opt
    return default


def _parse_intent(prompt: str) -> Dict[str, Any]:
    """
    Naive keyword-based intent extractor that turns a free-text prompt into
    a structured world-build plan.
    """
    p = prompt.lower()

    biome   = _extract_choice(p, _BIOMES, "grassland")
    style   = _extract_choice(p, _STYLES, "medieval")

    # World size hints
    size_kw = ["large", "huge", "big", "giant", "massive"]
    sm_kw   = ["small", "tiny", "mini", "compact"]
    if any(w in p for w in size_kw):
        width = height = 96
    elif any(w in p for w in sm_kw):
        width = height = 32
    else:
        width = height = 64

    buildings  = _extract_int(p, ["building", "house", "structure", "tower"], 3)
    characters = _extract_int(p, ["character", "hero", "npc", "person", "warrior", "mage"], 2)
    props      = _extract_int(p, ["prop", "tree", "object", "item", "decor"], 5)

    # Cap values at API limits
    buildings  = min(buildings,  20)
    characters = min(characters, 20)
    props      = min(props,      30)

    # World name — take first 3 meaningful words from prompt
    words = [w for w in re.sub(r"[^\w\s]", "", prompt.lower()).split()
             if len(w) > 2 and w not in ("the", "and", "with", "for", "from")]
    name  = "_".join(words[:3]) or "voxelworld"

    return {
        "name":           name,
        "biome":          biome,
        "width":          width,
        "height":         height,
        "buildings":      buildings,
        "building_style": style,
        "characters":     characters,
        "props":          props,
        "seed":           abs(hash(prompt)) % 100000,
    }


# ---------------------------------------------------------------------------
# VoxelForgeAgent
# ---------------------------------------------------------------------------

class VoxelForgeAgent:
    """
    Autonomous voxel world creation agent.

    Parameters
    ----------
    api_key : str, optional
        OpenAI (or compatible) API key.  Falls back to OPENAI_API_KEY env var.
    model : str
        LLM model to use.  Default: "gpt-4o".
    base_url : str, optional
        Override the OpenAI base URL for compatible providers (Ollama, OpenRouter, etc.)
    direct_mode : bool
        Skip the LLM and use only the keyword parser.  Useful for offline use.
    max_rounds : int
        Maximum tool-calling rounds per run before aborting.
    verbose : bool
        Print progress to stdout.
    """

    SYSTEM_PROMPT = """You are VoxelForge AI, an autonomous game world creation engine.
Your job is to take a user description and build a complete, playable game world using the
available tools.

WORKFLOW:
1. Analyse the user's description to understand the world theme, biome, scale, and content.
2. Call `build_world` to generate the entire world in one shot (terrain + buildings + characters + props + scene).
   - Choose biome, building_style, character count, prop count based on the description.
   - Set a meaningful `name` from the description (snake_case, no spaces).
3. If the user asked for specific extra assets not covered by build_world, generate them individually
   with generate_terrain / generate_building / generate_character / generate_prop.
4. If extra assets were generated, call `build_scene` to create a final scene that includes everything.
5. Always end with a summary: list of all generated files and how to run the scene in VoxelForge.

RULES:
- Always call at least `build_world` first.
- Use appropriate biomes: medieval/fantasy → grassland, sci-fi → desert/ocean, horror → forest, arctic → snow.
- Give every asset a unique descriptive name using snake_case.
- Never call the same tool with the same arguments twice.
- Stop after producing a working scene file.

Be creative but efficient. Produce a complete, directly playable game world."""

    def __init__(
        self,
        api_key:     Optional[str] = None,
        model:       str           = "gpt-4o",
        base_url:    Optional[str] = None,
        direct_mode: bool          = False,
        max_rounds:  int           = 20,
        verbose:     bool          = True,
    ):
        self.model       = model
        self.max_rounds  = max_rounds
        self.verbose     = verbose
        self.direct_mode = direct_mode
        self._client     = None

        if not direct_mode:
            try:
                import openai
                key = api_key or os.environ.get("OPENAI_API_KEY")
                kwargs: Dict[str, Any] = {}
                if base_url:
                    kwargs["base_url"] = base_url
                self._client = openai.OpenAI(api_key=key, **kwargs)
            except ImportError:
                if verbose:
                    print("[VoxelForge] openai package not found — falling back to direct mode")
                self.direct_mode = True

    # ------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[VoxelForge] {msg}")

    # ------------------------------------------------------------------
    def run(self, prompt: str) -> Dict[str, Any]:
        """
        Run the agent to generate a complete game world from a text prompt.

        Returns a summary dict with scene_path, asset_paths, and statistics.
        """
        self._log(f"Starting world generation for: {prompt!r}")
        t0 = time.time()

        if self.direct_mode:
            result = self._run_direct(prompt)
        else:
            result = self._run_llm(prompt)

        elapsed = time.time() - t0
        result["elapsed_seconds"] = round(elapsed, 2)
        self._log(f"Done in {elapsed:.1f}s — scene: {result.get('scene_path', '?')}")
        return result

    # ------------------------------------------------------------------
    def _run_direct(self, prompt: str) -> Dict[str, Any]:
        """
        Run without an LLM.  Parses the prompt with keyword heuristics and
        calls build_world directly.
        """
        self._log("Direct mode: extracting intent from prompt keywords")
        params = _parse_intent(prompt)
        self._log(f"Parsed intent: {params}")
        result = call_tool("build_world", params)
        return {
            "mode":         "direct",
            "params":       params,
            "scene_path":   result.get("scene_path", ""),
            "asset_paths":  result.get("asset_paths", []),
            "entity_count": result.get("entity_count", 0),
            "seed":         result.get("seed", 0),
            "raw":          result,
        }

    # ------------------------------------------------------------------
    def _run_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Run with an LLM using OpenAI function-calling.
        The LLM plans the generation and calls tools; we execute them.
        """
        messages: List[Dict[str, Any]] = [
            {"role": "system",  "content": self.SYSTEM_PROMPT},
            {"role": "user",    "content": prompt},
        ]

        tool_results: List[Dict[str, Any]] = []
        scene_path   = ""
        asset_paths: List[str] = []

        for round_n in range(self.max_rounds):
            self._log(f"LLM round {round_n + 1}/{self.max_rounds}")
            try:
                response = self._client.chat.completions.create(  # type: ignore[union-attr]
                    model   = self.model,
                    messages= messages,
                    tools   = TOOLS,
                    tool_choice = "auto",
                )
            except Exception as exc:
                self._log(f"LLM error: {exc} — falling back to direct mode")
                return self._run_direct(prompt)

            msg = response.choices[0].message

            # No more tool calls → done
            if not msg.tool_calls:
                self._log("LLM finished tool calls")
                break

            # Append assistant message
            messages.append(msg.model_dump())  # type: ignore[arg-type]

            # Execute each tool call
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = tc.function.arguments
                self._log(f"  → {fn_name}({fn_args[:80]}{'…' if len(fn_args) > 80 else ''})")

                result = call_tool(fn_name, fn_args)
                tool_results.append({"tool": fn_name, "result": result})

                # Collect output paths
                if "scene_path" in result:
                    scene_path = result["scene_path"]
                if "path" in result and str(result["path"]).endswith(".vox"):
                    asset_paths.append(result["path"])
                if "asset_paths" in result:
                    asset_paths.extend(result["asset_paths"])

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result),
                })

        return {
            "mode":         "llm",
            "model":        self.model,
            "scene_path":   scene_path,
            "asset_paths":  list(dict.fromkeys(asset_paths)),  # deduplicate
            "entity_count": len(asset_paths),
            "rounds":       round_n + 1,
            "tool_results": tool_results,
        }

    # ------------------------------------------------------------------
    def run_batch(self, prompts: List[str]) -> List[Dict[str, Any]]:
        """Run the agent on multiple prompts sequentially."""
        return [self.run(p) for p in prompts]
