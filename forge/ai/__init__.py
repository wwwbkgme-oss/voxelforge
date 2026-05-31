"""
forge.ai
========
AI integration layer for VoxelForge.

Provides:
    TOOLS           — OpenAI-compatible function-calling tool definitions
    VoxelForgeAgent — Autonomous game-creation agent
"""

from .tools import TOOLS, call_tool  # noqa: F401
from .agent import VoxelForgeAgent    # noqa: F401
