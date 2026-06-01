"""
Tests for forge.voxel — VoxelModel, Palette, .vox I/O
"""

import os

import pytest

from forge.voxel import Palette, VoxelModel, save_multi_vox


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

class TestPalette:
    def test_default_256_entries(self):
        pal = Palette()
        assert len(pal) == 256

    def test_index_zero_transparent(self):
        pal = Palette()
        r, g, b, a = pal[0]
        assert a == 0

    def test_getset(self):
        pal = Palette()
        pal[5] = (10, 20, 30, 255)
        assert pal[5] == (10, 20, 30, 255)

    def test_closest(self):
        pal = Palette()
        pal[10] = (255, 0, 0, 255)
        idx = pal.closest(250, 0, 0)
        assert idx == 10

    def test_natural_256(self):
        pal = Palette.natural()
        assert len(pal) == 256

    def test_grayscale_monotone(self):
        pal = Palette.grayscale()
        r, g, b, a = pal[100]
        assert r == g == b

    def test_roundtrip_bytes(self):
        pal = Palette.natural()
        b   = pal.to_bytes()
        assert len(b) == 256 * 4
        pal2 = Palette.from_bytes(b)
        assert pal2[50] == pal[50]


# ---------------------------------------------------------------------------
# VoxelModel basic ops
# ---------------------------------------------------------------------------

class TestVoxelModel:
    def test_empty_shape(self):
        m = VoxelModel.empty(4, 5, 6)
        assert m.width  == 4
        assert m.height == 5
        assert m.depth  == 6
        assert m.voxel_count() == 0

    def test_set_get(self):
        m = VoxelModel.empty(8, 8, 8)
        m.set(3, 3, 3, 42)
        assert m.get(3, 3, 3) == 42
        assert m.get(0, 0, 0) == 0

    def test_set_out_of_bounds(self):
        m = VoxelModel.empty(4, 4, 4)
        m.set(100, 100, 100, 1)   # should not raise, just silently skip
        assert m.voxel_count() == 0

    def test_fill(self):
        m = VoxelModel.empty(8, 8, 8)
        m.fill(0, 0, 0, 3, 3, 3, 5)
        assert m.voxel_count() == 4 * 4 * 4

    def test_voxels_iterator(self):
        m = VoxelModel.empty(4, 4, 4)
        m.set(1, 2, 3, 7)
        voxels = list(m.voxels())
        assert len(voxels) == 1
        x, y, z, c = voxels[0]
        assert (x, y, z, c) == (1, 2, 3, 7)


# ---------------------------------------------------------------------------
# .vox file I/O
# ---------------------------------------------------------------------------

class TestVoxFileIO:
    def test_save_load_roundtrip(self, tmp_path):
        m = VoxelModel.empty(6, 6, 6, name="roundtrip")
        m.set(1, 1, 1, 10)
        m.set(3, 3, 3, 20)
        path = str(tmp_path / "rt.vox")
        m.save(path)

        m2 = VoxelModel.load(path)
        assert m2.width  == 6
        assert m2.height == 6
        assert m2.depth  == 6
        assert m2.get(1, 1, 1) == 10
        assert m2.get(3, 3, 3) == 20
        assert m2.get(0, 0, 0) == 0

    def test_voxel_count_preserved(self, tmp_path):
        m = VoxelModel.empty(10, 10, 10)
        m.fill(0, 0, 0, 4, 4, 4, 3)
        path = str(tmp_path / "cnt.vox")
        m.save(path)
        m2 = VoxelModel.load(path)
        assert m2.voxel_count() == m.voxel_count()

    def test_palette_preserved(self, tmp_path):
        pal = Palette()
        pal[1] = (255, 0, 128, 255)
        m = VoxelModel.empty(4, 4, 4, palette=pal)
        m.set(0, 0, 0, 1)
        path = str(tmp_path / "pal.vox")
        m.save(path)
        m2 = VoxelModel.load(path)
        assert m2.palette[1] == (255, 0, 128, 255)

    def test_load_engine_char(self):
        """Load one of the bundled engine .vox files."""
        path = "engine/Assets/Game/Models/char.vox"
        if not os.path.isfile(path):
            pytest.skip("Engine assets not present")
        m = VoxelModel.load(path)
        assert m.voxel_count() > 0

    def test_load_engine_bullet(self):
        path = "engine/Assets/Game/Models/Bullet.vox"
        if not os.path.isfile(path):
            pytest.skip("Engine assets not present")
        m = VoxelModel.load(path)
        assert m.voxel_count() > 0

    def test_multi_vox_saves(self, tmp_path):
        a = VoxelModel.empty(4, 4, 4, name="a")
        b = VoxelModel.empty(6, 6, 6, name="b")
        a.set(0, 0, 0, 1)
        b.set(1, 1, 1, 2)
        path = str(tmp_path / "multi.vox")
        save_multi_vox({"a": a, "b": b}, path)
        assert os.path.isfile(path)
        # Single-load reads first model
        m = VoxelModel.load(path)
        assert m.voxel_count() > 0


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

