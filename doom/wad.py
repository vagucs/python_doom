"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

WAD loader (w_wad / w_file_stdc). Lump names are 8-byte, case-insensitive.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field
from typing import Optional


def _name8(raw: bytes) -> str:
    if b"\x00" in raw:
        raw = raw.split(b"\x00", 1)[0]
    return raw.decode("latin1", errors="replace").rstrip(" ").upper()


@dataclass
class Lump:
    name: str
    position: int
    size: int
    cache: Optional[bytes] = None
    wad_path: str = ""


class Wad:
    def __init__(self) -> None:
        self.lumps: list[Lump] = []
        self._index: dict[str, int] = {}
        self._files: dict[str, object] = {}

    def add_file(self, path: str) -> None:
        path = os.path.abspath(path)
        with open(path, "rb") as f:
            header = f.read(12)
            ident = header[:4]
            if ident not in (b"IWAD", b"PWAD"):
                raise RuntimeError(f"not a WAD: {path}")
            numlumps, infotableofs = struct.unpack_from("<II", header, 4)
            f.seek(infotableofs)
            directory = f.read(numlumps * 16)
        start = len(self.lumps)
        for i in range(numlumps):
            off = i * 16
            pos, size = struct.unpack_from("<II", directory, off)
            name = _name8(directory[off + 8 : off + 16])
            self.lumps.append(Lump(name=name, position=pos, size=size, wad_path=path))
        for i in range(start, len(self.lumps)):
            self._index[self.lumps[i].name] = i

    def num_lumps(self) -> int:
        return len(self.lumps)

    def check_num_for_name(self, name: str) -> int:
        key = name.upper().split("\x00", 1)[0].rstrip(" ")[:8]
        return self._index.get(key, -1)

    def get_num_for_name(self, name: str) -> int:
        n = self.check_num_for_name(name)
        if n < 0:
            raise RuntimeError(f"lump not found: {name}")
        return n

    def lump_length(self, num: int) -> int:
        return self.lumps[num].size

    def cache_lump_num(self, num: int) -> bytes:
        lump = self.lumps[num]
        if lump.cache is None:
            with open(lump.wad_path, "rb") as f:
                f.seek(lump.position)
                lump.cache = f.read(lump.size)
        return lump.cache

    def cache_lump_name(self, name: str) -> bytes:
        return self.cache_lump_num(self.get_num_for_name(name))

    def lump_name(self, num: int) -> str:
        return self.lumps[num].name
