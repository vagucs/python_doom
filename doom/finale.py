"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

End-of-episode text (f_finale.prg, condensed).
"""

from __future__ import annotations

import pygame

from .defs import HU_FONTEND, HU_FONTSTART, HU_FONTSIZE, SCREENWIDTH
from .v_video import draw_patch, fill, patch_size

TEXTSPEED = 3
TEXTWAIT = 250
STAGE_TEXT = 0
STAGE_ART = 1

E1TEXT = (
    "Once you beat the big badasses and\n"
    "clean out the moon base you're supposed\n"
    "to win, aren't you? Aren't you? Where's\n"
    "your fat reward and ticket home? What\n"
    "the hell is this? It's not supposed to\n"
    "end this way!\n"
    "\n"
    "It stinks like rotten meat, but looks\n"
    "like the lost Deimos base.  Looks like\n"
    "you're stuck on The Shores of Hell.\n"
    "The only way out is through.\n"
    "\n"
    "To continue the DOOM experience, play\n"
    "The Shores of Hell and its amazing\n"
    "sequel, Inferno!\n"
)

E2TEXT = (
    "You've done it! The hideous cyber-\n"
    "demon lord that ruled the lost Deimos\n"
    "moon base has been slain and you\n"
    "are triumphant! But ... where are\n"
    "you? You clamber to the edge of the\n"
    "moon and look down to see the awful\n"
    "truth.\n"
    "\n"
    "Deimos floats above Hell itself!\n"
    "You've never heard of anyone escaping\n"
    "from Hell, but you'll make the bastards\n"
    "sorry they ever heard of you! Quickly,\n"
    "you rappel down to  the surface of\n"
    "Hell.\n"
    "\n"
    "Now, it's on to the final chapter of\n"
    "DOOM! -- Inferno.\n"
)

E3TEXT = (
    "The loathsome spiderdemon that\n"
    "masterminded the invasion of the moon\n"
    "bases and caused so much death has had\n"
    "its ass kicked for all time.\n"
    "\n"
    "A hidden doorway opens and you enter.\n"
    "You've proven too tough for Hell to\n"
    "contain, and now Hell at last plays\n"
    "fair -- for you emerge from the door\n"
    "to see the green fields of Earth!\n"
    "Home at last.\n"
    "\n"
    "You wonder what's been happening on\n"
    "Earth while you were battling evil\n"
    "unleashed. It's good that no Hell-\n"
    "spawn could have come through that\n"
    "door with you ...\n"
)

C1TEXT = (
    "You have won! Your victory has enabled\n"
    "humankind to evacuate Earth and escape\n"
    "the nightmare.  Now you are the only\n"
    "human left on the face of the planet.\n"
    "Can you defeat the final enemy and\n"
    "return to Earth, or will you just\n"
    "rot here with the rest of the walking\n"
    "dead?\n"
)


class Finale:
    def __init__(self, game) -> None:
        self.game = game
        self.stage = STAGE_TEXT
        self.count = 0
        self.done = False
        commercial = game.wad.check_num_for_name("MAP01") >= 0
        if commercial:
            self.text = C1TEXT
            self.flat = "SLIME16"
            game.sound.change_music("read_m", looping=True)
        else:
            texts = {1: E1TEXT, 2: E2TEXT, 3: E3TEXT}
            flats = {1: "FLOOR4_8", 2: "SFLR6_1", 3: "MFLR8_4"}
            self.text = texts.get(game.episode, E1TEXT)
            self.flat = flats.get(game.episode, "FLOOR4_8")
            game.sound.change_music("victor", looping=True)
        self._flat_lump = None
        n = game.wad.check_num_for_name(self.flat)
        if n >= 0:
            self._flat_lump = game.wad.cache_lump_num(n)
        self._art = None
        art = "CREDIT" if game.wad.check_num_for_name("CREDIT") >= 0 else "HELP2"
        n = game.wad.check_num_for_name(art)
        if n < 0:
            n = game.wad.check_num_for_name("HELP1")
        if n >= 0:
            self._art = game.wad.cache_lump_num(n)

    def ticker(self) -> None:
        self.count += 1
        if self.stage == STAGE_TEXT:
            if self.count > len(self.text) * TEXTSPEED + TEXTWAIT:
                self.stage = STAGE_ART
                self.count = 0
                self.game.force_wipe = True
        elif self.stage == STAGE_ART:
            if self._want_skip() and self.count > 10:
                self.done = True

    def _want_skip(self) -> bool:
        if self.game.menu and self.game.menu.active:
            return False
        k = self.game.keys
        return bool(
            pygame.K_LCTRL in k
            or pygame.K_RCTRL in k
            or pygame.K_SPACE in k
            or pygame.K_RETURN in k
            or pygame.K_KP_ENTER in k
            or pygame.K_e in k
        )

    def draw(self, fb: bytearray) -> None:
        if self.stage == STAGE_ART and self._art:
            fill(fb, 0)
            draw_patch(fb, 0, 0, self._art)
            return
        self._draw_text(fb)

    def _fill_flat(self, fb: bytearray) -> None:
        lump = self._flat_lump
        if not lump or len(lump) < 4096:
            fill(fb, 0)
            return
        for y in range(200):
            row = (y & 63) << 6
            dest = y * SCREENWIDTH
            for x in range(0, SCREENWIDTH, 64):
                n = min(64, SCREENWIDTH - x)
                fb[dest + x : dest + x + n] = lump[row : row + n]

    def _draw_text(self, fb: bytearray) -> None:
        self._fill_flat(fb)
        nshow = self.count // TEXTSPEED
        cx, cy = 10, 10
        for i, ch in enumerate(self.text):
            if i >= nshow:
                break
            if ch == "\n":
                cx = 10
                cy += 11
                continue
            code = ord(ch.upper())
            if ch == " " or code < HU_FONTSTART or code > HU_FONTEND:
                cx += 4
                continue
            p = self._font(code)
            if not p:
                cx += 4
                continue
            w, _h, _l, _t = patch_size(p)
            if cx + w > SCREENWIDTH:
                break
            draw_patch(fb, cx, cy, p)
            cx += w

    def _font(self, code: int):
        if code - HU_FONTSTART < 0 or code - HU_FONTSTART >= HU_FONTSIZE:
            return None
        n = self.game.wad.check_num_for_name(f"STCFN{code:03d}")
        if n < 0:
            return None
        return self.game.wad.cache_lump_num(n)
