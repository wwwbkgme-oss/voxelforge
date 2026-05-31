"""
forge.gamegen
=============
HTML5 game generator and full game asset pipeline for VoxelForge Studio.

Combines patterns from:
  - yashdew3/AI-Game-Generator: text → complete self-contained HTML5 game
  - jamesvovos/ai-game-asset-creator: chained LLM pipeline for storyline →
    NPCs → quests → dialogue trees → items → textures
  - forge.llm_router: automatic free LLM routing

All generation uses free LLMs by default (Groq, Cerebras, Gemini free tier,
OpenRouter free models) — no paid API required.

Usage
-----
>>> from forge.gamegen import HTML5GameGenerator, AssetPipeline

# Generate a complete playable HTML5 game
>>> gen = HTML5GameGenerator()
>>> game = gen.generate("a platform game where a knight collects stars")
>>> print(game.html_path)   # open in any browser — fully playable

# Generate a complete narrative asset set for a VoxelForge game
>>> pipeline = AssetPipeline()
>>> assets = pipeline.run(
...     theme   = "dark ice dungeon",
...     details = "treacherous caves beneath the frozen mountains",
... )
>>> print(assets["dialogue_tree"])   # JSON branching dialogue
>>> print(assets["items"])           # list of items with visual descriptions
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llm_router import LLMRouter, get_router, llm


# ---------------------------------------------------------------------------
# HTML5 Game Generator
# ---------------------------------------------------------------------------

# Game genre templates with specific system guidance
_GENRE_TEMPLATES: Dict[str, str] = {
    "platformer": (
        "Create a side-scrolling platformer. Player moves left/right with "
        "arrow keys or WASD, jumps with Space/Up. Add platforms, collectibles, "
        "and a score counter. Use canvas-based rendering."
    ),
    "puzzle": (
        "Create a grid-based puzzle game. Clicking selects/moves pieces. "
        "Include clear win/loss conditions, move counter, and restart button."
    ),
    "rpg": (
        "Create a top-down RPG exploration game. WASD/arrow keys move the hero. "
        "Include an overworld grid, NPCs with dialogue, items to collect, "
        "and a quest/objective display."
    ),
    "shooter": (
        "Create a top-down or side-scrolling shooter. Player ship/character "
        "moves with WASD/arrows, shoots with Space/click. Spawn enemies with "
        "collision detection, lives, and score display."
    ),
    "arcade": (
        "Create an arcade-style game with simple controls, increasing difficulty, "
        "high score tracking, game over screen, and restart functionality."
    ),
    "adventure": (
        "Create a point-and-click adventure. Display scenes with interactive "
        "elements, inventory system, and branching narrative progression."
    ),
    "dungeon": (
        "Create a dungeon crawler. Top-down grid movement with WASD/arrows. "
        "Include enemies, combat, health bar, treasure chests, and level progression."
    ),
    "educational": (
        "Create an educational game. Clear learning objective, interactive exercises, "
        "immediate feedback, score/progress tracking, kid-friendly design."
    ),
}

_GAME_SYSTEM_PROMPT = """\
You are an expert HTML5 game developer. Generate a COMPLETE, VALID, \
SELF-CONTAINED single HTML file for a playable game.

STRICT REQUIREMENTS:
- Output ONLY raw HTML — no markdown, no backticks, no explanations.
- All CSS inside <style> tags. All JS inside <script> tags.
- No external libraries, CDNs, or asset files.
- Fully playable in any modern browser with zero setup.
- Include on-screen controls display and game instructions.
- Implement proper game loop, collision detection, and win/loss conditions.
- Use requestAnimationFrame for smooth animation.
- Mobile-responsive with touch controls where applicable.
- Nice visual design: gradients, shadows, smooth animations.
- Show score, health/lives, and current objective on screen.

OUTPUT: A single <!DOCTYPE html> file. Nothing else."""


@dataclass
class HTML5Game:
    """Result of HTML5 game generation."""
    title:     str
    genre:     str
    html_path: str          # Path to the .html file
    html:      str          # Raw HTML content
    prompt:    str
    model:     str
    provider:  str
    valid:     bool = True
    issues:    List[str] = field(default_factory=list)

    def open_url(self) -> str:
        """Return a file:// URL for browser opening."""
        return f"file://{os.path.abspath(self.html_path)}"


