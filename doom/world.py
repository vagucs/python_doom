"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Map load (p_setup.prg) — vertexes, linedefs, sidedefs, sectors, segs, nodes, things.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .compat import shar
from .defs import (
    ANG45,
    BOXBOTTOM,
    BOXLEFT,
    BOXRIGHT,
    BOXTOP,
    FRACUNIT,
    MAPBLOCKSHIFT,
    MAPLINEDEF_SIZE,
    MAPNODE_SIZE,
    MAPSECTOR_SIZE,
    MAPSEG_SIZE,
    MAPSIDEDEF_SIZE,
    MAPSUBSECTOR_SIZE,
    MAPTHING_SIZE,
    MAPVERTEX_SIZE,
    MAXRADIUS,
    ML_TWOSIDED,
)
from .r_data import Resources
from .wad import Wad


def _i16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _name8(data: bytes, off: int) -> str:
    raw = data[off : off + 8]
    if b"\x00" in raw:
        raw = raw.split(b"\x00", 1)[0]
    return raw.decode("latin1").rstrip(" ").upper()


@dataclass
class Vertex:
    x: int = 0
    y: int = 0


@dataclass
class Sector:
    floorheight: int = 0
    ceilingheight: int = 0
    floorpic: int = 0
    ceilingpic: int = 0
    lightlevel: int = 0
    special: int = 0
    tag: int = 0
    lines: list = field(default_factory=list)
    specialdata: object | None = None
    soundorg: object | None = None
    # P_GroupLines: mapblock indices [LEFT, RIGHT, BOTTOM, TOP] for P_ChangeSector.
    blockbox: list = field(default_factory=lambda: [0, 0, 0, 0])
    i_sector: int = 0
    validcount: int = 0
    soundtraversed: int = 0
    soundtarget: object | None = None


@dataclass
class Side:
    textureoffset: int = 0
    rowoffset: int = 0
    toptexture: int = 0
    bottomtexture: int = 0
    midtexture: int = 0
    sector: Sector | None = None


@dataclass
class Line:
    v1: Vertex | None = None
    v2: Vertex | None = None
    dx: int = 0
    dy: int = 0
    flags: int = 0
    special: int = 0
    tag: int = 0
    sidenum: list = field(default_factory=lambda: [-1, -1])
    bbox: list = field(default_factory=lambda: [0, 0, 0, 0])
    slopetype: int = 0
    frontsector: Sector | None = None
    backsector: Sector | None = None
    sides: list = field(default_factory=list)
    i_line: int = 0
    validcount: int = 0


@dataclass
class Seg:
    v1: Vertex | None = None
    v2: Vertex | None = None
    offset: int = 0
    angle: int = 0
    sidedef: Side | None = None
    linedef: Line | None = None
    frontsector: Sector | None = None
    backsector: Sector | None = None


@dataclass
class Subsector:
    numlines: int = 0
    firstline: int = 0
    sector: Sector | None = None


@dataclass
class Node:
    x: int = 0
    y: int = 0
    dx: int = 0
    dy: int = 0
    bbox: list = field(default_factory=lambda: [[0, 0, 0, 0], [0, 0, 0, 0]])
    children: list = field(default_factory=lambda: [0, 0])


@dataclass
class MapThing:
    x: int = 0
    y: int = 0
    angle: int = 0
    type: int = 0
    options: int = 0


