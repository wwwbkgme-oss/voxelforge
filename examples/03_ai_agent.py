"""
Example 03 — Autonomous AI agent builds a complete game world
=============================================================
The agent takes a single text prompt and autonomously calls
VoxelForge tools to generate terrain, assets, and a full scene.

Requirements:
  1. VoxelForge API server must be running:
       voxelforge api
  2. (Optional) Set OPENAI_API_KEY for LLM mode.
     Without it, the agent falls back to keyword-based direct mode.

Run:
    python examples/03_ai_agent.py
    python examples/03_ai_agent.py "a snowy arctic research base, 4 sci-fi buildings"
"""

import os
import sys
import json

# Allow running from project root without install
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge.ai.agent import VoxelForgeAgent

# Default prompt if none provided on command line
DEFAULT_PROMPT = (
    "A medieval fantasy village in a lush grassland with 4 buildings, "
    "a warrior hero, a mage NPC, oak trees, and a treasure chest"
)

prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_PROMPT

print(f"\n{'='*60}")
print("VoxelForge Autonomous Agent")
print(f"{'='*60}")
print(f"Prompt: {prompt}")
print(f"{'='*60}\n")

# Use direct mode if no API key set (no LLM needed)
use_direct = not os.environ.get("OPENAI_API_KEY")
if use_direct:
    print("No OPENAI_API_KEY found — using direct keyword-parser mode\n")

agent = VoxelForgeAgent(
    direct_mode=use_direct,
    verbose=True,
)

result = agent.run(prompt)

print(f"\n{'='*60}")
print("Generation complete!")
print(f"{'='*60}")
print(f"Scene:    {result.get('scene_path', 'N/A')}")
print(f"Assets:   {len(result.get('asset_paths', []))} files")
print(f"Entities: {result.get('entity_count', 0)}")
print(f"Time:     {result.get('elapsed_seconds', 0):.1f}s")

if result.get("scene_path"):
    print(f"\nPlay your world:")
    print(f"  cd engine && ./voxelforge --scene ../{result['scene_path']}")
    print(f"\nHeadless screenshot:")
    print(f"  cd engine && ./voxelforge --headless --screenshot ../preview "
          f"--scene ../{result['scene_path']}")
