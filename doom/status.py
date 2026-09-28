"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Status bar (st_stuff / st_lib).
"""

from __future__ import annotations

from .defs import (
    AM_CELL,
    AM_CLIP,
    AM_MISL,
    AM_SHELL,
    HU_FONTEND,
    HU_FONTSTART,
    IT_BLUECARD,
    IT_BLUESKULL,
    IT_REDCARD,
    IT_REDSKULL,
    IT_YELLOWCARD,
    IT_YELLOWSKULL,
    SBARHEIGHT,
    SCREENHEIGHT,
    SCREENWIDTH,
    CF_GODMODE,
    WP_BFG,
    WP_CHAINGUN,
    WP_MISSILE,
    WP_PLASMA,
    WP_SHOTGUN,
    WP_SUPERSHOTGUN,
)
from .v_video import draw_patch, patch_size

ST_AMMOX, ST_AMMOY = 44, 171
ST_HEALTHX, ST_HEALTHY = 90, 171
ST_ARMORX, ST_ARMORY = 221, 171
ST_FACESX, ST_FACESY = 143, 168
ST_ARMSBGX, ST_ARMSBGY = 104, 168
ST_ARMSX, ST_ARMSY = 111, 172
ST_ARMSXSPACE, ST_ARMSYSPACE = 12, 10
ST_KEY0X, ST_KEY0Y = 239, 171
ST_AMMO0X, ST_AMMO0Y = 288, 173
ST_MAXAMMO0X, ST_MAXAMMO0Y = 314, 173
ST_AMMO_POS = [(288, 173), (288, 179), (288, 191), (288, 185)]
ST_MAX_POS = [(314, 173), (314, 179), (314, 191), (314, 185)]


class StatusBar:
    def __init__(self, wad) -> None:
        self.wad = wad
        self.sbar = wad.cache_lump_name("STBAR")
        self.tallnum = [wad.cache_lump_name(f"STTNUM{i}") for i in range(10)]
        self.shortnum = [wad.cache_lump_name(f"STYSNUM{i}") for i in range(10)]
        self.tallpercent = wad.cache_lump_name("STTPRCNT")
        self.keys = []
        for i in range(6):
            n = wad.check_num_for_name(f"STKEYS{i}")
            self.keys.append(wad.cache_lump_num(n) if n >= 0 else None)
        self.armsbg = wad.cache_lump_name("STARMS") if wad.check_num_for_name("STARMS") >= 0 else None
        self.arms_off = [wad.cache_lump_name(f"STGNUM{i}") for i in range(2, 8)]
        self.face = wad.cache_lump_name("STFST00")
        self.faces = []
        for pain in range(5):
            n = wad.check_num_for_name(f"STFST{pain}0")
            self.faces.append(wad.cache_lump_num(n) if n >= 0 else self.face)
        n = wad.check_num_for_name("STFGOD0")
        self.god_face = wad.cache_lump_num(n) if n >= 0 else self.face
        n = wad.check_num_for_name("STFDEAD0")
        self.dead_face = wad.cache_lump_num(n) if n >= 0 else None
        self.font = []
        for ch in range(HU_FONTSTART, HU_FONTEND + 1):
            name = f"STCFN{ch:03d}"
            n = wad.check_num_for_name(name)
            self.font.append(wad.cache_lump_num(n) if n >= 0 else None)

    def draw(self, fb: bytearray, player, show_messages: bool = True) -> None:
        draw_patch(fb, 0, 168, self.sbar)
        if self.armsbg:
            draw_patch(fb, ST_ARMSBGX, ST_ARMSBGY, self.armsbg)
        ammo = 0
        from .player import WEAPON_AMMO

        at = WEAPON_AMMO.get(player.readyweapon)
        if at is not None:
            ammo = player.ammo[at]
        self._num(fb, ST_AMMOX, ST_AMMOY, ammo, 3, self.tallnum)
        self._num(fb, ST_HEALTHX, ST_HEALTHY, player.health, 3, self.tallnum)
        draw_patch(fb, ST_HEALTHX, ST_HEALTHY, self.tallpercent)
        self._num(fb, ST_ARMORX, ST_ARMORY, player.armorpoints, 3, self.tallnum)
        draw_patch(fb, ST_ARMORX, ST_ARMORY, self.tallpercent)
        owned = [
            player.weaponowned[WP_SHOTGUN] or player.weaponowned[WP_SUPERSHOTGUN],
            player.weaponowned[WP_CHAINGUN],
            player.weaponowned[WP_MISSILE],
            player.weaponowned[WP_PLASMA],
            player.weaponowned[WP_BFG],
            False,
        ]
        for i in range(6):
            x = ST_ARMSX + (i % 3) * ST_ARMSXSPACE
            y = ST_ARMSY + (i // 3) * ST_ARMSYSPACE
            if owned[i]:
                self._digit(fb, x, y, i + 2, self.shortnum)
            elif i < len(self.arms_off):
                draw_patch(fb, x, y, self.arms_off[i])
        health = min(100, max(0, player.health))
        pain = 0 if player.health <= 0 else min(4, ((100 - health) * 5) // 101)
        if player.health <= 0:
            if self.dead_face:
                draw_patch(fb, ST_FACESX, ST_FACESY, self.dead_face)
            elif self.faces:
                draw_patch(fb, ST_FACESX, ST_FACESY, self.faces[-1])
        elif player.cheats & CF_GODMODE:
            draw_patch(fb, ST_FACESX, ST_FACESY, self.god_face)
        elif pain < len(self.faces):
            draw_patch(fb, ST_FACESX, ST_FACESY, self.faces[pain])
        key_slots = [
            (IT_BLUECARD, IT_BLUESKULL, 0),
            (IT_YELLOWCARD, IT_YELLOWSKULL, 1),
            (IT_REDCARD, IT_REDSKULL, 2),
        ]
        for card, skull, slot in key_slots:
            y = ST_KEY0Y + slot * 10
            idx = skull if player.cards[skull] else card
            if player.cards[card] or player.cards[skull]:
                patch = self.keys[idx] if idx < len(self.keys) else None
                if patch:
                    draw_patch(fb, ST_KEY0X, y, patch)
        ammo_order = [AM_CLIP, AM_SHELL, AM_CELL, AM_MISL]
        for i, am in enumerate(ammo_order):
            ax, ay = ST_AMMO_POS[i]
            mx, my = ST_MAX_POS[i]
            self._num(fb, ax, ay, player.ammo[am], 3, self.shortnum)
            self._num(fb, mx, my, player.maxammo[am], 3, self.shortnum)
        if show_messages and player.message:
            self.draw_text(fb, 0, 0, player.message)

    def _digit(self, fb, x, y, n, font) -> None:
        n = max(0, min(9, n))
        draw_patch(fb, x, y, font[n])

    def _num(self, fb, x, y, value, digits, font) -> None:
        w, _, _, _ = patch_size(font[0])
        x -= w
        neg = value < 0
        value = abs(int(value))
        for _ in range(digits):
            draw_patch(fb, x, y, font[value % 10])
            x -= w
            value //= 10
            if value == 0:
                break

    def draw_text(self, fb, x, y, text: str) -> None:
        for ch in text.upper():
            idx = ord(ch) - HU_FONTSTART
            if 0 <= idx < len(self.font) and self.font[idx]:
                patch = self.font[idx]
                draw_patch(fb, x, y, patch)
                w, _, _, _ = patch_size(patch)
                x += w
            else:
                x += 4
