"""
forge.scene
===========
Python scene-builder for VoxelForge engine.

Produces JSON scene files that are **directly loadable** by the C engine.
The format exactly matches what EngineScene.c / EngineECS.c parse:

  {
    "data": {
      "backgroundColor": [r, g, b],
      "sunColor":        [r, g, b],
      "sunDirection":    [x, y, z]
    },
    "entities": [
      {
        "Transform":  { "position": [x,y,z], "rotation": [x,y,z] },
        "VoxelModel": { "modelPath": "...", "modelName": "...",
                        "smallScale": false, "center": [x,y,z] },
        "RigidBody":  { "mass": 1, "bounciness": 0.2,
                        "velocity": [0,0,0], "acceleration": [0,0,0],
                        "useGravity": true, "isStatic": true },
        "childs": [
          {
            "Transform":  { "position": [x,y,z], "rotation": [x,y,z] },
            "PointLight": { "color": [r,g,b], "intensity": 1.0,
                            "range": 100, "hueShift": 0 }
          }
        ]
      }
    ]
  }

Key engine constraints (verified from C source):
  - entities is an **array** (not a dict keyed by ID)
  - component data is a **direct key** on the entity object
  - children are **nested entity objects** under "childs"
  - Transform has only position[3] and rotation[3] (no scale)
  - PointLight uses "range" (not "radius") and requires "hueShift"
  - RigidBody uses "bounciness", "useGravity", "isStatic"

Example
-------
>>> from forge.scene import Scene
>>> scene = Scene()
>>> scene.add_voxel_model("terrain", "Assets/Game/Models/terrain.vox")
>>> scene.add_point_light("sun",  position=(10, 10, 30),
...                        color=(1.0, 0.95, 0.85), intensity=2.0, range_=80)
>>> scene.save("engine/Assets/Scenes/generated.scene")
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple


Vec3 = Tuple[float, float, float]

_ZERO3 = (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Low-level entity dict builder (matches engine JSON exactly)
# ---------------------------------------------------------------------------

def _transform(position: Vec3, rotation: Vec3) -> Dict[str, Any]:
    return {
        "position": list(position),
        "rotation": list(rotation),
    }


def _voxel_model(model_path: str, model_name: str,
                  small_scale: bool = False,
                  center: Vec3 = _ZERO3,
                  object_name: str = "") -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "modelPath":  model_path,
        "modelName":  model_name,
        "smallScale": small_scale,
        "center":     list(center),
    }
    if object_name:
        d["objectName"] = object_name
    return d


def _rigid_body(mass: float = 1.0, bounciness: float = 0.2,
                use_gravity: bool = True, is_static: bool = True) -> Dict[str, Any]:
    return {
        "mass":         mass,
        "bounciness":   bounciness,
        "velocity":     [0.0, 0.0, 0.0],
        "acceleration": [0.0, 0.0, 0.0],
        "useGravity":   use_gravity,
        "isStatic":     is_static,
    }


def _point_light(color: Vec3 = (1.0, 1.0, 1.0),
                  intensity: float = 1.0,
                  range_: float = 100.0,
                  hue_shift: float = 0.0) -> Dict[str, Any]:
    return {
        "color":     list(color),
        "intensity": intensity,
        "range":     range_,
        "hueShift":  hue_shift,
    }


def _lua_script(script_path: str, script_name: str) -> Dict[str, Any]:
    return {
        "scriptPath": script_path,
        "scriptName": script_name,
    }


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

class Scene:
    """
    Constructs a VoxelForge scene compatible with the C engine.

    Entities are stored as a list of dicts that precisely mirror the
    cJSON structure the engine reads via ``DecodeEntity()``.
    """

    def __init__(
        self,
        background_color: Vec3 = (0.0, 0.149, 0.294),
        sun_color:        Vec3 = (0.93, 0.92, 0.92),
        sun_direction:    Vec3 = (0.46, 0.13, -0.98),
    ):
        self.background_color = background_color
        self.sun_color        = sun_color
        self.sun_direction    = sun_direction
        # Each item is a raw dict ready for JSON serialisation
        self._entities: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_entity(
        self,
        position: Vec3 = _ZERO3,
        rotation: Vec3 = _ZERO3,
    ) -> Dict[str, Any]:
        return {"Transform": _transform(position, rotation)}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_voxel_model(
        self,
        name: str,             # used only as a comment / for our tracking
        vox_path: str,
        position:    Vec3   = _ZERO3,
        rotation:    Vec3   = _ZERO3,
        small_scale: bool   = False,
        object_name: str    = "",
        center:      Vec3   = _ZERO3,
        add_rigidbody: bool = True,
        is_static:   bool   = True,
        mass:        float  = 1.0,
        bounciness:  float  = 0.2,
    ) -> Dict[str, Any]:
        """
        Add an entity with a Transform + VoxelModel (+ optional RigidBody).

        ``vox_path`` should be relative to the engine working directory,
        e.g. ``"Assets/Game/Models/terrain.vox"`` or a relative path like
        ``"generated_assets/terrain/terrain.vox"``.

        Returns the entity dict (can be used to attach children later).
        """
        model_path = os.path.dirname(vox_path).replace("\\", "/")
        model_name = os.path.basename(vox_path)
        if not model_path:
            model_path = "."
        # Engine expects trailing slash on the path
        if model_path and not model_path.endswith("/"):
            model_path += "/"

        entity: Dict[str, Any] = {
            "Transform":  _transform(position, rotation),
            "VoxelModel": _voxel_model(model_path, model_name, small_scale,
                                        center, object_name),
        }
        if add_rigidbody:
            entity["RigidBody"] = _rigid_body(mass, bounciness,
                                               use_gravity=not is_static,
                                               is_static=is_static)
        self._entities.append(entity)
        return entity

    # ------------------------------------------------------------------
    def add_point_light(
        self,
        name:      str,        # comment / tracking only
        position:  Vec3   = (0.0, 0.0, 10.0),
        color:     Vec3   = (1.0, 1.0, 1.0),
        intensity: float  = 1.0,
        range_:    float  = 100.0,
        hue_shift: float  = 0.0,
        parent:    Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add a point-light entity (Transform + PointLight).

        If ``parent`` is given (a dict returned by ``add_voxel_model``),
        the light is embedded as a child of that entity (matching the way
        the engine editor creates lights attached to objects).

        Otherwise the light is a top-level entity.
        """
        entity: Dict[str, Any] = {
            "Transform":  _transform(position, (0.0, 0.0, 0.0)),
            "PointLight": _point_light(color, intensity, range_, hue_shift),
        }
        if parent is not None:
            parent.setdefault("childs", []).append(entity)
        else:
            self._entities.append(entity)
        return entity

    # ------------------------------------------------------------------
    def add_lua_script(
        self,
        entity:      Dict[str, Any],
        script_path: str,
        script_name: str,
    ) -> None:
        """Attach a LuaScript component to an existing entity dict."""
        entity["LuaScript"] = _lua_script(script_path, script_name)

    # ------------------------------------------------------------------
    def add_prefab(
        self,
        prefab_path: str,
        prefab_name: str,
        position:    Vec3 = _ZERO3,
        rotation:    Vec3 = _ZERO3,
    ) -> Dict[str, Any]:
        """Instantiate a prefab entity at a given transform."""
        entity: Dict[str, Any] = {
            "prefabPath": prefab_path,
            "prefabName": prefab_name,
            "Transform":  _transform(position, rotation),
        }
        self._entities.append(entity)
        return entity

    # ------------------------------------------------------------------
    @property
    def entity_count(self) -> int:
        return len(self._entities)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": {
                "backgroundColor": list(self.background_color),
                "sunColor":        list(self.sun_color),
                "sunDirection":    list(self.sun_direction),
            },
            "entities": self._entities,
        }

    def save(self, path: str) -> None:
        """Write the scene to a JSON .scene file."""
        d = os.path.dirname(os.path.abspath(path))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent="\t")

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "Scene":
        """Load an existing .scene file (read-only — returns a Scene)."""
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        data = doc.get("data", {})
        scene = cls(
            background_color = tuple(data.get("backgroundColor", [0, 0.149, 0.294])),
            sun_color        = tuple(data.get("sunColor",        [0.93, 0.92, 0.92])),
            sun_direction    = tuple(data.get("sunDirection",    [0.46, 0.13, -0.98])),
        )
        scene._entities = doc.get("entities", [])
        return scene

    def __repr__(self) -> str:
        return (
            f"<Scene entities={len(self._entities)} "
            f"bg={self.background_color}>"
        )


# ---------------------------------------------------------------------------
# Module-level convenience aliases kept for backward compat
# ---------------------------------------------------------------------------
Entity = Dict[str, Any]
