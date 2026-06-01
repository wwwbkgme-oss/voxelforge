"""
forge.narrative
===============
LLM-native interactive narrative engine for VoxelForge games.

Inspired by ackness/ai-gamestudio — implements:
  - Dual-model architecture: narrative LLM + mechanics plugin agent
  - Plugin system: combat, inventory, social, memory, image, guide
  - SQLite persistence for game state, characters, events, log
  - Block-based structured output (text, choices, combat, item, image)
  - Memory compression for long sessions
  - LiteLLM-compatible (works with any OpenAI-compatible API)

Usage
-----
>>> from forge.narrative import NarrativeEngine, GameSession
>>> engine = NarrativeEngine(
...     llm_model  = "gpt-4o-mini",
...     llm_api_key= os.environ["OPENAI_API_KEY"],
... )
>>> session = engine.start_session(
...     world_file = "design/worlds/crystal_dungeon.md",
...     player_name= "Hero",
...     genre      = "dungeon",
... )
>>> response = engine.send_message(session.id, "I look around the room")
>>> for block in response.blocks:
...     print(block.type, block.data)

Environment
-----------
    OPENAI_API_KEY     OpenAI / OpenRouter API key
    LLM_API_KEY        Alternative key name
    LLM_API_BASE       Custom endpoint (for OpenRouter, Ollama, etc.)
    LLM_MODEL          Model name override
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Block types (structured narrative output)
# ---------------------------------------------------------------------------

BLOCK_TYPES = {
    "narrative":  "Story text / scene description",
    "dialogue":   "Character speech",
    "choices":    "Player action options",
    "combat":     "Combat round result",
    "item":       "Item found / used",
    "image":      "Scene image trigger",
    "notification":"System notification",
    "game_over":  "Win or lose condition met",
    "stats":      "Character stats update",
}


@dataclass
class Block:
    type: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "data": self.data}


@dataclass
class NarrativeResponse:
    session_id: str
    turn_id:    str
    blocks:     List[Block]
    raw_text:   str = ""
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":  self.session_id,
            "turn_id":     self.turn_id,
            "blocks":      [b.to_dict() for b in self.blocks],
            "tokens_used": self.tokens_used,
        }

    def text(self) -> str:
        """Extract all narrative/dialogue text."""
        parts = []
        for b in self.blocks:
            if b.type in ("narrative", "dialogue"):
                parts.append(b.data.get("text", ""))
        return "\n\n".join(p for p in parts if p)

    def choices(self) -> List[str]:
        """Extract player choices."""
        for b in self.blocks:
            if b.type == "choices":
                return b.data.get("options", [])
        return []


# ---------------------------------------------------------------------------
# Game session
# ---------------------------------------------------------------------------

@dataclass
class GameSession:
    id:           str
    player_name:  str
    world:        str
    genre:        str
    created_at:   str
    updated_at:   str
    turn_count:   int = 0
    hp:           int = 100
    max_hp:       int = 100
    gold:         int = 0
    score:        int = 0
    inventory:    List[str] = field(default_factory=list)
    status:       str = "active"   # active | paused | ended


# ---------------------------------------------------------------------------
# Plugin system
# ---------------------------------------------------------------------------

class PluginBase:
    """Base class for narrative engine plugins."""
    name: str = "base"

    def on_session_start(self, session: GameSession) -> List[Block]:
        return []

    def process(self, block_data: Dict[str, Any], session: GameSession,
                db: "GameStateDB") -> List[Block]:
        return []

    def on_player_message(self, message: str, session: GameSession) -> Optional[str]:
        """Pre-process player message. Return modified version or None to pass through."""
        return None


class CombatPlugin(PluginBase):
    """
    Resolves combat encounters with dice rolls and HP tracking.
    Triggered when the narrative LLM emits a combat block.
    """
    name = "combat"

    def process(self, data: Dict[str, Any], session: GameSession,
                db: "GameStateDB") -> List[Block]:
        import random
        enemy    = data.get("enemy", "enemy")
        atk      = data.get("player_attack", random.randint(5, 20))
        def_     = data.get("enemy_defense", random.randint(1, 10))
        dmg_to_enemy = max(0, atk - def_)
        enemy_hp     = data.get("enemy_hp", 30) - dmg_to_enemy
        dmg_to_player = max(0, random.randint(3, 15) - random.randint(0, 5))
        session.hp = max(0, session.hp - dmg_to_player)

        result_text = (
            f"⚔️ You strike {enemy} for {dmg_to_enemy} damage! "
            f"They counter for {dmg_to_player}. "
            f"Your HP: {session.hp}/{session.max_hp}. "
            f"{enemy.title()} HP: {max(0, enemy_hp)}."
        )
        blocks = [Block("combat", {
            "enemy":          enemy,
            "damage_dealt":   dmg_to_enemy,
            "damage_taken":   dmg_to_player,
            "player_hp":      session.hp,
            "enemy_hp":       max(0, enemy_hp),
            "result":         result_text,
        })]

        if session.hp <= 0:
            blocks.append(Block("game_over", {"won": False, "message": "You have fallen..."}))
        elif enemy_hp <= 0:
            score_gain = 10 + dmg_to_enemy
            session.score += score_gain
            blocks.append(Block("notification", {
                "level": "success",
                "title": f"{enemy.title()} defeated!",
                "content": f"+{score_gain} score",
            }))
        return blocks


class InventoryPlugin(PluginBase):
    """Manages player inventory — add, remove, list items."""
    name = "inventory"

    def process(self, data: Dict[str, Any], session: GameSession,
                db: "GameStateDB") -> List[Block]:
        action = data.get("action", "add")
        item   = data.get("item", "unknown item")
        blocks = []

        if action == "add":
            session.inventory.append(item)
            blocks.append(Block("item", {
                "action": "acquired",
                "item":   item,
                "total":  len(session.inventory),
            }))
        elif action == "remove":
            if item in session.inventory:
                session.inventory.remove(item)
                blocks.append(Block("item", {
                    "action": "used",
                    "item":   item,
                    "total":  len(session.inventory),
                }))
        elif action == "list":
            blocks.append(Block("stats", {
                "inventory": session.inventory,
                "count":     len(session.inventory),
            }))

        return blocks


class MemoryPlugin(PluginBase):
    """
    Compresses long conversation history to keep context within LLM limits.
    Summarises older turns using the LLM itself.
    """
    name = "memory"
    COMPRESS_THRESHOLD = 20   # compress when history exceeds this many turns

    def compress_history(
        self,
        history: List[Dict[str, str]],
        llm_fn,
    ) -> List[Dict[str, str]]:
        """
        If history is longer than threshold, summarise older half with LLM.
        Returns compressed history.
        """
        if len(history) <= self.COMPRESS_THRESHOLD:
            return history

        to_compress = history[: len(history) // 2]
        recent      = history[len(history) // 2 :]

        summary_prompt = (
            "Summarise the following game events in 3-5 sentences. "
            "Keep character names, locations, and key plot points:\n\n"
            + "\n".join(
                f"{m['role'].upper()}: {m['content'][:200]}"
                for m in to_compress
            )
        )

        try:
            summary = llm_fn(summary_prompt, system="You are a concise narrator.")
            compressed = [{"role": "system", "content": f"[Earlier events]: {summary}"}]
            return compressed + recent
        except Exception:
            return recent   # fallback: just discard old history


class GuidePlugin(PluginBase):
    """Generates contextual action suggestions for the player."""
    name = "guide"

    SUGGESTIONS: Dict[str, List[str]] = {
        "dungeon": [
            "Look for hidden passages",
            "Search the room for items",
            "Proceed cautiously",
            "Examine the walls",
            "Check your inventory",
        ],
        "village": [
            "Talk to the locals",
            "Visit the inn",
            "Look for work",
            "Explore the market",
        ],
        "combat": [
            "Attack the enemy",
            "Defend and wait",
            "Use an item",
            "Try to flee",
        ],
    }

    def on_session_start(self, session: GameSession) -> List[Block]:
        suggestions = self.SUGGESTIONS.get(session.genre, self.SUGGESTIONS["dungeon"])
        return [Block("choices", {"options": suggestions[:3], "source": "guide"})]


class SocialPlugin(PluginBase):
    """Tracks NPC relationship scores."""
    name = "social"

    def process(self, data: Dict[str, Any], session: GameSession,
                db: "GameStateDB") -> List[Block]:
        npc    = data.get("npc", "stranger")
        change = int(data.get("change", 0))
        db.update_relationship(session.id, npc, change)
        score  = db.get_relationship(session.id, npc)
        status = "friendly" if score > 20 else "neutral" if score > -20 else "hostile"
        return [Block("notification", {
            "level":   "info",
            "title":   f"Relationship with {npc}",
            "content": f"{status} ({score:+d})",
        })]


# ---------------------------------------------------------------------------
# SQLite database layer
# ---------------------------------------------------------------------------

class GameStateDB:
    """
    SQLite-backed game state store.

    Tables: sessions, history, items, events, relationships
    """

    def __init__(self, db_path: str = "generated_assets/narrative.db"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._path = db_path
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    player_name TEXT,
                    world TEXT,
                    genre TEXT,
                    hp INTEGER DEFAULT 100,
                    max_hp INTEGER DEFAULT 100,
                    gold INTEGER DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    inventory TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'active',
                    turn_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    event_type TEXT,
                    data TEXT,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS relationships (
                    session_id TEXT,
                    npc TEXT,
                    score INTEGER DEFAULT 0,
                    PRIMARY KEY (session_id, npc)
                );
            """)

    # ------------------------------------------------------------------
    def create_session(self, session: GameSession) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (session.id, session.player_name, session.world, session.genre,
                 session.hp, session.max_hp, session.gold, session.score,
                 json.dumps(session.inventory), session.status,
                 session.turn_count, session.created_at, session.updated_at),
            )

    def load_session(self, session_id: str) -> Optional[GameSession]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            return None
        return GameSession(
            id          = row["id"],
            player_name = row["player_name"],
            world       = row["world"],
            genre       = row["genre"],
            hp          = row["hp"],
            max_hp      = row["max_hp"],
            gold        = row["gold"],
            score       = row["score"],
            inventory   = json.loads(row["inventory"] or "[]"),
            status      = row["status"],
            turn_count  = row["turn_count"],
            created_at  = row["created_at"],
            updated_at  = row["updated_at"],
        )

    def save_session(self, session: GameSession) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as c:
            c.execute("""
                UPDATE sessions SET hp=?, max_hp=?, gold=?, score=?, inventory=?,
                status=?, turn_count=?, updated_at=? WHERE id=?
            """, (session.hp, session.max_hp, session.gold, session.score,
                  json.dumps(session.inventory), session.status,
                  session.turn_count, now, session.id))

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT id, player_name, genre, score, status, created_at FROM sessions ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def add_history(self, session_id: str, role: str, content: str) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO history(session_id,role,content,timestamp) VALUES(?,?,?,?)",
                      (session_id, role, content, datetime.utcnow().isoformat()))

    def get_history(self, session_id: str, limit: int = 40) -> List[Dict[str, str]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT role, content FROM history WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def log_event(self, session_id: str, event_type: str, data: Dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO events(session_id,event_type,data,timestamp) VALUES(?,?,?,?)",
                      (session_id, event_type, json.dumps(data), datetime.utcnow().isoformat()))

    def update_relationship(self, session_id: str, npc: str, delta: int) -> None:
        with self._conn() as c:
            c.execute("""
                INSERT INTO relationships(session_id,npc,score) VALUES(?,?,?)
                ON CONFLICT(session_id,npc) DO UPDATE SET score=score+?
            """, (session_id, npc, delta, delta))

    def get_relationship(self, session_id: str, npc: str) -> int:
        with self._conn() as c:
            row = c.execute("SELECT score FROM relationships WHERE session_id=? AND npc=?",
                            (session_id, npc)).fetchone()
        return row["score"] if row else 0


# ---------------------------------------------------------------------------
# LLM client (LiteLLM-compatible)
# ---------------------------------------------------------------------------

class LLMClient:
    """
    Minimal LLM client compatible with any OpenAI-compatible endpoint.
    Works with OpenAI, OpenRouter, Anthropic (via proxy), Ollama, etc.
    """

    def __init__(
        self,
        model:   str = "",
        api_key: str = "",
        api_base: str = "",
    ):
        self.model    = model    or os.environ.get("LLM_MODEL",    "gpt-4o-mini")
        self.api_key  = api_key  or os.environ.get("LLM_API_KEY",  "") \
                                 or os.environ.get("OPENAI_API_KEY", "")
        self.api_base = api_base or os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages:    List[Dict[str, str]],
        system:      Optional[str] = None,
        temperature: float = 0.85,
        max_tokens:  int   = 600,
    ) -> str:
        """Send a chat completion request. Returns response text."""
        if not self.available:
            return self._fallback_response(messages[-1]["content"] if messages else "")

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        import requests as req
        resp = req.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       self.model,
                "messages":    all_messages,
                "temperature": temperature,
                "max_tokens":  max_tokens,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _fallback_response(self, player_input: str) -> str:
        """Generate a basic response when no LLM API is available."""
        responses = [
            "You look around carefully. The path ahead is unclear.",
            "The world holds many mysteries. What will you do next?",
            "Your footsteps echo in the silence.",
            "Something stirs in the distance.",
            "The air grows thick with anticipation.",
        ]
        import random
        return random.choice(responses)


