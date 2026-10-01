"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

In-game menu (m_menu.prg subset): ESC, New Game, Options, Load, Save, Read This, Quit.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .defs import GS_LEVEL, HU_FONTSIZE, HU_FONTSTART, LOADSAVEEMPTY, SAVESTRINGSIZE
from .saveg import read_slot_description
from .v_video import draw_patch, patch_size

LINEHEIGHT = 16
SKULLXOFF = -32


@dataclass
class MenuItem:
    status: int
    name: str
    action: str
    alpha: int = 0


@dataclass
class MenuDef:
    items: list[MenuItem]
    routine: str
    x: int
    y: int
    last_on: int = 0
    prev: str | None = None


class Menu:
    def __init__(self, wad, sound, game) -> None:
        self.wad = wad
        self.sound = sound
        self.game = game
        self.active = False
        self.screen = "main"
        self.item_on = 0
        self.which_skull = 0
        self.skull_tics = 8
        self.epi = 0
        self.message: str | None = None
        self.message_confirm = False
        self.message_action: str | None = None
        self.save_strings = [LOADSAVEEMPTY] * 6
        self.save_slot_ok = [False] * 6
        self.save_string_enter = False
        self.save_slot = 0
        self.save_old_string = ""
        self.save_char_index = 0
        self.menus: dict[str, MenuDef] = {
            "main": MenuDef(
                [
                    MenuItem(1, "M_NGAME", "newgame", 110),
                    MenuItem(1, "M_OPTION", "options", 111),
                    MenuItem(1, "M_LOADG", "loadgame", 108),
                    MenuItem(1, "M_SAVEG", "savegame", 115),
                    MenuItem(1, "M_RDTHIS", "readthis", 114),
                    MenuItem(1, "M_QUITG", "quit", 113),
                ],
                "main",
                97,
                64,
            ),
            "episode": MenuDef(
                [
                    MenuItem(1, "M_EPI1", "episode", 107),
                    MenuItem(1, "M_EPI2", "episode", 116),
                    MenuItem(1, "M_EPI3", "episode", 105),
                    MenuItem(1, "M_EPI4", "episode", 116),
                ],
                "episode",
                48,
                63,
                prev="main",
            ),
            "skill": MenuDef(
                [
                    MenuItem(1, "M_JKILL", "skill", 105),
                    MenuItem(1, "M_ROUGH", "skill", 104),
                    MenuItem(1, "M_HURT", "skill", 104),
                    MenuItem(1, "M_ULTRA", "skill", 117),
                    MenuItem(1, "M_NMARE", "skill", 110),
                ],
                "skill",
                48,
                63,
                last_on=2,
                prev="episode",
            ),
            "options": MenuDef(
                [
                    MenuItem(1, "M_ENDGAM", "endgame", 101),
                    MenuItem(1, "M_MESSG", "messages", 109),
                    MenuItem(1, "M_DETAIL", "detail", 103),
                    MenuItem(2, "M_SCRNSZ", "scrnsize", 115),
                    MenuItem(-1, "", "", 0),
                    MenuItem(2, "M_MSENS", "mousesens", 109),
                    MenuItem(-1, "", "", 0),
                    MenuItem(1, "M_SVOL", "sound", 115),
                ],
                "options",
                60,
                37,
                prev="main",
            ),
            "sound": MenuDef(
                [
                    MenuItem(2, "M_SFXVOL", "sfxvol", 115),
                    MenuItem(-1, "", "", 0),
                    MenuItem(2, "M_MUSVOL", "musvol", 109),
                    MenuItem(-1, "", "", 0),
                ],
                "sound",
                80,
                64,
                prev="options",
            ),
            "load": MenuDef(
                [MenuItem(1, "", "loadslot") for _ in range(6)],
                "load",
                80,
                54,
                prev="main",
            ),
            "save": MenuDef(
                [MenuItem(1, "", "saveslot") for _ in range(6)],
                "save",
                80,
                54,
                prev="main",
            ),
            "read1": MenuDef(
                [MenuItem(1, "", "read2", 0)],
                "read1",
                280,
                185,
                prev="main",
            ),
            "read2": MenuDef(
                [MenuItem(1, "", "finishread", 0)],
                "read2",
                330,
                175,
                prev="read1",
            ),
        }
        if not self._has_episodes():
            self.menus["skill"].prev = "main"

    def _has_episodes(self) -> bool:
        if self.wad.check_num_for_name("MAP01") >= 0:
            return False
        return self.wad.check_num_for_name("E2M1") >= 0

    def _has(self, name: str) -> bool:
        return self.wad.check_num_for_name(name) >= 0

    def _patch(self, name: str) -> bytes | None:
        n = self.wad.check_num_for_name(name)
        if n < 0:
            return None
        return self.wad.cache_lump_num(n)

    def ticker(self) -> None:
        if not self.active:
            return
        self.skull_tics -= 1
        if self.skull_tics <= 0:
            self.which_skull ^= 1
            self.skull_tics = 8

    def start(self) -> None:
        if self.active:
            return
        self.active = True
        self.screen = "main"
        self.item_on = self.menus["main"].last_on
        self.message = None
        self.save_string_enter = False
        self.sound.play("swtchn")

    def clear(self) -> None:
        self.active = False
        self.message = None
        self.save_string_enter = False

    def responder(self, key: int, char: str = "") -> bool:
        if self.save_string_enter:
            return self._save_string_key(key, char)

        if self.message:
            if self.message_confirm:
                if key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                    action = self.message_action
                    self.message = None
                    if action == "quit":
                        self.game.running = False
                    elif action == "endgame":
                        self.game.return_to_title()
                    return True
                if key in (pygame.K_n, pygame.K_ESCAPE):
                    self.message = None
                    return True
                return True
            if key:
                self.message = None
                return True

        if key == pygame.K_F2:
            self._do_action("savegame", 0)
            return True
        if key == pygame.K_F3:
            self._do_action("loadgame", 0)
            return True
        if key == pygame.K_F1:
            self._open_help()
            return True

        if not self.active:
            if key == pygame.K_ESCAPE:
                self.start()
                return True
            return False

        menu = self.menus[self.screen]
        if key == pygame.K_ESCAPE:
            menu.last_on = self.item_on
            self.clear()
            self.sound.play("swtchx")
            return True
        if key == pygame.K_BACKSPACE:
            menu.last_on = self.item_on
            if menu.prev:
                self.screen = menu.prev
                self.item_on = self.menus[self.screen].last_on
                self.sound.play("swtchx")
            else:
                self.clear()
                self.sound.play("swtchx")
            return True
        if key == pygame.K_DOWN:
            n = len(menu.items)
            while True:
                self.item_on = (self.item_on + 1) % n
                self.sound.play("pstop")
                if menu.items[self.item_on].status != -1:
                    break
            return True
        if key == pygame.K_UP:
            n = len(menu.items)
            while True:
                self.item_on = (self.item_on - 1) % n
                self.sound.play("pstop")
                if menu.items[self.item_on].status != -1:
                    break
            return True
        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            item = menu.items[self.item_on]
            if item.status == 2 and item.action:
                self.sound.play("stnmov")
                self._do_action(item.action, 0 if key == pygame.K_LEFT else 1)
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            item = menu.items[self.item_on]
            if item.status:
                menu.last_on = self.item_on
                self.sound.play("pistol")
                self._do_action(item.action, 1 if item.status == 2 else self.item_on)
            return True
        return True

    def _do_action(self, action: str, choice: int) -> None:
        if action == "newgame":
            if self.wad.check_num_for_name("MAP01") >= 0 or not self._has_episodes():
                self.epi = 0
                self._goto("skill")
            else:
                self._goto("episode")
        elif action == "options":
            self._goto("options")
        elif action == "loadgame":
            self._open_load()
        elif action == "savegame":
            if self.game.gamestate != GS_LEVEL or self.game.player is None:
                self.sound.play("oof")
                return
            self._open_save()
        elif action == "loadslot":
            if not self.save_slot_ok[choice]:
                self.sound.play("oof")
                return
            if self.game.load_game(choice):
                self.clear()
            else:
                self.sound.play("oof")
        elif action == "saveslot":
            self._begin_save_name(choice)
        elif action == "readthis":
            self._goto("read1")
        elif action == "read2":
            if self._has("HELP1") and self.screen == "read1":
                self._goto("read2")
            else:
                self._goto("main")
        elif action == "finishread":
            self._goto("main")
        elif action == "quit":
            self.message = "ARE YOU SURE YOU WANT TO QUIT?"
            self.message_confirm = True
            self.message_action = "quit"
        elif action == "endgame":
            if self.game.gamestate != GS_LEVEL:
                self.sound.play("oof")
                return
            self.message = "END GAME?"
            self.message_confirm = True
            self.message_action = "endgame"
        elif action == "sound":
            self._goto("sound")
        elif action == "messages":
            self.game.show_messages = not self.game.show_messages
            if self.game.player:
                self.game.player.set_message(
                    "Messages On" if self.game.show_messages else "Messages Off"
                )
        elif action == "detail":
            self.game.detail_level = 0 if self.game.detail_level else 1
            self.game.apply_view_size()
            if self.game.player:
                self.game.player.set_message(
                    "High detail" if self.game.detail_level == 0 else "Low detail"
                )
        elif action == "scrnsize":
            if choice:
                if self.game.screen_size < 8:
                    self.game.screen_size += 1
            elif self.game.screen_size > 0:
                self.game.screen_size -= 1
            self.game.apply_view_size()
        elif action == "mousesens":
            if choice:
                if self.game.mouse_sensitivity < 9:
                    self.game.mouse_sensitivity += 1
            elif self.game.mouse_sensitivity > 0:
                self.game.mouse_sensitivity -= 1
        elif action == "sfxvol":
            vol = self.game.sound.sfx_volume
            vol = min(15, vol + 1) if choice else max(0, vol - 1)
            self.game.sound.set_sfx_volume(vol)
        elif action == "musvol":
            vol = self.game.sound.music_volume
            vol = min(15, vol + 1) if choice else max(0, vol - 1)
            self.game.sound.set_music_volume(vol)
        elif action == "episode":
            if not self._has("E2M1") and choice != 0:
                self.message = "ONLY AVAILABLE IN THE REGISTERED VERSION."
                self.message_confirm = False
                self.message_action = None
                self._goto("read1")
                return
            self.epi = choice
            self._goto("skill")
        elif action == "skill":
            self.game.start_new_game(choice, self.epi + 1, 1)
            self.clear()

    def _open_help(self) -> None:
        """F1 / key_menu_help: ReadDef1 (HELP2 no shareware 1.9)."""
        self.active = True
        self.message = None
        self.save_string_enter = False
        self.menus["read1"].last_on = 0
        self.screen = "read1"
        self.item_on = 0
        self.sound.play("swtchn")

    def _goto(self, name: str) -> None:
        self.menus[self.screen].last_on = self.item_on
        self.screen = name
        self.item_on = self.menus[name].last_on

    def _read_save_strings(self) -> None:
        load = self.menus["load"]
        save = self.menus["save"]
        for i in range(6):
            desc, ok = read_slot_description(self.game, i)
            self.save_strings[i] = desc
            self.save_slot_ok[i] = ok
            load.items[i].status = 1 if ok else 0
            save.items[i].status = 1

    def _open_load(self) -> None:
        self._read_save_strings()
        self.save_string_enter = False
        self.message = None
        if not self.active:
            self.active = True
            self.screen = "load"
            self.item_on = self.menus["load"].last_on
        else:
            self._goto("load")
        self.sound.play("swtchn")

    def _open_save(self) -> None:
        self._read_save_strings()
        self.save_string_enter = False
        self.message = None
        if not self.active:
            self.active = True
            self.screen = "save"
            self.item_on = self.menus["save"].last_on
        else:
            self._goto("save")
        self.sound.play("swtchn")

    def _begin_save_name(self, slot: int) -> None:
        self.save_string_enter = True
        self.save_slot = slot
        self.save_old_string = self.save_strings[slot]
        if self.save_strings[slot] == LOADSAVEEMPTY:
            self.save_strings[slot] = ""
        self.save_char_index = len(self.save_strings[slot])

    def _save_string_key(self, key: int, char: str) -> bool:
        slot = self.save_slot
        if key == pygame.K_BACKSPACE:
            if self.save_char_index > 0:
                self.save_char_index -= 1
                self.save_strings[slot] = self.save_strings[slot][: self.save_char_index]
            return True
        if key == pygame.K_ESCAPE:
            self.save_string_enter = False
            self.save_strings[slot] = self.save_old_string
            return True
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.save_string_enter = False
            if self.save_strings[slot]:
                self._do_save(slot)
            else:
                self.save_strings[slot] = self.save_old_string
            return True
        ch = (char or "").upper()
        if len(ch) != 1:
            return True
        code = ord(ch)
        if ch != " ":
            idx = code - HU_FONTSTART
            if idx < 0 or idx >= HU_FONTSIZE:
                return True
        name = self.save_strings[slot]
        if (
            32 <= code <= 127
            and self.save_char_index < SAVESTRINGSIZE - 1
            and self._string_width(name) < (SAVESTRINGSIZE - 2) * 8
        ):
            self.save_strings[slot] = name + ch
            self.save_char_index += 1
        return True

    def _do_save(self, slot: int) -> None:
        if self.game.save_game(slot, self.save_strings[slot]):
            self.clear()
        else:
            self.sound.play("oof")

    def _string_width(self, text: str) -> int:
        w = 0
        for ch in text.upper():
            c = ord(ch) - HU_FONTSTART
            if c < 0 or c >= HU_FONTSIZE:
                w += 4
                continue
            p = self._patch(f"STCFN{ord(ch):03d}")
            if p:
                pw, _h, _l, _t = patch_size(p)
                w += max(4, pw)
            else:
                w += 8
        return w

    def _write_text(self, fb: bytearray, x: int, y: int, text: str) -> int:
        xx = x
        for ch in text.upper():
            if ch == " ":
                xx += 4
                continue
            p = self._patch(f"STCFN{ord(ch):03d}")
            if p:
                draw_patch(fb, xx, y, p)
                pw, _h, _l, _t = patch_size(p)
                xx += max(4, pw)
            else:
                xx += 8
        return xx

    def _draw_saveload_border(self, fb: bytearray, x: int, y: int) -> None:
        left = self._patch("M_LSLEFT")
        mid = self._patch("M_LSCNTR")
        right = self._patch("M_LSRGHT")
        if left:
            draw_patch(fb, x - 8, y + 7, left)
        xx = x
        for _ in range(SAVESTRINGSIZE):
            if mid:
                draw_patch(fb, xx, y + 7, mid)
            xx += 8
        if right:
            draw_patch(fb, xx, y + 7, right)

    def _draw_save_slots(self, fb: bytearray, menu: MenuDef) -> None:
        for i in range(6):
            y = menu.y + LINEHEIGHT * i
            self._draw_saveload_border(fb, menu.x, y)
            name = self.save_strings[i]
            xx = self._write_text(fb, menu.x, y, name)
            if self.save_string_enter and i == self.save_slot:
                self._write_text(fb, xx, y, "_")

    def draw(self, fb: bytearray) -> None:
        if not self.active:
            return
        if self.message:
            self._draw_message(fb)
            return
        menu = self.menus[self.screen]
        if menu.routine == "main":
            p = self._patch("M_DOOM")
            if p:
                draw_patch(fb, 94, 2, p)
        elif menu.routine == "skill":
            p = self._patch("M_NEWG")
            if p:
                draw_patch(fb, 96, 14, p)
            p = self._patch("M_SKILL")
            if p:
                draw_patch(fb, 54, 38, p)
        elif menu.routine == "episode":
            p = self._patch("M_EPISOD")
            if p:
                draw_patch(fb, 54, 38, p)
        elif menu.routine == "options":
            p = self._patch("M_OPTTTL")
            if p:
                draw_patch(fb, 108, 15, p)
            g = self.game
            msg = "M_MSGON" if g.show_messages else "M_MSGOFF"
            p = self._patch(msg)
            if p:
                draw_patch(fb, menu.x + 120, menu.y + LINEHEIGHT * 1, p)
            det = "M_GDHIGH" if g.detail_level == 0 else "M_GDLOW"
            p = self._patch(det)
            if p:
                draw_patch(fb, menu.x + 175, menu.y + LINEHEIGHT * 2, p)
        elif menu.routine == "sound":
            p = self._patch("M_SVOL")
            if p:
                draw_patch(fb, 60, 38, p)
        elif menu.routine == "read1":
            lump = "HELP2" if self._has("HELP2") else "HELP1" if self._has("HELP1") else "HELP" if self._has("HELP") else "CREDIT"
            p = self._patch(lump)
            if p:
                draw_patch(fb, 0, 0, p)
        elif menu.routine == "read2":
            p = self._patch("HELP1") or self._patch("CREDIT")
            if p:
                draw_patch(fb, 0, 0, p)
        elif menu.routine == "load":
            p = self._patch("M_LOADG")
            if p:
                draw_patch(fb, 72, 28, p)
            self._draw_save_slots(fb, menu)
        elif menu.routine == "save":
            p = self._patch("M_SAVEG")
            if p:
                draw_patch(fb, 72, 28, p)
            self._draw_save_slots(fb, menu)

        if menu.routine not in ("read1", "read2", "load", "save"):
            y = menu.y
            for item in menu.items:
                if item.name:
                    p = self._patch(item.name)
                    if p:
                        draw_patch(fb, menu.x, y, p)
                y += LINEHEIGHT

        if menu.routine == "options":
            self._draw_thermo(fb, menu.x, menu.y + LINEHEIGHT * 4, 9, self.game.screen_size)
            self._draw_thermo(fb, menu.x, menu.y + LINEHEIGHT * 6, 10, self.game.mouse_sensitivity)
        elif menu.routine == "sound":
            self._draw_thermo(fb, menu.x, menu.y + LINEHEIGHT, 16, self.game.sound.sfx_volume)
            self._draw_thermo(fb, menu.x, menu.y + LINEHEIGHT * 3, 16, self.game.sound.music_volume)

        skull = "M_SKULL2" if self.which_skull else "M_SKULL1"
        p = self._patch(skull)
        if p and menu.routine not in ("read1", "read2"):
            draw_patch(
                fb,
                menu.x + SKULLXOFF,
                menu.y - 5 + self.item_on * LINEHEIGHT,
                p,
            )

    def _draw_thermo(self, fb: bytearray, x: int, y: int, width: int, dot: int) -> None:
        left = self._patch("M_THERML")
        mid = self._patch("M_THERMM")
        right = self._patch("M_THERMR")
        knob = self._patch("M_THERMO")
        xx = x
        if left:
            draw_patch(fb, xx, y, left)
        xx += 8
        for _ in range(width):
            if mid:
                draw_patch(fb, xx, y, mid)
            xx += 8
        if right:
            draw_patch(fb, xx, y, right)
        if knob:
            draw_patch(fb, x + 8 + max(0, min(width - 1, dot)) * 8, y, knob)

    def _draw_message(self, fb: bytearray) -> None:
        # Minimal overlay: darken a band and stamp STCFN glyphs if present.
        text = self.message or ""
        if self.message_confirm:
            text += "  (Y/N)"
        x = 10
        y = 80
        for ch in text:
            if ch == " ":
                x += 8
                continue
            lump = f"STCFN{ord(ch):03d}"
            p = self._patch(lump)
            if p:
                draw_patch(fb, x, y, p)
                from .v_video import patch_size

                w, _h, _l, _t = patch_size(p)
                x += max(4, w)
            else:
                x += 8
            if x > 300:
                x = 10
                y += 10