class World:
    def __init__(self) -> None:
        self.vertexes: list[Vertex] = []
        self.sectors: list[Sector] = []
        self.sides: list[Side] = []
        self.lines: list[Line] = []
        self.segs: list[Seg] = []
        self.subsectors: list[Subsector] = []
        self.nodes: list[Node] = []
        self.things: list[MapThing] = []
        self.numnodes = 0
        self.blockmap: list[int] = []
        self.bmaporgx = self.bmaporgy = 0
        self.bmapwidth = self.bmapheight = 0
        self.blockmaplump: list = []
        self.blocklinks: list = []
        self.validcount = 0
        self.mobjs: list = []
        self.rejectmatrix: bytes = b""

    def setup_level(self, wad: Wad, res: Resources, episode: int, mapn: int) -> None:
        if wad.check_num_for_name(f"MAP{mapn:02d}") >= 0:
            lumpname = f"MAP{mapn:02d}"
        else:
            lumpname = f"E{episode}M{mapn}"
        lumpnum = wad.get_num_for_name(lumpname)
        self._load_vertexes(wad.cache_lump_num(lumpnum + 4))
        self._load_sectors(wad.cache_lump_num(lumpnum + 8), res)
        self._load_sides(wad.cache_lump_num(lumpnum + 3), res)
        self._load_lines(wad.cache_lump_num(lumpnum + 2))
        self._load_segs(wad.cache_lump_num(lumpnum + 5))
        self._load_subsectors(wad.cache_lump_num(lumpnum + 6))
        self._load_nodes(wad.cache_lump_num(lumpnum + 7))
        self._load_things(wad.cache_lump_num(lumpnum + 1))
        self._load_blockmap(wad.cache_lump_num(lumpnum + 10))
        self._load_reject(wad.cache_lump_num(lumpnum + 9))
        self.numnodes = len(self.nodes)
        for ss in self.subsectors:
            ss.sector = self.segs[ss.firstline].frontsector
        self._group_lines_blockboxes()

    def _load_vertexes(self, data: bytes) -> None:
        n = len(data) // MAPVERTEX_SIZE
        self.vertexes = []
        for i in range(n):
            self.vertexes.append(
                Vertex(_i16(data, i * 4) * FRACUNIT, _i16(data, i * 4 + 2) * FRACUNIT)
            )

    def _load_sectors(self, data: bytes, res: Resources) -> None:
        n = len(data) // MAPSECTOR_SIZE
        self.sectors = []
        for i in range(n):
            o = i * MAPSECTOR_SIZE
            s = Sector()
            s.floorheight = _i16(data, o) * FRACUNIT
            s.ceilingheight = _i16(data, o + 2) * FRACUNIT
            s.floorpic = res.flat_num_for_name(_name8(data, o + 4))
            s.ceilingpic = res.flat_num_for_name(_name8(data, o + 12))
            s.lightlevel = _i16(data, o + 20)
            s.special = _i16(data, o + 22)
            s.tag = _i16(data, o + 24)
            s.i_sector = i
            self.sectors.append(s)

    def _load_sides(self, data: bytes, res: Resources) -> None:
        n = len(data) // MAPSIDEDEF_SIZE
        self.sides = []
        for i in range(n):
            o = i * MAPSIDEDEF_SIZE
            sd = Side()
            sd.textureoffset = _i16(data, o) * FRACUNIT
            sd.rowoffset = _i16(data, o + 2) * FRACUNIT
            sd.toptexture = res.texture_num_for_name(_name8(data, o + 4))
            sd.bottomtexture = res.texture_num_for_name(_name8(data, o + 12))
            sd.midtexture = res.texture_num_for_name(_name8(data, o + 20))
            sec = _i16(data, o + 28)
            sd.sector = self.sectors[sec] if 0 <= sec < len(self.sectors) else self.sectors[0]
            self.sides.append(sd)

    def _load_lines(self, data: bytes) -> None:
        n = len(data) // MAPLINEDEF_SIZE
        self.lines = []
        for i in range(n):
            o = i * MAPLINEDEF_SIZE
            ln = Line()
            v1, v2 = _i16(data, o), _i16(data, o + 2)
            ln.v1, ln.v2 = self.vertexes[v1], self.vertexes[v2]
            ln.dx = ln.v2.x - ln.v1.x
            ln.dy = ln.v2.y - ln.v1.y
            ln.flags = _i16(data, o + 4)
            ln.special = _i16(data, o + 6)
            ln.tag = _i16(data, o + 8)
            s0, s1 = _i16(data, o + 10), _i16(data, o + 12)
            ln.sidenum = [s0, s1]
            ln.frontsector = self.sides[s0].sector if s0 >= 0 else None
            ln.backsector = self.sides[s1].sector if s1 >= 0 else None
            ln.sides = [
                self.sides[s0] if s0 >= 0 else None,
                self.sides[s1] if s1 >= 0 else None,
            ]
            ln.bbox = [0, 0, 0, 0]
            if ln.v1.x < ln.v2.x:
                ln.bbox[BOXLEFT] = ln.v1.x
                ln.bbox[BOXRIGHT] = ln.v2.x
            else:
                ln.bbox[BOXLEFT] = ln.v2.x
                ln.bbox[BOXRIGHT] = ln.v1.x
            if ln.v1.y < ln.v2.y:
                ln.bbox[BOXBOTTOM] = ln.v1.y
                ln.bbox[BOXTOP] = ln.v2.y
            else:
                ln.bbox[BOXBOTTOM] = ln.v2.y
                ln.bbox[BOXTOP] = ln.v1.y
            ln.i_line = i
            if ln.frontsector is not None:
                ln.frontsector.lines.append(ln)
            if ln.backsector is not None and ln.backsector is not ln.frontsector:
                ln.backsector.lines.append(ln)
            self.lines.append(ln)

    def _load_segs(self, data: bytes) -> None:
        n = len(data) // MAPSEG_SIZE
        self.segs = []
        for i in range(n):
            o = i * MAPSEG_SIZE
            sg = Seg()
            sg.v1 = self.vertexes[_i16(data, o)]
            sg.v2 = self.vertexes[_i16(data, o + 2)]
            sg.angle = (_i16(data, o + 4) << 16) & 0xFFFFFFFF
            ln = self.lines[_i16(data, o + 6)]
            sg.linedef = ln
            side = _i16(data, o + 8)
            sg.offset = _i16(data, o + 10) * FRACUNIT
            sg.sidedef = ln.sides[side] if ln.sides[side] else ln.sides[0]
            sg.frontsector = sg.sidedef.sector if sg.sidedef else None
            if ln.flags & ML_TWOSIDED:
                sg.backsector = ln.sides[side ^ 1].sector if ln.sides[side ^ 1] else None
            else:
                sg.backsector = None
            self.segs.append(sg)

    def _load_subsectors(self, data: bytes) -> None:
        n = len(data) // MAPSUBSECTOR_SIZE
        self.subsectors = []
        for i in range(n):
            o = i * MAPSUBSECTOR_SIZE
            self.subsectors.append(
                Subsector(numlines=_u16(data, o), firstline=_u16(data, o + 2))
            )

    def _load_nodes(self, data: bytes) -> None:
        n = len(data) // MAPNODE_SIZE
        self.nodes = []
        for i in range(n):
            o = i * MAPNODE_SIZE
            nd = Node()
            nd.x = _i16(data, o) * FRACUNIT
            nd.y = _i16(data, o + 2) * FRACUNIT
            nd.dx = _i16(data, o + 4) * FRACUNIT
            nd.dy = _i16(data, o + 6) * FRACUNIT
            # WAD order is BOXTOP, BOXBOTTOM, BOXLEFT, BOXRIGHT (vanilla).
            # Remap into defs indices used elsewhere (LEFT, RIGHT, BOTTOM, TOP).
            nd.bbox = []
            p = o + 8
            for _ in range(2):
                top = _i16(data, p) * FRACUNIT
                bot = _i16(data, p + 2) * FRACUNIT
                left = _i16(data, p + 4) * FRACUNIT
                right = _i16(data, p + 6) * FRACUNIT
                box = [0, 0, 0, 0]
                box[BOXLEFT] = left
                box[BOXRIGHT] = right
                box[BOXBOTTOM] = bot
                box[BOXTOP] = top
                nd.bbox.append(box)
                p += 8
            nd.children = [_u16(data, p), _u16(data, p + 2)]
            self.nodes.append(nd)

    def _load_things(self, data: bytes) -> None:
        n = len(data) // MAPTHING_SIZE
        self.things = []
        for i in range(n):
            o = i * MAPTHING_SIZE
            self.things.append(
                MapThing(
                    x=_i16(data, o),
                    y=_i16(data, o + 2),
                    angle=_i16(data, o + 4),
                    type=_i16(data, o + 6),
                    options=_i16(data, o + 8),
                )
            )

    def _load_blockmap(self, data: bytes) -> None:
        n = len(data) // 2
        lump = [int.from_bytes(data[i * 2 : i * 2 + 2], "little", signed=False) for i in range(n)]
        self.blockmaplump = lump
        self.blockmap = []
        self.blocklinks = []
        if n < 4:
            return
        self.bmaporgx = _i16(data, 0) * FRACUNIT
        self.bmaporgy = _i16(data, 2) * FRACUNIT
        self.bmapwidth = _i16(data, 4)
        self.bmapheight = _i16(data, 6)
        count = self.bmapwidth * self.bmapheight
        self.blockmap = lump[4 : 4 + count]
        self.blocklinks = [None] * count

    def _load_reject(self, data: bytes) -> None:
        self.rejectmatrix = data or b""

    def _group_lines_blockboxes(self) -> None:
        """P_GroupLines: soundorg + sector blockbox for P_ChangeSector (Harbour/PHP)."""
        if self.bmapwidth <= 0 or self.bmapheight <= 0:
            return
        for sector in self.sectors:
            left = right = bottom = top = None
            for li in sector.lines:
                if li.v1 is None or li.v2 is None:
                    continue
                for v in (li.v1, li.v2):
                    left = v.x if left is None or v.x < left else left
                    right = v.x if right is None or v.x > right else right
                    bottom = v.y if bottom is None or v.y < bottom else bottom
                    top = v.y if top is None or v.y > top else top
            if left is None:
                sector.blockbox = [0, 0, 0, 0]
                continue
            sector.soundorg = type("SoundOrg", (), {"x": (right + left) // 2, "y": (top + bottom) // 2})()
            block = shar(top - self.bmaporgy + MAXRADIUS, MAPBLOCKSHIFT)
            if block >= self.bmapheight:
                block = self.bmapheight - 1
            boxtop = max(0, block)
            block = shar(bottom - self.bmaporgy - MAXRADIUS, MAPBLOCKSHIFT)
            boxbottom = max(0, block)
            block = shar(right - self.bmaporgx + MAXRADIUS, MAPBLOCKSHIFT)
            if block >= self.bmapwidth:
                block = self.bmapwidth - 1
            boxright = max(0, block)
            block = shar(left - self.bmaporgx - MAXRADIUS, MAPBLOCKSHIFT)
            boxleft = max(0, block)
            sector.blockbox = [0, 0, 0, 0]
            sector.blockbox[BOXLEFT] = boxleft
            sector.blockbox[BOXRIGHT] = boxright
            sector.blockbox[BOXBOTTOM] = boxbottom
            sector.blockbox[BOXTOP] = boxtop

    def player_start(self) -> MapThing | None:
        for t in self.things:
            if t.type == 1:
                return t
        return self.things[0] if self.things else None
