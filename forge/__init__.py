"""
VoxelForge  —  AI-Powered Voxel World Builder
==============================================
Python automation layer for the VoxelForge engine.

Quick-start
-----------
>>> from forge import VoxelModel, Scene, Palette
>>> from forge.generators import TerrainGenerator, BuildingGenerator

>>> palette = Palette.from_file("engine/Assets/Textures/magicaPalette.png")
>>> terrain  = TerrainGenerator(palette).generate(width=32, height=32, depth=8)
>>> terrain.save("engine/Assets/Game/Models/terrain.vox")

>>> scene = Scene()
>>> scene.add_voxel_model("terrain", "Assets/Game/Models/terrain.vox")
>>> scene.save("engine/Assets/Scenes/generated.scene")
"""

from .voxel import VoxelModel, Palette  # noqa: F401
from .scene import Scene, Entity  # noqa: F401

__version__ = "1.0.0"
__author__  = "VoxelForge"
