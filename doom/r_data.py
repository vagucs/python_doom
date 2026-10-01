"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Textures, flats, colormaps (r_data.c).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .compat import as_i32
from .defs import FRACUNIT, PU_STATIC
from .wad import Wad


def _i32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def _i16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def _name8(data: bytes, off: int) -> str:
    raw = data[off : off + 8]
    if b"\x00" in raw:
        raw = raw.split(b"\x00", 1)[0]
    return raw.decode("latin1").rstrip(" ").upper()


@dataclass
class TexPatch:
    originx: int
    originy: int
    patch: int


@dataclass
class Texture:
    name: str
    width: int
    height: int
    patches: list[TexPatch] = field(default_factory=list)
    widthmask: int = 0
    columnofs: list[int] = field(default_factory=list)
    composite: bytes | bytearray | None = None
    # per-column: (lump, ofs) lump < 0 means composite
    col_lump: list[int] = field(default_factory=list)
    col_ofs: list[int] = field(default_factory=list)


class Resources:
    def __init__(self, wad: Wad) -> None:
        self.wad = wad
        self.textures: list[Texture] = []
        self.tex_index: dict[str, int] = {}
        self.flats_first = 0
        self.flats_last = 0
        self.flattranslation: list[int] = []
        self.texturetranslation: list[int] = []
        self.colormaps: bytes = b""
        self.skytexture = 0
        self.skyflatnum = 0
        self._patch_cache: dict[int, bytes] = {}
        self.sprites: dict = {}

    def init(self) -> None:
        from .sprites import init_sprite_defs

        self._init_textures()
        self._init_flats()
        self.colormaps = self.wad.cache_lump_name("COLORMAP")
        self.skyflatnum = self.flat_num_for_name("F_SKY1")
        sky = "SKY1"
        if self.wad.check_num_for_name("SKY1") >= 0:
            pass
        self.skytexture = self.texture_num_for_name(sky)
        self.sprites = init_sprite_defs(self.wad)

    def colormap(self, level: int) -> bytes:
        if level < 0:
            level = 0
        if level > 32:
            level = 32
        off = level * 256
        return self.colormaps[off : off + 256]

    def _init_flats(self) -> None:
        self.flats_first = self.wad.get_num_for_name("F_START") + 1
        self.flats_last = self.wad.get_num_for_name("F_END") - 1
        n = self.flats_last - self.flats_first + 1
        self.flattranslation = list(range(n))

    def flat_num_for_name(self, name: str) -> int:
        i = self.wad.check_num_for_name(name)
        if i < 0:
            return 0
        return i - self.flats_first

    def flat_lump(self, flatnum: int) -> int:
        if flatnum < 0:
            flatnum = 0
        n = self.flats_last - self.flats_first + 1
        if flatnum >= n:
            flatnum = 0
        return self.flats_first + self.flattranslation[flatnum]

    def _init_textures(self) -> None:
        pnames = self.wad.cache_lump_name("PNAMES")
        nummappatches = _i32(pnames, 0)
        patchlookup = []
        for i in range(nummappatches):
            name = _name8(pnames, 4 + i * 8)
            patchlookup.append(self.wad.check_num_for_name(name))

        maptex1 = self.wad.cache_lump_name("TEXTURE1")
        numtextures1 = _i32(maptex1, 0)
        maptex2 = b""
        numtextures2 = 0
        if self.wad.check_num_for_name("TEXTURE2") >= 0:
            maptex2 = self.wad.cache_lump_name("TEXTURE2")
            numtextures2 = _i32(maptex2, 0)

        directory1 = 4
        for i in range(numtextures1 + numtextures2):
            if i < numtextures1:
                offset = _i32(maptex1, directory1 + i * 4)
                src = maptex1
            else:
                offset = _i32(maptex2, 4 + (i - numtextures1) * 4)
                src = maptex2
            name = _name8(src, offset)
            width = _i16(src, offset + 12)
            height = _i16(src, offset + 14)
            patchcount = _i16(src, offset + 20)
            tex = Texture(name=name, width=width, height=height)
            poff = offset + 22
            for p in range(patchcount):
                ox = _i16(src, poff)
                oy = _i16(src, poff + 2)
                pidx = _i16(src, poff + 4)
                poff += 10
                lump = patchlookup[pidx] if 0 <= pidx < len(patchlookup) else -1
                tex.patches.append(TexPatch(ox, oy, lump))
            j = 1
            while j * 2 <= width:
                j *= 2
            tex.widthmask = j - 1
            tex.col_lump = [-1] * width
            tex.col_ofs = [0] * width
            self.tex_index[name] = len(self.textures)
            self.textures.append(tex)

        self.texturetranslation = list(range(len(self.textures)))
        for tex in self.textures:
            self._generate_lookup(tex)

    def _generate_lookup(self, tex: Texture) -> None:
        width = tex.width
        patchcount = [0] * width
        for mp in tex.patches:
            if mp.patch < 0:
                continue
            pdata = self.wad.cache_lump_num(mp.patch)
            pw = struct.unpack_from("<h", pdata, 0)[0]
            x1 = mp.originx
            x2 = x1 + pw
            x = 0 if x1 < 0 else x1
            if x2 > width:
                x2 = width
            while x < x2:
                patchcount[x] += 1
                tex.col_lump[x] = mp.patch
                tex.col_ofs[x] = struct.unpack_from("<I", pdata, 8 + (x - mp.originx) * 4)[0]
                x += 1
        for x in range(width):
            if patchcount[x] > 1:
                tex.col_lump[x] = -1

    def _generate_composite(self, tex: Texture) -> None:
        if tex.composite is not None:
            return
        buf = bytearray(tex.width * tex.height)
        for mp in tex.patches:
            if mp.patch < 0:
                continue
            pdata = self.wad.cache_lump_num(mp.patch)
            pw = struct.unpack_from("<h", pdata, 0)[0]
            x1 = mp.originx
            x2 = min(x1 + pw, tex.width)
            x = max(x1, 0)
            while x < x2:
                colofs = struct.unpack_from("<I", pdata, 8 + (x - mp.originx) * 4)[0]
                self._draw_column_in_cache(pdata, colofs, buf, x, mp.originy, tex)
                x += 1
        tex.composite = buf
        for x in range(tex.width):
            if tex.col_lump[x] < 0:
                tex.col_ofs[x] = x * tex.height

    def _draw_column_in_cache(
        self, patch: bytes, column: int, cache: bytearray, x: int, originy: int, tex: Texture
    ) -> None:
        while column < len(patch):
            topdelta = patch[column]
            if topdelta == 0xFF:
                break
            length = patch[column + 1]
            source = column + 3
            pos = originy + topdelta
            count = length
            if pos < 0:
                count += pos
                source -= pos
                pos = 0
            if pos + count > tex.height:
                count = tex.height - pos
            dest = x * tex.height + pos
            i = 0
            while i < count:
                cache[dest + i] = patch[source + i]
                i += 1
            column += length + 4

    def texture_num_for_name(self, name: str) -> int:
        key = name.upper().rstrip()[:8]
        if key == "-" or key == "":
            return 0
        return self.tex_index.get(key, 0)

    def texture_height(self, texnum: int) -> int:
        return self.textures[texnum].height * FRACUNIT

    def texture_width(self, texnum: int) -> int:
        return self.textures[texnum].width

    def column_posts(self, texnum: int, col: int) -> list[tuple[int, bytes]]:
        """Patch posts for R_DrawMaskedColumn (two-sided midtexture)."""
        if texnum <= 0 or texnum >= len(self.textures):
            return []
        tex = self.textures[texnum]
        col &= tex.widthmask
        lump = tex.col_lump[col]
        posts: list[tuple[int, bytes]] = []
        if lump >= 0:
            patch = self.wad.cache_lump_num(lump)
            column = tex.col_ofs[col]
            while column < len(patch):
                topdelta = patch[column]
                if topdelta == 0xFF:
                    break
                length = patch[column + 1]
                source = column + 3
                posts.append((topdelta, bytes(patch[source : source + length])))
                column += length + 4
            return posts
        self._generate_composite(tex)
        assert tex.composite is not None
        ofs = tex.col_ofs[col]
        colbytes = bytes(tex.composite[ofs : ofs + tex.height])
        if colbytes:
            posts.append((0, colbytes))
        return posts

    def get_column(self, texnum: int, col: int) -> bytes:
        tex = self.textures[texnum]
        col &= tex.widthmask
        lump = tex.col_lump[col]
        if lump >= 0:
            pdata = self.wad.cache_lump_num(lump)
            ofs = tex.col_ofs[col]
            # post column: skip to pixels — renderer uses 128-byte wrapped texture
            return self._column_to_source(pdata, ofs, tex.height)
        self._generate_composite(tex)
        assert tex.composite is not None
        ofs = tex.col_ofs[col]
        colbytes = bytes(tex.composite[ofs : ofs + tex.height])
        return self._repeat_column(colbytes)

    def _column_to_source(self, patch: bytes, column: int, height: int) -> bytes:
        buf = bytearray(128)
        while column < len(patch):
            topdelta = patch[column]
            if topdelta == 0xFF:
                break
            length = patch[column + 1]
            source = column + 3
            for i in range(length):
                y = topdelta + i
                if 0 <= y < 128:
                    buf[y] = patch[source + i]
            column += length + 4
        return bytes(buf)

    def _repeat_column(self, colbytes: bytes) -> bytes:
        buf = bytearray(128)
        if not colbytes:
            return bytes(buf)
        for i in range(128):
            buf[i] = colbytes[i % len(colbytes)]
        return bytes(buf)

    def flat_pixels(self, flatnum: int) -> bytes:
        lump = self.flat_lump(flatnum)
        data = self.wad.cache_lump_num(lump)
        if len(data) >= 4096:
            return data[:4096]
        return data + bytes(4096 - len(data))