class TestGenerators:
    def test_terrain_basic(self):
        from forge.generators import TerrainGenerator
        gen = TerrainGenerator(Palette.natural(), seed=0)
        m   = gen.generate(width=8, height=8, max_depth=6, biome="grassland")
        assert m.width == 8
        assert m.height == 8
        assert m.depth  == 6
        assert m.voxel_count() > 0

    def test_terrain_all_biomes(self):
        from forge.generators import TerrainGenerator
        gen = TerrainGenerator(Palette.natural(), seed=1)
        for biome in ("grassland", "desert", "snow", "ocean", "forest"):
            m = gen.generate(width=6, height=6, max_depth=4, biome=biome)
            assert m.voxel_count() > 0, f"biome={biome} produced no voxels"

    def test_building_all_styles(self):
        from forge.generators import BuildingGenerator
        gen = BuildingGenerator(Palette.natural(), seed=2)
        for style in ("modern", "medieval", "sci-fi", "rustic", "fantasy"):
            m = gen.generate(6, 6, 2, style=style)
            assert m.voxel_count() > 0, f"style={style} produced no voxels"

    def test_character_all_classes(self):
        from forge.generators import CharacterGenerator
        gen = CharacterGenerator(Palette.natural(), seed=3)
        for cls in ("warrior", "mage", "archer", "rogue"):
            m = gen.generate(class_type=cls, name=cls)
            assert m.voxel_count() > 0

    def test_props_all_types(self):
        from forge.generators import PropGenerator
        gen = PropGenerator(Palette.natural(), seed=4)
        for ptype in ("tree", "crate", "barrel", "lamp_post", "rock", "chest", "mushroom"):
            m = gen.generate(ptype, name=ptype)
            assert m.voxel_count() > 0, f"prop={ptype} produced no voxels"

    def test_unknown_prop_raises(self):
        from forge.generators import PropGenerator
        gen = PropGenerator(Palette.natural())
        with pytest.raises(ValueError):
            gen.generate("unicorn")


# ---------------------------------------------------------------------------
# Scene builder
# ---------------------------------------------------------------------------

class TestScene:
    def test_empty_scene_saves(self, tmp_path):
        from forge.scene import Scene
        scene = Scene()
        path  = str(tmp_path / "empty.scene")
        scene.save(path)
        import json
        with open(path) as f:
            doc = json.load(f)
        assert "data" in doc
        assert "entities" in doc
        assert isinstance(doc["entities"], list)
        assert len(doc["entities"]) == 0

    def test_add_voxel_model(self, tmp_path):
        from forge.scene import Scene
        scene = Scene()
        scene.add_voxel_model("obj", "Assets/Game/Models/char.vox",
                               position=(1, 2, 3))
        assert scene.entity_count == 1
        path = str(tmp_path / "s.scene")
        scene.save(path)
        import json
        with open(path) as f:
            doc = json.load(f)
        e = doc["entities"][0]
        assert "Transform" in e
        assert "VoxelModel" in e
        assert "RigidBody" in e
        assert e["Transform"]["position"] == [1, 2, 3]

    def test_add_point_light(self, tmp_path):
        from forge.scene import Scene
        scene = Scene()
        scene.add_point_light("sun", position=(0, 0, 20),
                               color=(1, 1, 1), intensity=2.0, range_=80.0)
        import json
        path = str(tmp_path / "light.scene")
        scene.save(path)
        with open(path) as f:
            doc = json.load(f)
        light_entities = [e for e in doc["entities"] if "PointLight" in e]
        assert len(light_entities) == 1
        pl = light_entities[0]["PointLight"]
        assert pl["range"]    == 80.0
        assert pl["hueShift"] == 0.0

    def test_scene_format_matches_engine(self, tmp_path):
        """Verify the scene JSON exactly matches what EngineScene.c parses."""
        from forge.scene import Scene
        scene = Scene(background_color=(0.1, 0.2, 0.3))
        scene.add_voxel_model("t", "Assets/Game/Models/char.vox",
                               is_static=True)
        scene.add_point_light("l", position=(5, 5, 10), range_=50.0)
        path = str(tmp_path / "fmt.scene")
        scene.save(path)
        import json
        with open(path) as f:
            doc = json.load(f)

        # Top-level: data + entities
        assert set(doc.keys()) == {"data", "entities"}
        # data has the three scene-global vectors
        data_keys = set(doc["data"].keys())
        assert "backgroundColor" in data_keys
        assert "sunColor"        in data_keys
        assert "sunDirection"    in data_keys
        # entities is a list
        assert isinstance(doc["entities"], list)
        # entity has direct component keys (no "components" wrapper)
        e0 = doc["entities"][0]
        assert "Transform"  in e0
        assert "VoxelModel" in e0
        # PointLight uses "range" and "hueShift"
        e1 = doc["entities"][1]
        assert "PointLight" in e1
        assert "range"    in e1["PointLight"]
        assert "hueShift" in e1["PointLight"]
        assert "radius"  not in e1["PointLight"]   # wrong key must NOT be present

    def test_scene_load_roundtrip(self, tmp_path):
        from forge.scene import Scene
        scene = Scene(background_color=(0.5, 0.6, 0.7))
        scene.add_voxel_model("x", "Assets/Game/Models/Bullet.vox",
                               position=(10, 20, 30))
        path = str(tmp_path / "rt.scene")
        scene.save(path)
        scene2 = Scene.load(path)
        assert len(scene2._entities) == len(scene._entities)
        assert scene2.background_color == pytest.approx((0.5, 0.6, 0.7))
