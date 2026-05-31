"""
forge.scene
===========
Python scene-builder for VoxelForge engine.

Scene files are JSON and fully compatible with the C engine loader.
Use this module to construct scenes programmatically, add entities,
configure components, and write the result to disk.

Example
-------
>>> from forge.scene import Scene
>>> scene = Scene(background_color=(0.05, 0.08, 0.12))
>>> eid = scene.add_voxel_model("hero", "Assets/Game/Models/char.vox",
...                              position=(0, 0, 0))
>>> scene.add_point_light("sun", position=(10, 20, 0),
...                        intensity=1.5, color=(1.0, 0.95, 0.8))
>>> scene.save("engine/Assets/Scenes/my_scene.scene")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes for component data
# ---------------------------------------------------------------------------

@dataclass
class TransformData:
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale:    Tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class VoxelModelData:
    model_path: str = "Assets/Game/Models"
    model_name: str = "model.vox"
    object_name: str = ""           # sub-object name for multi-model .vox
    small_scale: bool = False
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    enabled: bool = True


@dataclass
class RigidBodyData:
    is_kinematic: bool = True
    mass: float = 1.0


@dataclass
class PointLightData:
    color:     Tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    radius:    float = 10.0


@dataclass
class LuaScriptData:
    script_path: str = "Assets/Game/Scripts"
    script_name: str = "script.lua"


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    name: str
    entity_id: int
    transform:    Optional[TransformData]  = None
    voxel_model:  Optional[VoxelModelData] = None
    rigid_body:   Optional[RigidBodyData]  = None
    point_light:  Optional[PointLightData] = None
    lua_script:   Optional[LuaScriptData]  = None
    children:     List[int]                = field(default_factory=list)
    parent_id:    Optional[int]            = None
    is_prefab:    bool                     = False
    prefab_path:  str                      = ""
    prefab_name:  str                      = ""

    # ------------------------------------------------------------------
    def _encode(self) -> Dict[str, Any]:
        obj: Dict[str, Any] = {}

        if self.is_prefab:
            obj["isPrefab"] = True
            obj["prefabPath"] = self.prefab_path
            obj["prefabName"] = self.prefab_name

        components: Dict[str, Any] = {}

        if self.transform:
            t = self.transform
            components["Transform"] = {
                "position": list(t.position),
                "rotation": list(t.rotation),
                "scale":    list(t.scale),
            }

        if self.voxel_model:
            vm = self.voxel_model
            entry: Dict[str, Any] = {
                "modelPath":  vm.model_path,
                "modelName":  vm.model_name,
                "smallScale": vm.small_scale,
                "center":     list(vm.center),
            }
            if vm.object_name:
                entry["objectName"] = vm.object_name
            components["VoxelModel"] = entry

        if self.rigid_body:
            rb = self.rigid_body
            components["RigidBody"] = {
                "isKinematic": rb.is_kinematic,
                "mass":        rb.mass,
            }

        if self.point_light:
            pl = self.point_light
            components["PointLight"] = {
                "color":     list(pl.color),
                "intensity": pl.intensity,
                "radius":    pl.radius,
            }

        if self.lua_script:
            ls = self.lua_script
            components["LuaScript"] = {
                "scriptPath": ls.script_path,
                "scriptName": ls.script_name,
            }

        if components:
            obj["components"] = components

        if self.children:
            obj["children"] = self.children

        return obj


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

class Scene:
    """
    Constructs a VoxelForge scene that can be loaded by the C engine.

    All entities are stored in an ``entities`` dict keyed by integer ID.
    Entity IDs are auto-assigned starting from 0.
    """

    def __init__(
        self,
        background_color: Tuple[float, float, float] = (0.0, 0.149, 0.294),
        ambient_intensity: float = 0.3,
        directional_light: Tuple[float, float, float] = (0.5, -1.0, -0.5),
        palette_path: str = "Assets/Textures/magicaPalette.png",
    ):
        self.background_color    = background_color
        self.ambient_intensity   = ambient_intensity
        self.directional_light   = directional_light
        self.palette_path        = palette_path
        self.entities: Dict[int, Entity] = {}
        self._next_id: int       = 0

    # ------------------------------------------------------------------
    def _new_id(self) -> int:
        eid = self._next_id
        self._next_id += 1
        return eid

    # ------------------------------------------------------------------
    def add_entity(
        self,
        name: str,
        position: Tuple[float, float, float] = (0, 0, 0),
        rotation: Tuple[float, float, float] = (0, 0, 0),
        scale:    Tuple[float, float, float] = (1, 1, 1),
    ) -> int:
        """Create a bare entity with a Transform.  Returns its entity ID."""
        eid = self._new_id()
        self.entities[eid] = Entity(
            name=name,
            entity_id=eid,
            transform=TransformData(position, rotation, scale),
        )
        return eid

    # ------------------------------------------------------------------
    def add_voxel_model(
        self,
        name: str,
        vox_path: str,
        position: Tuple[float, float, float] = (0, 0, 0),
        rotation: Tuple[float, float, float] = (0, 0, 0),
        scale:    Tuple[float, float, float] = (1, 1, 1),
        small_scale: bool = False,
        object_name: str = "",
        parent_id: Optional[int] = None,
    ) -> int:
        """
        Add an entity with a VoxelModel component.

        ``vox_path`` should be relative to the engine working directory,
        e.g. ``"Assets/Game/Models/building.vox"``.

        Returns the entity ID.
        """
        model_path = os.path.dirname(vox_path).replace("\\", "/") or "."
        model_name = os.path.basename(vox_path)

        eid = self._new_id()
        entity = Entity(
            name=name,
            entity_id=eid,
            transform=TransformData(position, rotation, scale),
            voxel_model=VoxelModelData(
                model_path=model_path,
                model_name=model_name,
                object_name=object_name,
                small_scale=small_scale,
            ),
        )
        if parent_id is not None:
            entity.parent_id = parent_id
            if parent_id in self.entities:
                self.entities[parent_id].children.append(eid)

        self.entities[eid] = entity
        return eid

    # ------------------------------------------------------------------
    def add_point_light(
        self,
        name: str,
        position: Tuple[float, float, float] = (0, 10, 0),
        color:    Tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
        radius:    float = 15.0,
    ) -> int:
        """Add a point-light entity.  Returns its entity ID."""
        eid = self._new_id()
        self.entities[eid] = Entity(
            name=name,
            entity_id=eid,
            transform=TransformData(position),
            point_light=PointLightData(color, intensity, radius),
        )
        return eid

    # ------------------------------------------------------------------
    def add_rigid_body(
        self,
        entity_id: int,
        is_kinematic: bool = True,
        mass: float = 1.0,
    ) -> None:
        """Attach a RigidBody component to an existing entity."""
        if entity_id not in self.entities:
            raise KeyError(f"Entity {entity_id} not found")
        self.entities[entity_id].rigid_body = RigidBodyData(is_kinematic, mass)

    # ------------------------------------------------------------------
    def add_lua_script(
        self,
        entity_id: int,
        script_path: str,
        script_name: str,
    ) -> None:
        """Attach a Lua script component to an existing entity."""
        if entity_id not in self.entities:
            raise KeyError(f"Entity {entity_id} not found")
        self.entities[entity_id].lua_script = LuaScriptData(script_path, script_name)

    # ------------------------------------------------------------------
    def add_prefab(
        self,
        name: str,
        prefab_path: str,
        prefab_name: str,
        position: Tuple[float, float, float] = (0, 0, 0),
        rotation: Tuple[float, float, float] = (0, 0, 0),
        scale:    Tuple[float, float, float] = (1, 1, 1),
    ) -> int:
        """Instantiate a prefab entity at a given position.  Returns entity ID."""
        eid = self._new_id()
        self.entities[eid] = Entity(
            name=name,
            entity_id=eid,
            transform=TransformData(position, rotation, scale),
            is_prefab=True,
            prefab_path=prefab_path,
            prefab_name=prefab_name,
        )
        return eid

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        doc: Dict[str, Any] = {
            "backgroundColor": list(self.background_color),
            "ambientIntensity": self.ambient_intensity,
            "directionalLight": list(self.directional_light),
            "palettePath":      self.palette_path,
            "entities":         {},
        }
        for eid, entity in self.entities.items():
            doc["entities"][str(eid)] = entity._encode()
        return doc

    def save(self, path: str) -> None:
        """Write the scene to a JSON .scene file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "Scene":
        """Load an existing .scene file."""
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        scene = cls(
            background_color=tuple(doc.get("backgroundColor", [0, 0.149, 0.294])),
            ambient_intensity=doc.get("ambientIntensity", 0.3),
            directional_light=tuple(doc.get("directionalLight", [0.5, -1.0, -0.5])),
            palette_path=doc.get("palettePath", "Assets/Textures/magicaPalette.png"),
        )
        for eid_str, entity_doc in doc.get("entities", {}).items():
            eid = int(eid_str)
            entity = Entity(name=entity_doc.get("name", f"entity_{eid}"), entity_id=eid)
            comp = entity_doc.get("components", {})

            if "Transform" in comp:
                t = comp["Transform"]
                entity.transform = TransformData(
                    position=tuple(t.get("position", [0, 0, 0])),
                    rotation=tuple(t.get("rotation", [0, 0, 0])),
                    scale=tuple(t.get("scale", [1, 1, 1])),
                )
            if "VoxelModel" in comp:
                vm = comp["VoxelModel"]
                entity.voxel_model = VoxelModelData(
                    model_path=vm.get("modelPath", ""),
                    model_name=vm.get("modelName", ""),
                    object_name=vm.get("objectName", ""),
                    small_scale=vm.get("smallScale", False),
                    center=tuple(vm.get("center", [0, 0, 0])),
                )
            if "PointLight" in comp:
                pl = comp["PointLight"]
                entity.point_light = PointLightData(
                    color=tuple(pl.get("color", [1, 1, 1])),
                    intensity=pl.get("intensity", 1.0),
                    radius=pl.get("radius", 10.0),
                )
            if "RigidBody" in comp:
                rb = comp["RigidBody"]
                entity.rigid_body = RigidBodyData(
                    is_kinematic=rb.get("isKinematic", True),
                    mass=rb.get("mass", 1.0),
                )
            if "LuaScript" in comp:
                ls = comp["LuaScript"]
                entity.lua_script = LuaScriptData(
                    script_path=ls.get("scriptPath", ""),
                    script_name=ls.get("scriptName", ""),
                )
            entity.children   = entity_doc.get("children", [])
            entity.is_prefab  = entity_doc.get("isPrefab", False)
            entity.prefab_path = entity_doc.get("prefabPath", "")
            entity.prefab_name = entity_doc.get("prefabName", "")
            scene.entities[eid] = entity
            scene._next_id = max(scene._next_id, eid + 1)
        return scene

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Scene entities={len(self.entities)} "
            f"bg={self.background_color}>"
        )