# ---------------------------------------------------------------------------
# Narrative Engine
# ---------------------------------------------------------------------------

_WORLD_SYSTEM = """You are the narrator of an interactive voxel game world.
Generate immersive, concise narrative responses to player actions.

CRITICAL FORMAT RULES — respond ONLY with valid JSON:
{{
  "narrative": "2-4 sentences describing what happens",
  "choices": ["action 1", "action 2", "action 3"],
  "events": []  // optional list of plugin events
}}

Events can include:
  {{"type": "combat",    "data": {{"enemy": "...", "enemy_hp": 30}}}}
  {{"type": "inventory", "data": {{"action": "add", "item": "..."}}}}
  {{"type": "social",    "data": {{"npc": "...", "change": 10}}}}
  {{"type": "image",     "data": {{"prompt": "scene description"}}}}
  {{"type": "game_over", "data": {{"won": true, "message": "..."}}}}

Keep responses focused and game-like. Advance the story meaningfully.
"""

_GENRE_CONTEXTS: Dict[str, str] = {
    "dungeon": "You are in a dark, ancient dungeon. Stone corridors, flickering torches, dangerous creatures.",
    "village": "You are in a peaceful medieval village. Cobblestone streets, friendly NPCs, quests to find.",
    "space":   "You are in a derelict space station. Metal corridors, failing systems, alien threats.",
    "fantasy": "You are in an enchanted forest kingdom. Ancient magic, mystical creatures, epic quests.",
    "horror":  "You are in a cursed ruin. Shadows move, whispers echo, survival is paramount.",
    "arctic":  "You are in a frozen research outpost. Blizzard outside, dwindling supplies, mysterious events.",
}


