"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Sound effects from DS* lumps (i_allegrosound.prg CacheSFX) and MUS music.
"""

from __future__ import annotations

import array
import os
import struct
import sys
import tempfile
from typing import Optional

import pygame

from .mus2mid import mus2mid
from .wad import Wad

DOOM2_MUSIC = (
    "runnin",
    "stalks",
    "countd",
    "betwee",
    "doom",
    "the_da",
    "shawn",
    "ddtblu",
    "in_cit",
    "dead",
    "stlks2",
    "theda2",
    "doom2",
    "ddtbl2",
    "runni2",
    "dead2",
    "stlks3",
    "romero",
    "shawn2",
    "messag",
    "count2",
    "ddtbl3",
    "ampie",
    "theda3",
    "adrian",
    "messg2",
    "romer2",
    "tense",
    "shawn3",
    "openin",
    "evil",
    "ultima",
)


class Sound:
    def __init__(self) -> None:
        self.wad: Optional[Wad] = None
        self._cache: dict[str, Optional[pygame.mixer.Sound]] = {}
        self.enabled = True
        self.music_enabled = True
        self._init = False
        self._freq = 11025
        self._channels = 1
        self._music_path: Optional[str] = None
        self._music_name = ""
        self._music_loop = False
        self._music_backend = ""  # "mci" | "pygame" | ""
        self.sfx_volume = 8
        self.music_volume = 8

    def init(self, wad: Wad) -> None:
        self.wad = wad
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=11025, size=-16, channels=1, buffer=512)
            info = pygame.mixer.get_init()
            if info:
                self._freq, _size, self._channels = info[0], info[1], info[2]
            pygame.mixer.set_num_channels(8)
            self._init = True
            self.set_sfx_volume(self.sfx_volume)
            self.set_music_volume(self.music_volume)
        except pygame.error:
            self.enabled = False

    def play(self, name: str) -> None:
        if not self.enabled or not self._init or not self.wad:
            return
        snd = self._get(name)
        if snd is not None:
            try:
                snd.set_volume(self.sfx_volume / 15.0)
                snd.play()
            except pygame.error:
                pass

    def play_title_music(self) -> None:
        if not self.wad:
            return
        if self.wad.check_num_for_name("MAP01") >= 0:
            self.change_music("dm2ttl", looping=False)
        elif self.wad.check_num_for_name("D_INTROA") >= 0:
            self.change_music("introa", looping=False)
        else:
            self.change_music("intro", looping=False)

    def play_level_music(self, episode: int, mapn: int) -> None:
        if not self.wad:
            return
        if self.wad.check_num_for_name("MAP01") >= 0:
            name = DOOM2_MUSIC[(max(1, mapn) - 1) % len(DOOM2_MUSIC)]
        else:
            name = f"e{episode}m{mapn}"
        self.change_music(name, looping=True)

    def has_music(self, name: str) -> bool:
        if not self.wad or not name:
            return False
        return self.wad.check_num_for_name("D_" + name.upper()[:6]) >= 0

    def change_music(self, name: str, looping: bool = True) -> None:
        if not self.music_enabled or not self.wad or not name:
            return
        if name.lower() == self._music_name:
            return
        lump = "D_" + name.upper()[:6]
        n = self.wad.check_num_for_name(lump)
        if n < 0:
            return
        midi = mus2mid(self.wad.cache_lump_num(n))
        if not midi:
            return
        self.stop_music()
        fd, path = tempfile.mkstemp(suffix=".mid")
        os.close(fd)
        with open(path, "wb") as f:
            f.write(midi)
        self._music_path = path
        self._music_name = name.lower()
        self._music_loop = looping
        if sys.platform == "win32" and _mci_play(path):
            self._music_backend = "mci"
            self.set_music_volume(self.music_volume)
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1 if looping else 0)
            self._music_backend = "pygame"
            self.set_music_volume(self.music_volume)
        except pygame.error:
            self._music_backend = ""

    def set_sfx_volume(self, vol: int) -> None:
        self.sfx_volume = max(0, min(15, vol))

    def set_music_volume(self, vol: int) -> None:
        self.music_volume = max(0, min(15, vol))
        level = self.music_volume / 15.0
        try:
            pygame.mixer.music.set_volume(level)
        except pygame.error:
            pass
        if self._music_backend == "mci":
            _mci(f"setaudio doommus volume to {int(level * 1000)}")

    def stop_music(self) -> None:
        if self._music_backend == "mci":
            _mci("close doommus")
        elif self._music_backend == "pygame":
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
        self._music_backend = ""
        self._music_name = ""
        if self._music_path:
            try:
                os.remove(self._music_path)
            except OSError:
                pass
            self._music_path = None

    def update(self) -> None:
        if self._music_backend == "mci" and self._music_loop and self._music_path:
            mode = _mci_status("status doommus mode")
            if mode and mode != "playing":
                _mci("play doommus from 0")

    def _get(self, name: str) -> Optional[pygame.mixer.Sound]:
        key = name.lower()
        if key in self._cache:
            return self._cache[key]
        lump = f"DS{key.upper()[:6]}"
        n = self.wad.check_num_for_name(lump)
        if n < 0:
            self._cache[key] = None
            return None
        data = self.wad.cache_lump_num(n)
        snd = _ds_to_sound(data, self._freq, self._channels)
        self._cache[key] = snd
        return snd


def _mci(cmd: str) -> int:
    try:
        import ctypes

        return int(ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None))
    except Exception:
        return 1


def _mci_status(cmd: str) -> str:
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(64)
        if ctypes.windll.winmm.mciSendStringW(cmd, buf, 64, None):
            return ""
        return buf.value
    except Exception:
        return ""


def _mci_play(path: str) -> bool:
    _mci("close doommus")
    quoted = path.replace("/", "\\")
    if _mci(f'open "{quoted}" type sequencer alias doommus'):
        if _mci(f'open "{quoted}" alias doommus'):
            return False
    return _mci("play doommus from 0") == 0


def _ds_to_sound(data: bytes, mix_rate: int, mix_ch: int) -> Optional[pygame.mixer.Sound]:
    """Harbour CacheSFX: header 8 bytes, skip 16 pad, drop 16 pad at end."""
    if len(data) < 8 or data[0] != 3 or data[1] != 0:
        return None
    rate = data[2] + data[3] * 256
    length = struct.unpack_from("<I", data, 4)[0]
    if length > len(data) - 8 or length <= 48:
        return None
    length -= 32
    samples = data[16 : 16 + length]
    if not samples or rate <= 0:
        return None
    if mix_rate != rate:
        out_n = max(1, int(len(samples) * mix_rate / rate))
        src = samples
        converted = array.array("h")
        for i in range(out_n):
            src_i = min(len(src) - 1, i * len(src) // out_n)
            converted.append((src[src_i] - 128) << 8)
    else:
        converted = array.array("h", ((b - 128) << 8 for b in samples))
    if mix_ch >= 2:
        stereo = array.array("h")
        for s in converted:
            stereo.append(s)
            stereo.append(s)
        converted = stereo
    raw = converted.tobytes()
    frame = 2 * max(1, mix_ch)
    if len(raw) % frame:
        raw += b"\x00" * (frame - len(raw) % frame)
    try:
        return pygame.mixer.Sound(buffer=raw)
    except pygame.error:
        return None
