"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

DeHackEd / BEX subset (deh_main / deh_str / deh_misc / deh_cheat / deh_thing).
"""

from __future__ import annotations

import os
from typing import Optional

from .defs import TICRATE

SIGS = (
    "Patch File for DeHackEd v2.3",
    "Patch File for DeHackEd v3.0",
)

THING_DOOMED = {
    2: 3004,
    3: 9,
    4: 64,
    6: 66,
    9: 67,
    12: 3001,
    13: 3002,
    15: 3005,
    16: 3003,
    18: 69,
    19: 3006,
    20: 7,
    21: 68,
    22: 16,
    23: 71,
    24: 84,
    25: 72,
    31: 2035,
}

BEX_STRINGS = {
    "STSTR_DQDON": "Degreelessness Mode On",
    "STSTR_DQDOFF": "Degreelessness Mode Off",
    "STSTR_KFAADDED": "Very Happy Ammo Added",
    "STSTR_FAADDED": "Ammo Added",
    "STSTR_NCON": "No Clipping Mode ON",
    "STSTR_NCOFF": "No Clipping Mode OFF",
    "STSTR_BEHOLD": "invin visis rad allmap lite amp",
    "STSTR_BEHOLDX": "Power-up Toggled",
    "STSTR_CHOPPERS": "... doesn't suck - GM",
    "STSTR_CLEV": "Changing Level...",
    "STSTR_MUS": "Music Change",
    "STSTR_NOMUS": "IMPOSSIBLE SELECTION",
    "GOTSTIM": "Picked up a stimpack.",
    "GOTMEDIKIT": "Picked up a medikit.",
    "GOTHTHBONUS": "You pick up a health bonus.",
    "GOTARMBONUS": "You pick up an armor bonus.",
    "GOTARMOR": "Picked up the armor.",
    "GOTMEGA": "Picked up the MegaArmor!",
    "GOTSUPER": "Supercharge!",
    "GOTMSPHERE": "MegaSphere!",
    "GOTBERSERK": "Berserk!",
    "GOTINVUL": "Invulnerability!",
    "GOTINVIS": "Partial Invisibility",
    "GOTSUIT": "Radiation Shielding Suit",
    "GOTMAP": "Computer Area Map",
    "GOTVISOR": "Light Amplification Visor",
    "GGSAVED": "game saved.",
    "AMSTR_FOLLOWON": "Follow Mode ON",
    "AMSTR_FOLLOWOFF": "Follow Mode OFF",
    "AMSTR_GRIDON": "Grid ON",
    "AMSTR_GRIDOFF": "Grid OFF",
    "AMSTR_MARKSCLEARED": "All Marks Cleared",
    "MSGOFF": "Messages Off",
    "MSGON": "Messages On",
    "DETAILHI": "High detail",
    "DETAILLO": "Low detail",
    "GOTSHOTGUN": "You got the shotgun!",
    "GOTSHOTGUN2": "You got the super shotgun!",
    "GOTCHAINGUN": "You got the chaingun!",
    "GOTLAUNCHER": "You got the rocket launcher!",
    "GOTPLASMA": "You got the plasma gun!",
    "GOTBFG9000": "You got the BFG9000!",
    "GOTCHAINSAW": "A chainsaw!  Find some meat!",
}

MISC_KEYS = {
    "Initial Health": "initial_health",
    "Initial Bullets": "initial_bullets",
    "Max Health": "max_health",
    "Max Armor": "max_armor",
    "Green Armor Class": "green_armor_class",
    "Blue Armor Class": "blue_armor_class",
    "Max Soulsphere": "max_soulsphere",
    "Soulsphere Health": "soulsphere_health",
    "Megasphere Health": "megasphere_health",
    "God Mode Health": "god_mode_health",
    "IDFA Armor": "idfa_armor",
    "IDFA Armor Class": "idfa_armor_class",
    "IDKFA Armor": "idkfa_armor",
    "IDKFA Armor Class": "idkfa_armor_class",
    "BFG Cells/Shot": "bfg_cells_per_shot",
}


class CheatSeq:
    def __init__(self, action: str, sequence: str, param_chars: int = 0, deh_name: str | None = None) -> None:
        self.action = action
        self.sequence = sequence
        self.param_chars = param_chars
        self.deh_name = deh_name
        self.chars_read = 0
        self.param_buf = ""

    def feed(self, ch: str) -> Optional[str]:
        seq = self.sequence
        if not seq:
            return None
        if self.chars_read < len(seq):
            if ch == seq[self.chars_read]:
                self.chars_read += 1
            else:
                self.chars_read = 1 if ch == seq[0] else 0
            if self.chars_read < len(seq):
                return None
            if self.param_chars <= 0:
                self.chars_read = 0
                return ""
            return None
        if len(self.param_buf) < self.param_chars:
            self.param_buf += ch
        if len(self.param_buf) >= self.param_chars:
            buf = self.param_buf
            self.chars_read = 0
            self.param_buf = ""
            return buf
        return None


def make_cheats() -> list[CheatSeq]:
    return [
        CheatSeq("god", "iddqd", deh_name="iddqd"),
        CheatSeq("kfa", "idkfa", deh_name="idkfa"),
        CheatSeq("fa", "idfa", deh_name="idfa"),
        CheatSeq("noclip2", "idclip", deh_name="idclip"),
        CheatSeq("noclip", "idspispopd", deh_name="idspispopd"),
        CheatSeq("iddt", "iddt"),
        CheatSeq("beholdv", "idbeholdv"),
        CheatSeq("beholds", "idbeholds"),
        CheatSeq("beholdi", "idbeholdi"),
        CheatSeq("beholdr", "idbeholdr"),
        CheatSeq("beholda", "idbeholda"),
        CheatSeq("beholdl", "idbeholdl"),
        CheatSeq("behold", "idbehold", deh_name="idbehold"),
        CheatSeq("choppers", "idchoppers", deh_name="idchoppers"),
        CheatSeq("mypos", "idmypos", deh_name="idmypos"),
        CheatSeq("clev", "idclev", param_chars=2, deh_name="idclev"),
        CheatSeq("mus", "idmus", param_chars=2, deh_name="idmus"),
    ]


class _Ctx:
    def __init__(self, data: str, name: str) -> None:
        self.data = data
        self.name = name
        self.pos = 0
        self.line = 1
        self.had_error = False

    def get_char(self) -> int:
        if self.pos >= len(self.data):
            return -1
        ch = self.data[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ord(ch)

    def read_line(self, extended: bool = False) -> Optional[str]:
        if self.pos >= len(self.data):
            return None
        parts: list[str] = []
        while True:
            buf: list[str] = []
            while self.pos < len(self.data):
                ch = self.data[self.pos]
                self.pos += 1
                if ch == "\n":
                    self.line += 1
                    break
                if ch != "\r":
                    buf.append(ch)
            line = "".join(buf)
            if extended and line.endswith("\\"):
                parts.append(line[:-1] + "\n")
                if self.pos >= len(self.data):
                    break
                continue
            parts.append(line)
            break
        return "".join(parts)


class Dehacked:
    def __init__(self) -> None:
        self.files: list[str] = []
        self.nodeh = False
        self.dehlump = False
        self.apply_cheats = True
        self.allow_long_strings = False
        self.allow_long_cheats = False
        self.allow_extended_strings = False
        self.replacements: dict[str, str] = {}
        self.cheats = make_cheats()
        self.initial_health = 100
        self.initial_bullets = 50
        self.max_health = 200
        self.max_armor = 200
        self.green_armor_class = 1
        self.blue_armor_class = 2
        self.max_soulsphere = 200
        self.soulsphere_health = 100
        self.megasphere_health = 200
        self.god_mode_health = 100
        self.idfa_armor = 200
        self.idfa_armor_class = 2
        self.idkfa_armor = 200
        self.idkfa_armor_class = 2
        self.bfg_cells_per_shot = 40
        self.species_infighting = 0
        self.maxammo = [200, 50, 300, 50]
        self.clipammo = [10, 4, 20, 1]

    def string(self, text: str) -> str:
        return self.replacements.get(text, text)

    def add_replacement(self, from_text: str, to_text: str) -> None:
        self.replacements[from_text] = to_text

    def find_cheat(self, name: str) -> Optional[CheatSeq]:
        key = name.lower()
        for cheat in self.cheats:
            if cheat.deh_name == key:
                return cheat
        return None

    def load_file(self, path: str) -> None:
        with open(path, "rb") as handle:
            data = handle.read().decode("latin1", errors="replace")
        print(f" loading {path}")
        self._parse(_Ctx(data, path))

    def load_lump(self, wad, lumpnum: int) -> None:
        raw = wad.cache_lump_num(lumpnum)
        name = wad.lump_name(lumpnum)
        print(f" loading lump {name}")
        self._parse(_Ctx(raw.decode("latin1", errors="replace"), name))

    def load_after_iwad(self, wad, iwad_path: str) -> None:
        if not self.nodeh:
            base = os.path.splitext(os.path.basename(iwad_path))[0].lower()
            if base.startswith("chex"):
                sibling = os.path.join(os.path.dirname(iwad_path) or ".", "chex.deh")
                if os.path.isfile(sibling):
                    self.load_file(sibling)
            for i, lump in enumerate(wad.lumps):
                if lump.name == "DEHACKED":
                    self.load_lump(wad, i)
        for path in self.files:
            if os.path.isfile(path):
                self.load_file(path)
            else:
                print(f"DEH_LoadFile: Unable to open {path}")

    def _parse(self, ctx: _Ctx) -> None:
        self.allow_long_strings = False
        self.allow_long_cheats = False
        self.allow_extended_strings = False
        first = ctx.read_line(False)
        if first is None or first.strip() not in SIGS:
            print(f"{ctx.name}: This is not a valid dehacked patch file!")
            return
        section = None
        tag: object = None
        while not ctx.had_error:
            extended = section == "[STRINGS]"
            line = ctx.read_line(extended)
            if line is None:
                return
            stripped = line.lstrip(" \t")
            if stripped.startswith("#"):
                self._comment(stripped)
                continue
            if stripped.strip() == "":
                section = None
                tag = None
                continue
            if section is not None:
                self._parse_line(ctx, section, stripped, tag)
            else:
                word = stripped.split(None, 1)[0]
                if word.upper() == "[STRINGS]" and not self.allow_extended_strings:
                    section = None
                    continue
                section = word
                tag = self._start_section(ctx, word, stripped)

    def _comment(self, comment: str) -> None:
        if "*allow-long-strings*" in comment:
            self.allow_long_strings = True
        if "*allow-long-cheats*" in comment:
            self.allow_long_cheats = True
        if "*allow-extended-strings*" in comment:
            self.allow_extended_strings = True

    def _start_section(self, ctx: _Ctx, word: str, line: str) -> object:
        key = word.lower()
        if key == "thing":
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return None
        if key == "ammo":
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return None
        if key == "text":
            self._parse_text(ctx, line)
            return None
        return None

    def _parse_line(self, ctx: _Ctx, section: str, line: str, tag: object) -> None:
        key = section.lower()
        if key == "misc":
            self._parse_misc(line)
        elif key == "thing":
            self._parse_thing(line, tag)
        elif key == "ammo":
            self._parse_ammo(line, tag)
        elif key == "cheat":
            self._parse_cheat(line)
        elif key == "[strings]":
            self._parse_bex(line)
        elif key in ("frame", "pointer", "sound", "weapon"):
            return

    def _assignment(self, line: str) -> Optional[tuple[str, str]]:
        eq = line.find("=")
        if eq < 0:
            return None
        return line[:eq].strip(), line[eq + 1 :].strip()

    def _parse_misc(self, line: str) -> None:
        asg = self._assignment(line)
        if asg is None:
            return
        name, raw = asg
        try:
            value = int(raw)
        except ValueError:
            return
        if name.lower() == "monsters infight":
            if value == 221:
                self.species_infighting = 1
            elif value == 202:
                self.species_infighting = 0
            return
        field = None
        for label, attr in MISC_KEYS.items():
            if label.lower() == name.lower():
                field = attr
                break
        if field:
            setattr(self, field, value)

    def _parse_thing(self, line: str, tag: object) -> None:
        asg = self._assignment(line)
        if asg is None or not isinstance(tag, int):
            return
        name, raw = asg
        try:
            value = int(raw)
        except ValueError:
            return
        doomed = THING_DOOMED.get(tag)
        if doomed is None:
            return
        if name.lower() != "hit points":
            return
        from .info import MI_SPAWNHEALTH, MOBJINFO, mobj_type_for_doomednum
        from .mobj import INFO

        rec = INFO.get(doomed)
        if rec is not None:
            sprite, radius, height, _hp, flags, kind, extra = rec
            INFO[doomed] = (sprite, radius, height, value, flags, kind, extra)
        typ = mobj_type_for_doomednum(doomed)
        if typ >= 0:
            MOBJINFO[typ][MI_SPAWNHEALTH] = value

    def _parse_ammo(self, line: str, tag: object) -> None:
        asg = self._assignment(line)
        if asg is None or not isinstance(tag, int) or tag < 0 or tag > 3:
            return
        name, raw = asg
        try:
            value = int(raw)
        except ValueError:
            return
        if name.lower() == "max ammo":
            self.maxammo[tag] = value
        elif name.lower() == "per ammo":
            self.clipammo[tag] = value

    def _parse_cheat(self, line: str) -> None:
        asg = self._assignment(line)
        if asg is None or not self.apply_cheats:
            return
        cheat = self.find_cheat(asg[0])
        if cheat is None:
            return
        seq = ""
        for i, ch in enumerate(asg[1], start=1):
            code = ord(ch)
            if code == 0 or code == 0xFF:
                break
            if not self.allow_long_cheats and i > len(cheat.sequence):
                break
            seq += ch
        cheat.sequence = seq
        cheat.chars_read = 0
        cheat.param_buf = ""

    def _parse_bex(self, line: str) -> None:
        asg = self._assignment(line)
        if asg is None:
            return
        original = BEX_STRINGS.get(asg[0].upper())
        if original is None:
            return
        text = asg[1].replace("\\n", "\n")
        self.add_replacement(original, text)

    def _parse_text(self, ctx: _Ctx, line: str) -> None:
        parts = line.split()
        if len(parts) < 3:
            return
        try:
            n_from = int(parts[1])
            n_to = int(parts[2])
        except ValueError:
            return
        src = ""
        dst = ""
        for _ in range(n_from):
            code = ctx.get_char()
            if code < 0:
                break
            src += chr(code)
        for _ in range(n_to):
            code = ctx.get_char()
            if code < 0:
                break
            dst += chr(code)
        self.add_replacement(src, dst)


deh = Dehacked()


def deh_string(text: str) -> str:
    return deh.string(text)


INVULNTICS = 30 * TICRATE
INVISTICS = 60 * TICRATE
IRONTICS = 60 * TICRATE
INFRATICS = 120 * TICRATE
PW_INVULN = 0
PW_STRENGTH = 1
PW_INVIS = 2
PW_IRONFEET = 3
PW_ALLMAP = 4
PW_INFRARED = 5
NUMPOWERS = 6
POWER_TICS = (INVULNTICS, 1, INVISTICS, IRONTICS, 1, INFRATICS)
