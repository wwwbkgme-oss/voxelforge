"""
Example 04 — OpenAI function-calling integration
=================================================
Shows how to wire VoxelForge tools into an OpenAI chat completion call
so that GPT-4o (or any compatible model) can directly call VoxelForge
to build game assets.

Prerequisites:
  - pip install openai
  - export OPENAI_API_KEY=sk-...
  - VoxelForge API running: voxelforge api

Run:
    python examples/04_openai_function_calling.py
"""

import os
import json

try:
    import openai
except ImportError:
    print("Install openai: pip install openai")
    raise

from forge.ai.tools import TOOLS, call_tool

client = openai.OpenAI()

USER_MESSAGE = (
    "I need a complete desert sci-fi level with 3 futuristic buildings, "
    "2 mage characters, and some rock and crate props. Seed it with 777."
)

print(f"User: {USER_MESSAGE}\n")

messages = [
    {
        "role": "system",
        "content": (
            "You are a game world builder.  Use the VoxelForge tools to create "
            "the assets the user requests.  Always end by calling build_world or "
            "build_scene to produce a playable scene file."
        ),
    },
    {"role": "user", "content": USER_MESSAGE},
]

# Agentic tool-calling loop
MAX_ROUNDS = 10
for round_n in range(MAX_ROUNDS):
    response = client.chat.completions.create(
        model       = "gpt-4o",
        messages    = messages,
        tools       = TOOLS,
        tool_choice = "auto",
    )

    msg = response.choices[0].message

    if not msg.tool_calls:
        print("\nAssistant:", msg.content)
        break

    messages.append(msg.model_dump())

    for tc in msg.tool_calls:
        fn   = tc.function.name
        args = tc.function.arguments
        print(f"[Tool] {fn}({args[:120]}{'…' if len(args) > 120 else ''})")
        result = call_tool(fn, args)
        print(f"       → {json.dumps(result)[:200]}")

        messages.append({
            "role":         "tool",
            "tool_call_id": tc.id,
            "content":      json.dumps(result),
        })