class HTML5GameGenerator:
    """
    Generates complete, immediately-playable HTML5 games from text prompts.

    Uses free LLMs (Groq/Gemini/Cerebras/OpenRouter) to generate
    single-file HTML games with inline CSS and JS.

    Parameters
    ----------
    output_dir : str
        Where to save generated .html files.
    router : LLMRouter, optional
        Custom LLM router. Defaults to module-level router (auto-selects free provider).
    """

    def __init__(
        self,
        output_dir: str             = "generated_assets/games/html",
        router:     Optional[LLMRouter] = None,
    ):
        self.output_dir = output_dir
        self.router     = router or get_router()
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    def generate(
        self,
        prompt:      str,
        genre:       str           = "auto",
        title:       str           = "",
        name:        str           = "game",
        temperature: float         = 0.7,
        max_tokens:  int           = 8192,
    ) -> HTML5Game:
        """
        Generate a complete, playable HTML5 game from a text description.

        Parameters
        ----------
        prompt : str
            Game description (e.g. "a dungeon crawler where a knight fights skeletons").
        genre : str
            Genre hint: platformer|puzzle|rpg|shooter|arcade|adventure|dungeon|
            educational|auto. "auto" detects from prompt.
        title : str
            Game title. Auto-generated from prompt if empty.
        name : str
            Base filename (without .html).

        Returns
        -------
        HTML5Game
        """
        # Auto-detect genre
        if genre == "auto":
            genre = self._detect_genre(prompt)

        if not title:
            title = self._make_title(prompt)

        slug     = re.sub(r"[^\w]", "_", name.lower())[:30]
        filepath = os.path.join(self.output_dir, f"{slug}.html")

        # Build the full prompt
        genre_hint = _GENRE_TEMPLATES.get(genre, "")
        full_prompt = self._build_prompt(prompt, title, genre, genre_hint)

        # Call LLM
        resp = self.router.chat(
            prompt      = full_prompt,
            system      = _GAME_SYSTEM_PROMPT,
            task        = "code",
            temperature = temperature,
            max_tokens  = max_tokens,
        )

        html  = self._clean_output(resp.text if resp.ok else "")
        valid, issues = self._validate_html(html)

        # If validation failed and LLM gave us something, retry once with stricter prompt
        if not valid and resp.ok:
            retry_prompt = (
                f"{full_prompt}\n\n"
                "CRITICAL: The previous response was incomplete. "
                "You MUST return a COMPLETE HTML file from <!DOCTYPE html> to </html>. "
                "Every tag must be properly closed. Include full game logic."
            )
            resp2 = self.router.chat(
                prompt      = retry_prompt,
                system      = _GAME_SYSTEM_PROMPT,
                task        = "code",
                temperature = 0.5,
                max_tokens  = max_tokens,
            )
            if resp2.ok:
                html2 = self._clean_output(resp2.text)
                valid2, issues2 = self._validate_html(html2)
                if valid2 or len(html2) > len(html):
                    html, valid, issues = html2, valid2, issues2

        # If all else fails, use the procedural fallback game
        if not html or len(html) < 500:
            html  = self._fallback_game(title, genre, prompt)
            valid = True
            issues = []
            resp.provider = "procedural"
            resp.model    = "template"

        # Save
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        return HTML5Game(
            title     = title,
            genre     = genre,
            html_path = filepath,
            html      = html,
            prompt    = prompt,
            model     = resp.model,
            provider  = resp.provider,
            valid     = valid,
            issues    = issues,
        )

    # ------------------------------------------------------------------
    def generate_batch(
        self,
        prompts: List[str],
        genre:   str = "auto",
    ) -> List[HTML5Game]:
        """Generate multiple games from a list of prompts."""
        return [
            self.generate(p, genre=genre, name=f"game_{i:02d}")
            for i, p in enumerate(prompts)
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _detect_genre(self, prompt: str) -> str:
        p = prompt.lower()
        for genre, keywords in {
            "platformer": ["platform", "jump", "side-scroll", "run and jump"],
            "dungeon":    ["dungeon", "crawler", "dungeon crawler", "skeleton", "monster"],
            "rpg":        ["rpg", "quest", "npc", "dialogue", "overworld"],
            "shooter":    ["shoot", "bullet", "enemy", "laser", "space"],
            "puzzle":     ["puzzle", "block", "match", "solve", "logic"],
            "arcade":     ["arcade", "score", "avoid", "dodge", "collect"],
            "adventure":  ["adventure", "explore", "click", "story"],
            "educational":["learn", "math", "quiz", "education", "spell"],
        }.items():
            if any(k in p for k in keywords):
                return genre
        return "arcade"

    def _make_title(self, prompt: str) -> str:
        words = [w.capitalize() for w in re.sub(r"[^\w\s]", "", prompt).split()[:4]]
        return " ".join(words) or "VoxelForge Game"

    def _build_prompt(
        self, prompt: str, title: str, genre: str, genre_hint: str
    ) -> str:
        return (
            f"GAME TITLE: {title}\n"
            f"GENRE: {genre}\n"
            f"DESCRIPTION: {prompt}\n\n"
            f"GENRE REQUIREMENTS:\n{genre_hint}\n\n"
            "Generate the complete HTML5 game file now."
        )

    def _clean_output(self, text: str) -> str:
        """Strip markdown fences and extract the HTML content."""
        text = re.sub(r"```html\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```\s*",     "", text)
        text = text.strip()
        # Find the actual HTML block
        start = text.lower().find("<!doctype")
        if start == -1:
            start = text.lower().find("<html")
        if start > 0:
            text = text[start:]
        return text

    def _validate_html(self, html: str) -> tuple[bool, List[str]]:
        """Quick sanity checks on the generated HTML."""
        issues = []
        h = html.lower()
        if "<!doctype" not in h:       issues.append("Missing DOCTYPE")
        if "<html"     not in h:       issues.append("Missing <html> tag")
        if "</html>"   not in h:       issues.append("Missing </html> closing tag")
        if "<script"   not in h:       issues.append("No JavaScript found")
        if "</script>" not in h:       issues.append("Unclosed <script> tag")
        if len(html)   < 500:          issues.append(f"Output too short ({len(html)} chars)")
        return (len(issues) == 0), issues

    def _fallback_game(self, title: str, genre: str, description: str) -> str:
        """
        Minimal procedural HTML5 game — always works, no LLM needed.
        A simple canvas game appropriate for the requested genre.
        """
        escaped_title = title.replace('"', '&quot;')
        escaped_desc  = description[:80].replace('<', '&lt;').replace('>', '&gt;')
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escaped_title}</title>
<style>
  body {{ margin:0; background:#0f1117; display:flex; flex-direction:column;
          align-items:center; justify-content:center; height:100vh;
          font-family:'Segoe UI',sans-serif; color:#e2e8f0; }}
  canvas {{ border:2px solid #7c3aed; border-radius:8px;
            box-shadow:0 0 30px rgba(124,58,237,.4); }}
  #ui {{ display:flex; gap:2rem; margin-bottom:.75rem; font-size:.9rem; color:#a5b4fc; }}
  #info {{ margin-top:.5rem; font-size:.75rem; color:#64748b; }}
</style>
</head>
<body>
<div id="ui">
  <span>❤️ HP: <b id="hp">3</b></span>
  <span>⭐ Score: <b id="score">0</b></span>
  <span>🎯 {escaped_title}</span>
</div>
<canvas id="c" width="480" height="360"></canvas>
<div id="info">{escaped_desc} | WASD/Arrows=move  Space=action  R=restart</div>
<script>
const C=document.getElementById('c'), ctx=C.getContext('2d');
const $hp=document.getElementById('hp'), $sc=document.getElementById('score');
const W=C.width, H=C.height;
let score=0, hp=3, frame=0, gameOver=false;

const pal = ['#7c3aed','#10b981','#f59e0b','#ef4444','#3b82f6','#ec4899'];
const keys={{}};
document.addEventListener('keydown',e=>keys[e.key]=1);
document.addEventListener('keyup',  e=>keys[e.key]=0);

// Player
const p={{x:W/2-16,y:H/2-16,w:32,h:32,vx:0,vy:0,spd:3,color:'#7c3aed'}};

// Collectibles
let items=[],enemies=[];
function spawn(){{
  for(let i=0;i<8;i++) items.push({{
    x:Math.random()*(W-20)+10, y:Math.random()*(H-20)+10,
    r:8, color:pal[Math.floor(Math.random()*pal.length)], pulse:Math.random()*Math.PI*2
  }});
  for(let i=0;i<3;i++) enemies.push({{
    x:Math.random()<.5?0:W, y:Math.random()*H,
    vx:(Math.random()-.5)*2, vy:(Math.random()-.5)*2,
    r:12, color:'#ef4444'
  }});
}}
spawn();

function restart(){{
  score=0; hp=3; frame=0; gameOver=false;
  p.x=W/2-16; p.y=H/2-16; p.vx=0; p.vy=0;
  items=[]; enemies=[]; spawn();
  $hp.textContent=hp; $sc.textContent=score;
}}

document.addEventListener('keydown', e=>{{ if(e.key==='r'||e.key==='R') restart(); }});

function update(){{
  if(gameOver) return;
  frame++;

  // Input
  p.vx=(keys['ArrowRight']||keys['d']||keys['D']?p.spd:0)
      -(keys['ArrowLeft'] ||keys['a']||keys['A']?p.spd:0);
  p.vy=(keys['ArrowDown'] ||keys['s']||keys['S']?p.spd:0)
      -(keys['ArrowUp']   ||keys['w']||keys['W']?p.spd:0);
  p.x=Math.max(0,Math.min(W-p.w, p.x+p.vx));
  p.y=Math.max(0,Math.min(H-p.h, p.y+p.vy));

  // Collect items
  items=items.filter(it=>{{
    it.pulse+=.08;
    const dx=p.x+p.w/2-it.x, dy=p.y+p.h/2-it.y;
    if(dx*dx+dy*dy < (p.w/2+it.r)**2){{
      score+=10; $sc.textContent=score;
      return false;
    }}
    return true;
  }});
  if(items.length===0) spawn();

  // Move + collide enemies
  enemies.forEach(en=>{{
    en.x+=en.vx; en.y+=en.vy;
    if(en.x<0||en.x>W) en.vx*=-1;
    if(en.y<0||en.y>H) en.vy*=-1;
    const dx=p.x+p.w/2-en.x, dy=p.y+p.h/2-en.y;
    if(dx*dx+dy*dy < (p.w/2+en.r)**2 && frame%30===0){{
      hp--; $hp.textContent=hp;
      if(hp<=0) gameOver=true;
    }}
  }});
}}

function draw(){{
  ctx.fillStyle='#0f1117'; ctx.fillRect(0,0,W,H);

  // Grid
  ctx.strokeStyle='rgba(124,58,237,.12)'; ctx.lineWidth=1;
  for(let x=0;x<W;x+=40) {{ ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }}
  for(let y=0;y<H;y+=40) {{ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }}

  // Items
  items.forEach(it=>{{
    const r=it.r+Math.sin(it.pulse)*2;
    ctx.beginPath(); ctx.arc(it.x,it.y,r,0,Math.PI*2);
    ctx.fillStyle=it.color+'88'; ctx.fill();
    ctx.strokeStyle=it.color; ctx.lineWidth=2; ctx.stroke();
  }});

  // Enemies
  enemies.forEach(en=>{{
    ctx.beginPath(); ctx.arc(en.x,en.y,en.r,0,Math.PI*2);
    ctx.fillStyle='#ef444488'; ctx.fill();
    ctx.strokeStyle='#ef4444'; ctx.lineWidth=2; ctx.stroke();
    // X eyes
    ctx.fillStyle='#fff'; ctx.font='10px sans-serif';
    ctx.fillText('✕',en.x-4,en.y+3);
  }});

  // Player
  ctx.fillStyle=p.color+'cc';
  ctx.beginPath();
  ctx.roundRect(p.x,p.y,p.w,p.h,6);
  ctx.fill();
  ctx.strokeStyle='#a78bfa'; ctx.lineWidth=2; ctx.stroke();
  // Face
  ctx.fillStyle='#fff'; ctx.font='16px sans-serif';
  ctx.fillText('😤',p.x+7,p.y+22);

  if(gameOver){{
    ctx.fillStyle='rgba(0,0,0,.7)'; ctx.fillRect(0,0,W,H);
    ctx.fillStyle='#ef4444'; ctx.font='bold 36px sans-serif';
    ctx.textAlign='center';
    ctx.fillText('GAME OVER',W/2,H/2-20);
    ctx.fillStyle='#e2e8f0'; ctx.font='18px sans-serif';
    ctx.fillText('Score: '+score,W/2,H/2+20);
    ctx.fillStyle='#a5b4fc'; ctx.font='14px sans-serif';
    ctx.fillText('Press R to restart',W/2,H/2+50);
    ctx.textAlign='left';
  }}
}}

function loop(){{ update(); draw(); requestAnimationFrame(loop); }}
loop();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Asset Pipeline — chained LLM generation
# ---------------------------------------------------------------------------

@dataclass
class GameAssetPack:
    """Complete set of narrative and visual game assets."""
    theme:           str
    storyline:       str
    characters:      List[Dict[str, str]]    # [{name, description, role}]
    backstories:     str
    quests:          List[Dict[str, str]]    # [{title, description, objective}]
    dialogue_tree:   Dict[str, Any]          # JSON branching dialogue
    items:           List[Dict[str, str]]    # [{name, visual_description}]
    world_elements:  List[str]               # terrain features, locations, etc.
    lua_scripts:     Dict[str, str]          # {script_name: lua_code}
    output_dir:      str
    model:           str = "unknown"
    provider:        str = "unknown"

    def save(self) -> Dict[str, str]:
        """Save all assets to the output directory. Returns {name: path}."""
        os.makedirs(self.output_dir, exist_ok=True)
        paths = {}

        def _write(name: str, content: str, ext: str = "md") -> str:
            p = os.path.join(self.output_dir, f"{name}.{ext}")
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            paths[name] = p
            return p

        _write("storyline",      f"# Storyline\n\n{self.storyline}")
        _write("characters",     _format_characters(self.characters))
        _write("backstories",    f"# Character Backstories\n\n{self.backstories}")
        _write("quests",         _format_quests(self.quests))
        _write("dialogue_tree",  json.dumps(self.dialogue_tree, indent=2), "json")
        _write("items",          _format_items(self.items))
        _write("world_elements", "\n".join(f"- {e}" for e in self.world_elements))

        for script_name, code in self.lua_scripts.items():
            p = os.path.join(self.output_dir, f"{script_name}.lua")
            with open(p, "w", encoding="utf-8") as f:
                f.write(code)
            paths[script_name] = p

        return paths


class AssetPipeline:
    """
    Full narrative + visual game asset pipeline.

    Chains LLM calls to produce a coherent set of game assets:
    storyline → characters → backstories → quests → dialogue trees →
    items (with visual descriptions) → world elements → Lua scripts.

    All generation uses the free LLM router — works with Groq, Gemini,
    Cerebras, etc. with zero paid API cost.

    Parameters
    ----------
    output_dir : str
        Base directory for saving asset packs.
    router : LLMRouter, optional
    """

    def __init__(
        self,
        output_dir: str             = "generated_assets/narrative_packs",
        router:     Optional[LLMRouter] = None,
    ):
        self.output_dir = output_dir
        self.router     = router or get_router()
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    def run(
        self,
        theme:   str,
        details: str = "",
        genre:   str = "dungeon",
        seed:    int = 0,
    ) -> GameAssetPack:
        """
        Run the full asset generation pipeline.

        Parameters
        ----------
        theme : str
            Core game theme (e.g. "dark ice dungeon").
        details : str
            Additional world/scene details.
        genre : str
            Game genre — adjusts tone and content.

        Returns
        -------
        GameAssetPack
        """
        import re as _re, random
        rng  = random.Random(seed + hash(theme) % 100000)
        slug = _re.sub(r"[^\w]", "_", theme.lower())[:20]
        pack_dir = os.path.join(self.output_dir, slug)
        os.makedirs(pack_dir, exist_ok=True)

        print(f"[AssetPipeline] Generating: {theme!r}")
        model_used = "unknown"
        provider   = "unknown"

        # Step 1 — Storyline
        print("[AssetPipeline] Step 1/7: Storyline…")
        storyline, model_used, provider = self._call(
            f"Create a short compelling storyline for a {genre} game set in {theme}. "
            f"{'Additional context: ' + details if details else ''} "
            "Keep it to 3-4 sentences. Be vivid and atmospheric.",
            task="creative",
        )

        # Step 2 — Characters
        print("[AssetPipeline] Step 2/7: Characters…")
        chars_raw, *_ = self._call(
            f"Based on this game storyline: {storyline}\n\n"
            "Create exactly 2 NPC characters. For each character provide:\n"
            "- Name\n- Class/Role\n- 1-2 sentence description\n\n"
            "Format as JSON array: [{\"name\":\"...\",\"role\":\"...\",\"description\":\"...\"}]",
            task="creative",
        )
        characters = _parse_json_list(chars_raw, [
            {"name": "Elara", "role": "Village Elder", "description": "A wise old scholar guarding ancient secrets."},
            {"name": "Kron",  "role": "Enemy Commander", "description": "A ruthless warrior driven by dark ambition."},
        ])

        # Step 3 — Backstories
        print("[AssetPipeline] Step 3/7: Backstories…")
        backstories, *_ = self._call(
            f"Storyline: {storyline}\n\n"
            f"Characters: {json.dumps(characters, indent=2)}\n\n"
            "Write a backstory for each character (2-3 sentences each). "
            "Consider their motivations, past, and relationship to the world.",
            task="creative",
        )

        # Step 4 — Quests
        print("[AssetPipeline] Step 4/7: Quests…")
        quests_raw, *_ = self._call(
            f"Characters with backstories:\n{backstories}\n\n"
            f"World storyline: {storyline}\n\n"
            "Create one quest per character. Format as JSON array:\n"
            "[{\"title\":\"...\",\"giver\":\"...\","
            "\"description\":\"...\",\"objective\":\"...\","
            "\"reward\":\"...\"}]",
            task="creative",
        )
        quests = _parse_json_list(quests_raw, [
            {"title": "The Lost Relic",
             "giver": characters[0]["name"] if characters else "Elder",
             "description": "Retrieve a powerful artifact from the dungeon depths.",
             "objective": "Find and return the Crystal Shard",
             "reward": "Ancient spellbook"},
        ])

        # Step 5 — Dialogue Trees
        print("[AssetPipeline] Step 5/7: Dialogue trees…")
        dialogue_raw, *_ = self._call(
            f"Quests: {json.dumps(quests, indent=2)}\n\n"
            f"Character backstories:\n{backstories}\n\n"
            "Create branching dialogue trees for NPCs to guide the player. "
            "Output valid JSON: {\"characters\": [{\"name\":\"...\","
            "\"opening\":\"...\",\"branches\":[{\"player\":\"...\","
            "\"npc\":\"...\",\"leads_to\":\"...\"}]}]}",
            task="creative",
        )
        dialogue_tree = _parse_json_obj(dialogue_raw, {
            "characters": [
                {"name": c["name"],
                 "opening": f"Greetings, traveller. I am {c['name']}.",
                 "branches": [
                     {"player": "Tell me about your quest.",
                      "npc": "I need your help with an urgent matter.",
                      "leads_to": "quest_offer"},
                     {"player": "Farewell.",
                      "npc": "Safe travels.",
                      "leads_to": "end"},
                 ]}
                for c in characters
            ]
        })

        # Step 6 — Items
        print("[AssetPipeline] Step 6/7: Items…")
        items_raw, *_ = self._call(
            f"Given these quests: {json.dumps([q.get('title','') for q in quests])}\n"
            f"And this world: {theme}\n\n"
            "Generate 4 unique game items needed for these quests. "
            "For each, give a vivid visual description suitable for a pixel art artist. "
            "Format as JSON array: [{\"name\":\"...\",\"type\":\"...\","
            "\"visual_description\":\"...\",\"effect\":\"...\"}]",
            task="creative",
        )
        items = _parse_json_list(items_raw, [
            {"name": "Crystal Shard",
             "type": "quest_item",
             "visual_description": "A glowing blue crystal with jagged edges, pulsing with cold energy",
             "effect": "Unlocks the ice gate"},
            {"name": "Health Potion",
             "type": "consumable",
             "visual_description": "A small red vial filled with sparkling liquid",
             "effect": "Restores 25 HP"},
        ])

        # Step 7 — World elements
        print("[AssetPipeline] Step 7/7: World elements…")
        world_raw, *_ = self._call(
            f"For a {genre} game set in {theme}:\n"
            f"Details: {details or 'none'}\n\n"
            "List 8 unique world/environment elements (locations, terrain features, "
            "atmospheric details). One per line, no numbering.",
            task="creative",
        )
        world_elements = [line.strip("•- ").strip()
                          for line in world_raw.splitlines()
                          if line.strip() and len(line.strip()) > 3][:8]
        if not world_elements:
            world_elements = [
                "Frozen stone corridors lit by blue torches",
                "Ice stalactites hanging from the vaulted ceiling",
                "A frozen underground river cutting through the dungeon",
            ]

        # Step 8 — Lua scripts for VoxelForge
        lua_scripts = self._generate_lua_scripts(
            theme, characters, quests, items, genre
        )

        pack = GameAssetPack(
            theme          = theme,
            storyline      = storyline,
            characters     = characters,
            backstories    = backstories,
            quests         = quests,
            dialogue_tree  = dialogue_tree,
            items          = items,
            world_elements = world_elements,
            lua_scripts    = lua_scripts,
            output_dir     = pack_dir,
            model          = model_used,
            provider       = provider,
        )

        # Auto-save
        paths = pack.save()
        print(f"[AssetPipeline] Saved {len(paths)} files to {pack_dir}")
        return pack

    # ------------------------------------------------------------------
    def _call(
        self, prompt: str, task: str = "creative"
    ) -> tuple[str, str, str]:
        """LLM call — returns (text, model, provider)."""
        resp = self.router.chat(prompt, task=task, max_tokens=1500, temperature=0.8)
        return (resp.text or "", resp.model, resp.provider)

    def _generate_lua_scripts(
        self,
        theme:      str,
        characters: List[Dict[str, str]],
        quests:     List[Dict[str, str]],
        items:      List[Dict[str, str]],
        genre:      str,
    ) -> Dict[str, str]:
        """Generate VoxelForge-compatible Lua scripts for the narrative content."""
        scripts: Dict[str, str] = {}

        # NPC dialogue script
        for char in characters[:2]:
            name = char.get("name", "NPC")
            slug_name = re.sub(r"[^\w]", "_", name.lower())
            scripts[f"npc_{slug_name}"] = _lua_npc_script(name, char, theme)

        # Quest trigger script
        for i, quest in enumerate(quests[:2]):
            slug_q = re.sub(r"[^\w]", "_", quest.get("title", f"quest_{i}").lower())[:20]
            scripts[f"quest_{slug_q}"] = _lua_quest_script(quest, items)

        # Item pickup script
        if items:
            scripts["item_pickup"] = _lua_item_pickup_script(items)

        return scripts


# ---------------------------------------------------------------------------
# Lua script builders
# ---------------------------------------------------------------------------

def _lua_npc_script(name: str, char: Dict, theme: str) -> str:
    role = char.get("role", "NPC")
    desc = char.get("description", "")
    return (
        "--[[\n"
        "  VoxelForge NPC Script — " + name + "\n"
        "  Role: " + role + "\n"
        "  World: " + theme + "\n"
        "--]]\n\n"
        'local NPC_NAME    = "' + name + '"\n'
        'local NPC_ROLE    = "' + role + '"\n'
        "local talked      = false\n"
        "local interact_dist = 3.0\n\n"
        "function Start()\n"
        '    print("[NPC] ' + name + ' ready")\n'
        "end\n\n"
        "function Update()\n"
        '    local player = ECS.FindEntityByName("player")\n'
        "    if not player then return end\n"
        "    local np = Transform.GetPosition(self)\n"
        "    local pp = Transform.GetPosition(player)\n"
        "    local dx, dy = np.x - pp.x, np.y - pp.y\n"
        "    local dist = math.sqrt(dx*dx + dy*dy)\n"
        '    if dist < interact_dist and Input.GetKeyDown("E") and not talked then\n'
        "        talked = true\n"
        '        UI.DrawText("' + name + ': ' + (desc[:60] if desc else "Greetings, traveller.") + '...", 20, 120, 1,0.9,0.5,1)\n'
        '        print("[NPC] ' + name + ' spoken to")\n'
        "    end\n"
        "end\n"
    )


def _lua_quest_script(quest: Dict, items: List[Dict]) -> str:
    title     = quest.get("title", "Quest")
    objective = quest.get("objective", "Complete the objective")
    reward    = quest.get("reward", "Item")
    item_name = items[0].get("name", "item") if items else "item"
    return (
        "--[[\n"
        "  VoxelForge Quest Script — " + title + "\n"
        "  Objective: " + objective + "\n"
        "--]]\n\n"
        "local completed  = false\n"
        "local item_found = false\n\n"
        "function Start()\n"
        '    UI.DrawText("Quest: ' + title + '", 20, 20, 1,0.8,0,1)\n'
        '    UI.DrawText("Objective: ' + objective + '", 20, 44, 0.9,0.9,0.9,1)\n'
        "end\n\n"
        "function Update()\n"
        "    if completed then return end\n"
        '    local items = ECS.FindEntitiesByNameContaining("' + item_name + '")\n'
        "    if items and #items == 0 and item_found then\n"
        "        completed = true\n"
        '        UI.DrawText("Quest Complete! Reward: ' + reward + '", 20, 20, 0,1,0.5,1)\n'
        '        print("[Quest] ' + title + ' completed!")\n'
        "    end\n"
        "    if items and #items > 0 then\n"
        '        local player = ECS.FindEntityByName("player")\n'
        "        if not player then return end\n"
        "        local pp = Transform.GetPosition(player)\n"
        "        local ip = Transform.GetPosition(items[1])\n"
        "        local dx, dy = pp.x-ip.x, pp.y-ip.y\n"
        '        if dx*dx+dy*dy < 9 and Input.GetKeyDown("E") then\n'
        "            item_found = true\n"
        "            ECS.DestroyEntity(items[1])\n"
        '            UI.DrawText("Found: ' + item_name + '!", 20, 70, 1,1,0,1)\n'
        "        end\n"
        "    end\n"
        "end\n"
    )


def _lua_item_pickup_script(items: List[Dict]) -> str:
    lines = [
        "--[[\n"
        "  VoxelForge Item Pickup System\n"
        "--]]\n\n"
        "local items_collected = {}\n\n"
        "function Start()\n"
        '    print("[Items] Pickup system active")\n'
        "end\n\n"
        "function Update()\n"
        '    local player = ECS.FindEntityByName("player")\n'
        "    if not player then return end\n"
        "    local pp = Transform.GetPosition(player)\n"
    ]
    for item in items[:4]:
        nm = item.get("name", "item")
        eff = item.get("effect", "")
        lines.append(
            '    local ' + re.sub(r"[^\w]","_",nm.lower()) +
            ' = ECS.FindEntitiesByNameContaining("' + nm + '")\n'
            '    if ' + re.sub(r"[^\w]","_",nm.lower()) + ' then\n'
            '        for _,e in ipairs(' + re.sub(r"[^\w]","_",nm.lower()) + ') do\n'
            '            local ip = Transform.GetPosition(e)\n'
            '            local d2 = (pp.x-ip.x)^2+(pp.y-ip.y)^2\n'
            '            if d2 < 9 then\n'
            '                ECS.DestroyEntity(e)\n'
            '                items_collected["' + nm + '"] = true\n'
            '                UI.DrawText("' + nm + ': ' + eff[:40] + '", 20, 90, 1,1,0,1)\n'
            '            end\n'
            '        end\n'
            '    end\n'
        )
    lines.append("end\n")
    return "".join(lines)


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

def _parse_json_list(text: str, default: list) -> list:
    try:
        start = text.find("[")
        end   = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except Exception:
        pass
    return default


def _parse_json_obj(text: str, default: dict) -> dict:
    try:
        start = text.find("{")
        end   = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except Exception:
        pass
    return default


# ---------------------------------------------------------------------------
# Markdown formatters
# ---------------------------------------------------------------------------

def _format_characters(chars: List[Dict]) -> str:
    lines = ["# Characters\n"]
    for c in chars:
        lines.append(f"## {c.get('name', 'Unknown')}")
        lines.append(f"**Role**: {c.get('role', '')}")
        lines.append(f"\n{c.get('description', '')}\n")
    return "\n".join(lines)


def _format_quests(quests: List[Dict]) -> str:
    lines = ["# Quests\n"]
    for q in quests:
        lines.append(f"## {q.get('title', 'Unnamed Quest')}")
        lines.append(f"**Giver**: {q.get('giver', '')}")
        lines.append(f"**Objective**: {q.get('objective', '')}")
        lines.append(f"**Reward**: {q.get('reward', '')}")
        lines.append(f"\n{q.get('description', '')}\n")
    return "\n".join(lines)


def _format_items(items: List[Dict]) -> str:
    lines = ["# Game Items\n"]
    for it in items:
        lines.append(f"## {it.get('name', 'Item')}")
        lines.append(f"**Type**: {it.get('type', '')}")
        lines.append(f"**Effect**: {it.get('effect', '')}")
        lines.append(f"\n*Visual*: {it.get('visual_description', '')}\n")
    return "\n".join(lines)
