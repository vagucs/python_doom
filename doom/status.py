"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Status bar (st_stuff / st_lib), including vanilla HUD face widget.
"""

from __future__ import annotations

from .collision import angle_to
from .compat import as_u32
from .defs import (
    AM_CELL,
    AM_CLIP,
    AM_MISL,
    AM_SHELL,
    ANG45,
    ANG180,
    HU_FONTEND,
    HU_FONTSTART,
    IT_BLUECARD,
    IT_BLUESKULL,
    IT_REDCARD,
    IT_REDSKULL,
    IT_YELLOWCARD,
    IT_YELLOWSKULL,
    CF_GODMODE,
    TICRATE,
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

ST_NUMPAINFACES = 5
ST_NUMSTRAIGHTFACES = 3
ST_NUMTURNFACES = 2
ST_NUMSPECIALFACES = 3
ST_FACESTRIDE = ST_NUMSTRAIGHTFACES + ST_NUMTURNFACES + ST_NUMSPECIALFACES
ST_TURNOFFSET = ST_NUMSTRAIGHTFACES
ST_OUCHOFFSET = ST_TURNOFFSET + ST_NUMTURNFACES
ST_EVILGRINOFFSET = ST_OUCHOFFSET + 1
ST_RAMPAGEOFFSET = ST_EVILGRINOFFSET + 1
ST_GODFACE = ST_NUMPAINFACES * ST_FACESTRIDE
ST_DEADFACE = ST_GODFACE + 1
ST_EVILGRINCOUNT = 2 * TICRATE
ST_STRAIGHTFACECOUNT = TICRATE // 2
ST_TURNCOUNT = TICRATE
ST_RAMPAGEDELAY = 2 * TICRATE
ST_MUCHPAIN = 20


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
        self.fallback_face = wad.cache_lump_name("STFST00")
        self.faces = []
        for pain in range(ST_NUMPAINFACES):
            for look in range(ST_NUMSTRAIGHTFACES):
                self.faces.append(self._optional(f"STFST{pain}{look}"))
            self.faces.append(self._optional(f"STFTR{pain}0"))
            self.faces.append(self._optional(f"STFTL{pain}0"))
            self.faces.append(self._optional(f"STFOUCH{pain}"))
            self.faces.append(self._optional(f"STFEVL{pain}"))
            self.faces.append(self._optional(f"STFKILL{pain}"))
        self.faces.append(self._optional("STFGOD0"))
        self.faces.append(self._optional("STFDEAD0"))
        self.font = []
        for ch in range(HU_FONTSTART, HU_FONTEND + 1):
            name = f"STCFN{ch:03d}"
            n = wad.check_num_for_name(name)
            self.font.append(wad.cache_lump_num(n) if n >= 0 else None)
        self.reset(None)

    def _optional(self, name: str):
        n = self.wad.check_num_for_name(name)
        return self.wad.cache_lump_num(n) if n >= 0 else None

    def reset(self, player) -> None:
        self.face_index = 0
        self.face_count = 0
        self.face_priority = 0
        self.old_health = -1
        self.pain_old_health = -1
        self.last_calc = 0
        self.last_attackdown = -1
        self.old_weapons_owned = list(player.weaponowned) if player is not None else [False] * 9
        self.rnd = 1

    def ticker(self, player) -> None:
        if player is None:
            return
        self.rnd = (self.rnd * 1103515245 + 12345) & 0xFFFFFFFF
        st_random = (self.rnd >> 16) & 255
        self._update_face_widget(player, st_random)
        self.old_health = player.health

    def _face_patch(self, index: int):
        if 0 <= index < len(self.faces) and self.faces[index] is not None:
            return self.faces[index]
        return self.fallback_face

    def _calc_pain_offset(self, player) -> int:
        health = min(100, max(0, int(player.health)))
        if health != self.pain_old_health:
            self.last_calc = ST_FACESTRIDE * ((100 - health) * ST_NUMPAINFACES) // 101
            self.pain_old_health = health
        return self.last_calc

    def _update_face_widget(self, player, st_random: int) -> None:
        if self.face_priority < 10 and player.health <= 0:
            self.face_priority = 9
            self.face_index = ST_DEADFACE
            self.face_count = 1

        if self.face_priority < 9 and player.bonuscount:
            do_evil_grin = False
            n = min(len(self.old_weapons_owned), len(player.weaponowned))
            for i in range(n):
                if self.old_weapons_owned[i] != player.weaponowned[i]:
                    do_evil_grin = True
                    self.old_weapons_owned[i] = player.weaponowned[i]
            if do_evil_grin:
                self.face_priority = 8
                self.face_count = ST_EVILGRINCOUNT
                self.face_index = self._calc_pain_offset(player) + ST_EVILGRINOFFSET

        if (
            self.face_priority < 8
            and player.damagecount
            and getattr(player, "attacker", None) is not None
            and player.mo is not None
            and player.attacker is not player.mo
        ):
            self.face_priority = 7
            if player.health - self.old_health > ST_MUCHPAIN:
                self.face_count = ST_TURNCOUNT
                self.face_index = self._calc_pain_offset(player) + ST_OUCHOFFSET
            else:
                badguyangle = angle_to(player.mo.x, player.mo.y, player.attacker.x, player.attacker.y)
                if as_u32(badguyangle) > as_u32(player.mo.angle):
                    diffang = as_u32(badguyangle - player.mo.angle)
                    turn_right = diffang > as_u32(ANG180)
                else:
                    diffang = as_u32(player.mo.angle - badguyangle)
                    turn_right = diffang <= as_u32(ANG180)
                self.face_count = ST_TURNCOUNT
                self.face_index = self._calc_pain_offset(player)
                if diffang < as_u32(ANG45):
                    self.face_index += ST_RAMPAGEOFFSET
                elif turn_right:
                    self.face_index += ST_TURNOFFSET
                else:
                    self.face_index += ST_TURNOFFSET + 1

        if self.face_priority < 7 and player.damagecount:
            if player.health - self.old_health > ST_MUCHPAIN:
                self.face_priority = 7
                self.face_count = ST_TURNCOUNT
                self.face_index = self._calc_pain_offset(player) + ST_OUCHOFFSET
            else:
                self.face_priority = 6
                self.face_count = ST_TURNCOUNT
                self.face_index = self._calc_pain_offset(player) + ST_RAMPAGEOFFSET

        if self.face_priority < 6:
            if player.attackdown:
                if self.last_attackdown == -1:
                    self.last_attackdown = ST_RAMPAGEDELAY
                else:
                    self.last_attackdown -= 1
                    if self.last_attackdown == 0:
                        self.face_priority = 5
                        self.face_index = self._calc_pain_offset(player) + ST_RAMPAGEOFFSET
                        self.face_count = 1
                        self.last_attackdown = 1
            else:
                self.last_attackdown = -1

        if self.face_priority < 5 and (player.cheats & CF_GODMODE):
            self.face_priority = 4
            self.face_index = ST_GODFACE
            self.face_count = 1

        if self.face_count == 0:
            self.face_index = self._calc_pain_offset(player) + (st_random % 3)
            self.face_count = ST_STRAIGHTFACECOUNT
            self.face_priority = 0
        self.face_count -= 1

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
        draw_patch(fb, ST_FACESX, ST_FACESY, self._face_patch(self.face_index))
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