class NarrativeEngine:
    """
    LLM-native interactive narrative engine for VoxelForge.

    Implements dual-model architecture:
    - Primary LLM: generates narrative text and scene descriptions
    - Plugin agent: handles game mechanics (combat, inventory, social)

    Parameters
    ----------
    llm_model : str
        LLM model name (e.g. "gpt-4o-mini", "deepseek/deepseek-chat").
    llm_api_key : str
        API key for the LLM provider.
    llm_api_base : str
        API endpoint (default: OpenAI).
    db_path : str
        SQLite database file path.
    """

    def __init__(
        self,
        llm_model:    str = "",
        llm_api_key:  str = "",
        llm_api_base: str = "",
        db_path:      str = "generated_assets/narrative.db",
    ):
        self.llm     = LLMClient(llm_model, llm_api_key, llm_api_base)
        self.db      = GameStateDB(db_path)
        self.plugins: Dict[str, PluginBase] = {
            p.name: p for p in [
                CombatPlugin(),
                InventoryPlugin(),
                MemoryPlugin(),
                GuidePlugin(),
                SocialPlugin(),
            ]
        }

    # ------------------------------------------------------------------
    def start_session(
        self,
        player_name:  str,
        genre:        str = "dungeon",
        world_file:   Optional[str] = None,
        world_text:   Optional[str] = None,
    ) -> GameSession:
        """
        Create and persist a new game session.

        Parameters
        ----------
        player_name : str
        genre : str
            Game genre — sets the narrative context.
        world_file : str, optional
            Path to a Markdown world description file.
        world_text : str, optional
            World description text (alternative to world_file).

        Returns
        -------
        GameSession
        """
        world = world_text or ""
        if world_file and os.path.isfile(world_file):
            with open(world_file, encoding="utf-8") as f:
                world = f.read()[:2000]   # cap world context

        now = datetime.utcnow().isoformat()
        session = GameSession(
            id          = str(uuid.uuid4()),
            player_name = player_name,
            world       = world,
            genre       = genre,
            created_at  = now,
            updated_at  = now,
        )
        self.db.create_session(session)

        # Trigger start events
        intro_text = self._generate_intro(session)
        self.db.add_history(session.id, "assistant", intro_text)
        self.db.log_event(session.id, "session_start", {
            "player": player_name, "genre": genre
        })

        return session

    # ------------------------------------------------------------------
    def send_message(
        self,
        session_id: str,
        message:    str,
    ) -> NarrativeResponse:
        """
        Process a player message and return narrative + mechanics blocks.

        Parameters
        ----------
        session_id : str
        message : str
            Player's action/input.

        Returns
        -------
        NarrativeResponse
        """
        session = self.db.load_session(session_id)
        if not session:
            return NarrativeResponse(
                session_id = session_id,
                turn_id    = str(uuid.uuid4()),
                blocks     = [Block("notification", {"level": "error",
                                                      "title": "Session not found"})],
            )
        if session.status != "active":
            return NarrativeResponse(
                session_id = session_id,
                turn_id    = str(uuid.uuid4()),
                blocks     = [Block("notification", {"level": "warning",
                                                      "title": "Session ended",
                                                      "content": session.status})],
            )

        # Plugin pre-processing
        for plugin in self.plugins.values():
            modified = plugin.on_player_message(message, session)
            if modified is not None:
                message = modified

        # Add player message to history
        self.db.add_history(session_id, "user", message)

        # Load + optionally compress history
        history = self.db.get_history(session_id)
        mem_plugin = self.plugins.get("memory")
        if isinstance(mem_plugin, MemoryPlugin):
            history = mem_plugin.compress_history(
                history,
                lambda p, system="": self.llm.chat([{"role": "user", "content": p}], system=system),
            )

        # Generate narrative response
        turn_id   = str(uuid.uuid4())
        blocks: List[Block] = []

        llm_raw   = self._call_narrative_llm(session, history, message)
        llm_data  = self._parse_llm_response(llm_raw)

        # Add narrative block
        if llm_data.get("narrative"):
            blocks.append(Block("narrative", {"text": llm_data["narrative"]}))

        # Process plugin events from LLM response
        for event in llm_data.get("events", []):
            etype    = event.get("type", "")
            edata    = event.get("data", {})
            plugin   = self.plugins.get(etype)
            if plugin:
                blocks.extend(plugin.process(edata, session, self.db))

        # Add choices
        choices = llm_data.get("choices", [])
        if not choices:
            choices = self._default_choices(session.genre)
        blocks.append(Block("choices", {"options": choices[:4]}))

        # Stats update if needed
        if session.hp < session.max_hp * 0.3:
            blocks.append(Block("stats", {
                "warning": f"Low HP: {session.hp}/{session.max_hp}",
                "hp":       session.hp,
                "max_hp":   session.max_hp,
            }))

        # Persist
        session.turn_count += 1
        self.db.save_session(session)
        self.db.add_history(session_id, "assistant", llm_data.get("narrative", llm_raw))
        self.db.log_event(session_id, "turn", {
            "turn":    session.turn_count,
            "message": message[:200],
            "blocks":  len(blocks),
        })

        return NarrativeResponse(
            session_id   = session_id,
            turn_id      = turn_id,
            blocks       = blocks,
            raw_text     = llm_raw,
        )

    # ------------------------------------------------------------------
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Return current session state as a dict."""
        session = self.db.load_session(session_id)
        if not session:
            return {"error": "session not found"}
        return {
            "id":          session.id,
            "player":      session.player_name,
            "genre":       session.genre,
            "hp":          session.hp,
            "max_hp":      session.max_hp,
            "score":       session.score,
            "gold":        session.gold,
            "inventory":   session.inventory,
            "turn_count":  session.turn_count,
            "status":      session.status,
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        return self.db.list_sessions()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _generate_intro(self, session: GameSession) -> str:
        context = _GENRE_CONTEXTS.get(session.genre, _GENRE_CONTEXTS["dungeon"])
        world   = session.world[:500] if session.world else ""
        prompt  = (
            f"Start a new game session for player '{session.player_name}'. "
            f"Genre: {session.genre}. {context}. "
            + (f"World context: {world}" if world else "")
            + " Write a compelling 3-sentence opening scene."
        )
        try:
            return self.llm.chat(
                [{"role": "user", "content": prompt}],
                system  = f"You are a {session.genre} game narrator. Be immersive and concise.",
                max_tokens = 200,
            )
        except Exception:
            return context + f"\n\nWelcome, {session.player_name}. Your adventure begins..."

    def _call_narrative_llm(
        self,
        session: GameSession,
        history: List[Dict[str, str]],
        message: str,
    ) -> str:
        """Call the narrative LLM with full context."""
        context_str = _GENRE_CONTEXTS.get(session.genre, "")
        system      = _WORLD_SYSTEM.format() + f"\n\nGenre: {session.genre}. {context_str}"
        if session.world:
            system += f"\nWorld context: {session.world[:500]}"
        system += (
            f"\nPlayer: {session.player_name}. "
            f"HP: {session.hp}/{session.max_hp}. "
            f"Score: {session.score}. "
            f"Inventory: {', '.join(session.inventory) or 'empty'}."
        )

        messages = list(history[-10:])   # last 10 turns
        messages.append({"role": "user", "content": message})

        try:
            return self.llm.chat(messages, system=system, max_tokens=400)
        except Exception as exc:
            return json.dumps({
                "narrative": f"The world shifts... ({exc})",
                "choices":   self._default_choices(session.genre),
                "events":    [],
            })

    def _parse_llm_response(self, raw: str) -> Dict[str, Any]:
        """Parse LLM JSON response, with fallback for plain text."""
        # Try to extract JSON block
        raw = raw.strip()
        start = raw.find("{")
        end   = raw.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        # Plain text fallback
        return {
            "narrative": raw[:500] if raw else "The world awaits...",
            "choices":   [],
            "events":    [],
        }

    def _default_choices(self, genre: str) -> List[str]:
        return GuidePlugin.SUGGESTIONS.get(genre, GuidePlugin.SUGGESTIONS["dungeon"])[:3]


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_engine(
    model:   str = "",
    api_key: str = "",
    db_path: str = "generated_assets/narrative.db",
) -> NarrativeEngine:
    """Create a NarrativeEngine with sensible defaults from environment."""
    return NarrativeEngine(
        llm_model   = model   or os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        llm_api_key = api_key or os.environ.get("LLM_API_KEY", "")
                              or os.environ.get("OPENAI_API_KEY", ""),
        db_path     = db_path,
    )
