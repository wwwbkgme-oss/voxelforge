"""
forge.generators.characters
============================
Procedural humanoid character generator for VoxelForge.

Builds characters from body-part blocks with configurable proportions,
armour style, skin tone, and equipment.

Example
-------
>>> from forge.generators import CharacterGenerator
>>> gen = CharacterGenerator(Palette.natural(), seed=1)
>>> hero = gen.generate(class_type="warrior", skin_tone="tan")
>>> hero.save("engine/Assets/Game/Models/hero.vox")
"""

from __future__ import annotations

import random
from ..voxel import VoxelModel, Palette


# ---------------------------------------------------------------------------
# Colour ranges (palette indices)
# ---------------------------------------------------------------------------

_SKIN_TONES = {
    "light":   (82, 87),
    "tan":     (84, 90),
    "dark":    (21, 26),
    "fantasy": (1, 10),
}

_HAIR_COLORS = {
    "blonde": (101, 108),
    "brown":  (22, 28),
    "black":  (41, 44),
    "red":    (81, 86),
    "white":  (121, 130),
    "blue":   (61, 70),
}

_ARMOUR_COLORS = {
    "none":    None,
    "leather": (21, 32),
    "chainmail": (41, 52),
    "plate":   (45, 60),
    "mage":    (61, 79),
}

_WEAPON_COLORS = {
    "none":    None,
    "sword":   (42, 55),
    "staff":   (22, 30),
    "bow":     (21, 26),
    "axe":     (43, 56),
}


class CharacterGenerator:
    """Generates small humanoid voxel characters (approx 8×4×16 voxels)."""

    # Character canvas dimensions
    W, D, H = 8, 4, 16

    def __init__(self, palette: Palette, seed: int = 0):
        self.palette = palette
        self._rng = random.Random(seed)

    def _c(self, lo: int, hi: int) -> int:
        return self._rng.randint(lo, hi)

    # ------------------------------------------------------------------
    def generate(
        self,
        class_type:  str = "warrior",
        skin_tone:   str = "tan",
        hair_color:  str = "brown",
        armour:      str = "chainmail",
        weapon:      str = "sword",
        name:        str = "",
    ) -> VoxelModel:
        """
        Generate a humanoid character.

        Parameters
        ----------
        class_type : str
            warrior | mage | archer | rogue
        skin_tone : str
            light | tan | dark | fantasy
        hair_color : str
            blonde | brown | black | red | white | blue
        armour : str
            none | leather | chainmail | plate | mage
        weapon : str
            none | sword | staff | bow | axe

        Returns
        -------
        VoxelModel
        """
        model = VoxelModel.empty(self.W, self.D, self.H, self.palette,
                                  name=name or f"char_{class_type}")

        skin_lo, skin_hi = _SKIN_TONES.get(skin_tone, (82, 87))
        hair_lo, hair_hi = _HAIR_COLORS.get(hair_color, (22, 28))
        arm_range        = _ARMOUR_COLORS.get(armour)
        wpn_range        = _WEAPON_COLORS.get(weapon)

        # --- Legs (Z 0..3) ---
        leg_c = self._c(skin_lo, skin_hi)
        if arm_range:
            leg_c = self._c(*arm_range)
        for z in range(4):
            # Left leg
            for y in range(self.D):
                model.set(1, y, z, leg_c)
                model.set(2, y, z, leg_c)
            # Right leg
            for y in range(self.D):
                model.set(4, y, z, leg_c)
                model.set(5, y, z, leg_c)

        # --- Torso (Z 4..9) ---
        torso_c = self._c(*arm_range) if arm_range else self._c(skin_lo, skin_hi)
        for z in range(4, 10):
            for x in range(1, self.W - 1):
                for y in range(self.D):
                    model.set(x, y, z, torso_c)

        # --- Arms (Z 4..8) ---
        arm_c = self._c(*arm_range) if arm_range else self._c(skin_lo, skin_hi)
        for z in range(4, 9):
            for y in range(self.D):
                model.set(0, y, z, arm_c)      # left arm
                model.set(self.W-1, y, z, arm_c)  # right arm

        # --- Head (Z 10..14) ---
        head_c = self._c(skin_lo, skin_hi)
        for z in range(10, 15):
            for x in range(2, self.W - 2):
                for y in range(self.D):
                    model.set(x, y, z, head_c)
        # Eyes
        eye_c = 65
        for y in range(self.D):
            model.set(2, y, 13, eye_c)
            model.set(5, y, 13, eye_c)

        # --- Hair (Z 14..15) ---
        hair_c = self._c(hair_lo, hair_hi)
        for x in range(1, self.W - 1):
            for y in range(self.D):
                model.set(x, y, 14, hair_c)
                if self.H > 15:
                    model.set(x, y, 15, hair_c)

        # --- Weapon in right hand (extends from arm) ---
        if wpn_range:
            wpn_c = self._c(*wpn_range)
            # Simple vertical sword/staff extending above the hand
            if weapon in ("sword", "staff", "axe"):
                for z in range(4, 10):
                    model.set(self.W - 1, self.D // 2, z + 1, wpn_c)
            elif weapon == "bow":
                for z in range(4, 9):
                    model.set(self.W - 1, self.D // 2, z, wpn_c)
                    model.set(self.W - 1, 0, z + 2, wpn_c)  # bow arm

        return model
