"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Collision, use-lines and hitscan (p_map / p_maputl).
"""

from __future__ import annotations

from .compat import as_i32, as_u32, fixed_div, fixed_mul, shar
from .defs import (
    ANGLETOFINESHIFT,
    ANG180,
    BOXBOTTOM,
    BOXLEFT,
    BOXRIGHT,
    BOXTOP,
    FINEMASK,
    FRACBITS,
    FRACUNIT,
    MAXMOVE,
    MAXSTEP,
    MAPBLOCKSHIFT,
    MAPBLOCKSIZE,
    MAPBTOFRAC,
    MAXRADIUS,
    PT_ADDLINES,
    PT_ADDTHINGS,
    PT_EARLYOUT,
    MF_DROPOFF,
    MF_FLOAT,
    MF_MISSILE,
    MF_NOBLOCKMAP,
    MF_NOBLOOD,
    MF_NOCLIP,
    MF_PICKUP,
    MF_SHOOTABLE,
    MF_SKULLFLY,
    MF_SOLID,
    MF_SPECIAL,
    MF_TELEPORT,
    ML_BLOCKING,
    ML_BLOCKMONSTERS,
    ML_TWOSIDED,
    NF_SUBSECTOR,
    PLAYER_HEIGHT,
    USERANGE,
)
from .tables import fine_cos, fine_sin


def point_on_side(x: int, y: int, node) -> int:
    dx = as_i32(x - node.x)
    dy = as_i32(y - node.y)
    left = as_i32(node.dy >> 16) * dx
    right = dy * as_i32(node.dx >> 16)
    return 1 if right >= left else 0


def point_in_subsector(world, x: int, y: int):
    nodenum = world.numnodes - 1
    if nodenum < 0:
        return world.subsectors[0]
    while not (nodenum & NF_SUBSECTOR):
        node = world.nodes[nodenum]
        nodenum = node.children[point_on_side(x, y, node)]
    return world.subsectors[nodenum & ~NF_SUBSECTOR]


def point_on_line_side(x: int, y: int, line) -> int:
    if line.dx == 0:
        if x <= line.v1.x:
            return 1 if line.dy > 0 else 0
        return 1 if line.dy < 0 else 0
    if line.dy == 0:
        if y <= line.v1.y:
            return 1 if line.dx < 0 else 0
        return 1 if line.dx > 0 else 0
    dx = as_i32(x - line.v1.x)
    dy = as_i32(y - line.v1.y)
    left = fixed_mul(line.dy >> FRACBITS, dx)
    right = fixed_mul(dy, line.dx >> FRACBITS)
    return 0 if right < left else 1


def box_on_line_side(bbox: list[int], line) -> int:
    if line.dx == 0:
        p1 = 0 if bbox[BOXRIGHT] < line.v1.x else 1
        p2 = 0 if bbox[BOXLEFT] < line.v1.x else 1
        if line.dy > 0:
            p1 ^= 1
            p2 ^= 1
    elif line.dy == 0:
        p1 = 0 if bbox[BOXTOP] > line.v1.y else 1
        p2 = 0 if bbox[BOXBOTTOM] > line.v1.y else 1
        if line.dx < 0:
            p1 ^= 1
            p2 ^= 1
    else:
        slopetype = 0 if (line.dy > 0) == (line.dx > 0) else 1
        if slopetype == 0:
            p1 = point_on_line_side(bbox[BOXLEFT], bbox[BOXTOP], line)
            p2 = point_on_line_side(bbox[BOXRIGHT], bbox[BOXBOTTOM], line)
        else:
            p1 = point_on_line_side(bbox[BOXRIGHT], bbox[BOXTOP], line)
            p2 = point_on_line_side(bbox[BOXLEFT], bbox[BOXBOTTOM], line)
    if p1 == p2:
        return p1
    return -1


def line_opening(line) -> tuple[int, int, int]:
    """Return (opentop, openbottom, lowfloor)."""
    if line.backsector is None:
        return 0, 0, 0
    front, back = line.frontsector, line.backsector
    opentop = min(front.ceilingheight, back.ceilingheight)
    if front.floorheight > back.floorheight:
        return opentop, front.floorheight, back.floorheight
    return opentop, back.floorheight, front.floorheight


class MoveCheck:
    def __init__(self) -> None:
        self.floorz = 0
        self.ceilingz = 0
        self.dropoffz = 0
        self.spechit: list = []
        self.blocked = False
        self.hit_thing = None
        self.ceilingline = None
        self.bbox = [0, 0, 0, 0]


floatok = False
tmfloorz = 0
last_spechit: list = []
ceilingline = None


def unset_thing_position(world, thing) -> None:
    """P_UnsetThingPosition: drop the thing from its blockmap cell."""
    if not getattr(thing, "blocklinked", False):
        return
    nxt = thing.bnext
    prev = thing.bprev
    if nxt is not None:
        nxt.bprev = prev
    if prev is not None:
        prev.bnext = nxt
    else:
        i = getattr(thing, "_bindex", -1)
        links = getattr(world, "blocklinks", None) or []
        if 0 <= i < len(links) and links[i] is thing:
            links[i] = nxt
    thing.bnext = None
    thing.bprev = None
    thing.blocklinked = False


def set_thing_position(world, thing) -> None:
    """P_SetThingPosition: link the thing at the head of its block."""
    links = getattr(world, "blocklinks", None) or []
    thing.bnext = None
    thing.bprev = None
    thing.blocklinked = False
    if thing.flags & MF_NOBLOCKMAP or not links:
        return
    bx = shar(thing.x - world.bmaporgx, MAPBLOCKSHIFT)
    by = shar(thing.y - world.bmaporgy, MAPBLOCKSHIFT)
    if bx < 0 or by < 0 or bx >= world.bmapwidth or by >= world.bmapheight:
        return
    i = by * world.bmapwidth + bx
    head = links[i]
    thing.bnext = head
    if head is not None:
        head.bprev = thing
    links[i] = thing
    thing._bindex = i
    thing.blocklinked = True


def _block_things(world, x: int, y: int, func) -> bool:
    links = world.blocklinks
    if x < 0 or y < 0 or x >= world.bmapwidth or y >= world.bmapheight:
        return True
    mo = links[y * world.bmapwidth + x]
    while mo is not None:
        nxt = mo.bnext
        if not func(mo):
            return False
        mo = nxt
    return True


def _block_lines(world, x: int, y: int, func) -> bool:
    if x < 0 or y < 0 or x >= world.bmapwidth or y >= world.bmapheight:
        return True
    lump = world.blockmaplump
    offset = world.blockmap[y * world.bmapwidth + x]
    while 0 <= offset < len(lump):
        n = lump[offset]
        offset += 1
        if n == 0xFFFF:
            return True
        if n >= len(world.lines):
            continue
        ld = world.lines[n]
        if ld.validcount == world.validcount:
            continue
        ld.validcount = world.validcount
        if not func(ld):
            return False
    return True


def _pit_thing(world, tm, other, game) -> bool:
    """PIT_CheckThing. False stops the move."""
    if not (other.flags & (MF_SOLID | MF_SPECIAL | MF_SHOOTABLE)):
        return True
    blockdist = other.radius + tm.radius
    if abs(other.x - tm._tmx) >= blockdist or abs(other.y - tm._tmy) >= blockdist:
        return True
    if other is tm:
        return True
    if tm.flags & MF_SKULLFLY:
        from .enemy import p_random
        from .thinker import set_mobj_state

        dmg = ((p_random() % 8) + 1) * (tm.damage or 0)
        if game is not None:
            game.damage_mobj(other, tm, dmg, tm)
        tm.flags &= ~MF_SKULLFLY
        tm.momx = tm.momy = tm.momz = 0
        set_mobj_state(tm, _spawn_state(tm), world, game)
        return False
    if tm.flags & MF_MISSILE:
        if tm.z > other.z + other.height or tm.z + tm.height < other.z:
            return True
        target = tm.target
        if target is not None and _same_species(target, other):
            if other is target:
                return True
            from .info import MT_PLAYER

            if other.type != MT_PLAYER:
                return False
        if not (other.flags & MF_SHOOTABLE):
            return (other.flags & MF_SOLID) == 0
        from .enemy import p_random

        dmg = ((p_random() % 8) + 1) * (tm.damage or 0)
        if game is not None:
            game.damage_mobj(other, tm.target if tm.target is not None else tm, dmg, tm)
        return False
    if other.flags & MF_SPECIAL:
        solid = other.flags & MF_SOLID
        if (tm.flags & MF_PICKUP) and game is not None:
            game.touch_special(other, tm)
        return solid == 0
    return (other.flags & MF_SOLID) == 0


def _spawn_state(tm) -> int:
    from .info import MI_SPAWNSTATE, MOBJINFO

    return MOBJINFO[tm.type][MI_SPAWNSTATE]


def _same_species(target, other) -> bool:
    from .info import MT_BRUISER, MT_KNIGHT

    if target.type == other.type:
        return True
    if target.type == MT_KNIGHT and other.type == MT_BRUISER:
        return True
    return target.type == MT_BRUISER and other.type == MT_KNIGHT


def _pit_line(tm, chk: MoveCheck, ld) -> bool:
    bbox = chk.bbox
    if (
        bbox[BOXRIGHT] <= ld.bbox[BOXLEFT]
        or bbox[BOXLEFT] >= ld.bbox[BOXRIGHT]
        or bbox[BOXTOP] <= ld.bbox[BOXBOTTOM]
        or bbox[BOXBOTTOM] >= ld.bbox[BOXTOP]
    ):
        return True
    if box_on_line_side(bbox, ld) != -1:
        return True
    if ld.backsector is None:
        return False
    if not (tm.flags & MF_MISSILE):
        if ld.flags & ML_BLOCKING:
            return False
        if tm.player is None and (ld.flags & ML_BLOCKMONSTERS):
            return False
    opentop, openbottom, lowfloor = line_opening(ld)
    if opentop < chk.ceilingz:
        chk.ceilingz = opentop
        chk.ceilingline = ld
    if openbottom > chk.floorz:
        chk.floorz = openbottom
    if lowfloor < chk.dropoffz:
        chk.dropoffz = lowfloor
    if ld.special:
        chk.spechit.append(ld)
    return True


def check_position(world, thing, x: int, y: int, game=None) -> MoveCheck:
    """P_CheckPosition: things first (with MAXRADIUS), then lines, in blockmap order."""
    chk = MoveCheck()
    thing._tmx, thing._tmy = x, y
    radius = thing.radius
    bbox = chk.bbox
    bbox[BOXTOP] = y + radius
    bbox[BOXBOTTOM] = y - radius
    bbox[BOXRIGHT] = x + radius
    bbox[BOXLEFT] = x - radius
    sub = point_in_subsector(world, x, y)
    chk.floorz = sub.sector.floorheight
    chk.dropoffz = chk.floorz
    chk.ceilingz = sub.sector.ceilingheight
    world.validcount += 1
    if thing.flags & MF_NOCLIP:
        return chk
    links = getattr(world, "blocklinks", None) or []
    if not links:
        return chk
    orgx, orgy = world.bmaporgx, world.bmaporgy
    xl = shar(bbox[BOXLEFT] - orgx - MAXRADIUS, MAPBLOCKSHIFT)
    xh = shar(bbox[BOXRIGHT] - orgx + MAXRADIUS, MAPBLOCKSHIFT)
    yl = shar(bbox[BOXBOTTOM] - orgy - MAXRADIUS, MAPBLOCKSHIFT)
    yh = shar(bbox[BOXTOP] - orgy + MAXRADIUS, MAPBLOCKSHIFT)
    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not _block_things(world, bx, by, lambda th: _pit_thing(world, thing, th, game)):
                chk.blocked = True
                return chk
    xl = shar(bbox[BOXLEFT] - orgx, MAPBLOCKSHIFT)
    xh = shar(bbox[BOXRIGHT] - orgx, MAPBLOCKSHIFT)
    yl = shar(bbox[BOXBOTTOM] - orgy, MAPBLOCKSHIFT)
    yh = shar(bbox[BOXTOP] - orgy, MAPBLOCKSHIFT)
    for bx in range(xl, xh + 1):
        for by in range(yl, yh + 1):
            if not _block_lines(world, bx, by, lambda ld: _pit_line(thing, chk, ld)):
                chk.blocked = True
                return chk
    return chk


def try_move(world, thing, x: int, y: int, game=None) -> bool:
    """P_TryMove. Leaves floatok, tmfloorz, last_spechit and ceilingline for P_Move."""
    global floatok, tmfloorz, last_spechit, ceilingline
    floatok = False
    ceilingline = None
    chk = check_position(world, thing, x, y, game)
    last_spechit = chk.spechit
    tmfloorz = chk.floorz
    ceilingline = chk.ceilingline
    if chk.blocked:
        return False
    if not (thing.flags & MF_NOCLIP):
        if chk.ceilingz - chk.floorz < thing.height:
            return False
        floatok = True
        if not (thing.flags & MF_TELEPORT) and chk.ceilingz - thing.z < thing.height:
            return False
        if not (thing.flags & MF_TELEPORT) and chk.floorz - thing.z > MAXSTEP:
            return False
        if not (thing.flags & (MF_DROPOFF | MF_FLOAT)) and chk.floorz - chk.dropoffz > MAXSTEP:
            return False
    unset_thing_position(world, thing)
    oldx, oldy = thing.x, thing.y
    thing.floorz = chk.floorz
    thing.ceilingz = chk.ceilingz
    thing.x = x
    thing.y = y
    set_thing_position(world, thing)
    if game is not None and not (thing.flags & (MF_TELEPORT | MF_NOCLIP)):
        for ln in reversed(chk.spechit):
            side = point_on_line_side(thing.x, thing.y, ln)
            oldside = point_on_line_side(oldx, oldy, ln)
            if side != oldside and ln.special:
                game.cross_special(ln, oldside, thing)
    return True


class _Div:
    __slots__ = ("x", "y", "dx", "dy")

    def __init__(self, x: int, y: int, dx: int, dy: int) -> None:
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy


_earlyout = False
_intercepts: list[dict] = []
_trace = {"x": 0, "y": 0, "dx": 0, "dy": 0}
_INT_MAX = 0x7FFFFFFF


def _div_trace() -> _Div:
    return _Div(_trace["x"], _trace["y"], _trace["dx"], _trace["dy"])


def point_on_divline_side(x: int, y: int, line) -> int:
    """P_PointOnDivlineSide."""
    if line.dx == 0:
        if x <= line.x:
            return 1 if line.dy > 0 else 0
        return 1 if line.dy < 0 else 0
    if line.dy == 0:
        if y <= line.y:
            return 1 if line.dx < 0 else 0
        return 1 if line.dx > 0 else 0
    dx = x - line.x
    dy = y - line.y
    xor = as_u32(line.dy) ^ as_u32(line.dx) ^ as_u32(dx) ^ as_u32(dy)
    if xor & 0x80000000:
        return 1 if (as_u32(line.dy) ^ as_u32(dx)) & 0x80000000 else 0
    left = fixed_mul(shar(line.dy, 8), shar(dx, 8))
    right = fixed_mul(shar(dy, 8), shar(line.dx, 8))
    return 0 if right < left else 1


def intercept_vector(v2, v1) -> int:
    """P_InterceptVector: frac of v2 along v1."""
    den = as_i32(fixed_mul(shar(v1.dy, 8), v2.dx) - fixed_mul(shar(v1.dx, 8), v2.dy))
    if den == 0:
        return 0
    num = as_i32(
        fixed_mul(shar(v1.x - v2.x, 8), v1.dy) + fixed_mul(shar(v2.y - v1.y, 8), v1.dx)
    )
    return fixed_div(num, den)


def _add_line_intercept(ld) -> bool:
    big = 16 * FRACUNIT
    dx, dy = _trace["dx"], _trace["dy"]
    if dx > big or dy > big or dx < -big or dy < -big:
        tr = _div_trace()
        s1 = point_on_divline_side(ld.v1.x, ld.v1.y, tr)
        s2 = point_on_divline_side(ld.v2.x, ld.v2.y, tr)
    else:
        s1 = point_on_line_side(_trace["x"], _trace["y"], ld)
        s2 = point_on_line_side(_trace["x"] + dx, _trace["y"] + dy, ld)
    if s1 == s2:
        return True
    frac = intercept_vector(_div_trace(), _Div(ld.v1.x, ld.v1.y, ld.dx, ld.dy))
    if frac < 0:
        return True
    if _earlyout and frac < FRACUNIT and ld.backsector is None:
        return False
    _intercepts.append({"frac": frac, "isaline": True, "line": ld, "thing": None})
    return True


def _add_thing_intercept(thing) -> bool:
    tr = _div_trace()
    positive = as_i32(as_u32(tr.dx) ^ as_u32(tr.dy)) > 0
    if positive:
        x1, y1 = thing.x - thing.radius, thing.y + thing.radius
        x2, y2 = thing.x + thing.radius, thing.y - thing.radius
    else:
        x1, y1 = thing.x - thing.radius, thing.y - thing.radius
        x2, y2 = thing.x + thing.radius, thing.y + thing.radius
    if point_on_divline_side(x1, y1, tr) == point_on_divline_side(x2, y2, tr):
        return True
    frac = intercept_vector(tr, _Div(x1, y1, x2 - x1, y2 - y1))
    if frac < 0:
        return True
    _intercepts.append({"frac": frac, "isaline": False, "line": None, "thing": thing})
    return True


def _traverse_intercepts(func, maxfrac: int) -> bool:
    count = len(_intercepts)
    while count > 0:
        count -= 1
        dist = _INT_MAX
        chosen = None
        for scan in _intercepts:
            if scan["frac"] < dist:
                dist = scan["frac"]
                chosen = scan
        if dist > maxfrac:
            return True
        if chosen is None or not func(chosen):
            return False
        chosen["frac"] = _INT_MAX
    return True


def _abs32(n: int) -> int:
    n = as_i32(n)
    return -n if n < 0 else n


def path_traverse(world, x1: int, y1: int, x2: int, y2: int, flags: int, trav) -> bool:
    """P_PathTraverse: blockmap DDA, then intercepts from nearest to farthest."""
    global _earlyout
    _earlyout = (flags & PT_EARLYOUT) != 0
    world.validcount += 1
    _intercepts.clear()
    orgx, orgy = world.bmaporgx, world.bmaporgy
    if ((x1 - orgx) & (MAPBLOCKSIZE - 1)) == 0:
        x1 += FRACUNIT
    if ((y1 - orgy) & (MAPBLOCKSIZE - 1)) == 0:
        y1 += FRACUNIT
    _trace["x"] = x1
    _trace["y"] = y1
    _trace["dx"] = as_i32(x2 - x1)
    _trace["dy"] = as_i32(y2 - y1)
    x1 = as_i32(x1 - orgx)
    y1 = as_i32(y1 - orgy)
    xt1 = shar(x1, MAPBLOCKSHIFT)
    yt1 = shar(y1, MAPBLOCKSHIFT)
    x2m = as_i32(x2 - orgx)
    y2m = as_i32(y2 - orgy)
    xt2 = shar(x2m, MAPBLOCKSHIFT)
    yt2 = shar(y2m, MAPBLOCKSHIFT)
    if xt2 > xt1:
        mapxstep = 1
        partial = FRACUNIT - (shar(x1, MAPBTOFRAC) & (FRACUNIT - 1))
        ystep = fixed_div(as_i32(y2m - y1), _abs32(as_i32(x2m - x1)))
    elif xt2 < xt1:
        mapxstep = -1
        partial = shar(x1, MAPBTOFRAC) & (FRACUNIT - 1)
        ystep = fixed_div(as_i32(y2m - y1), _abs32(as_i32(x2m - x1)))
    else:
        mapxstep = 0
        partial = FRACUNIT
        ystep = 256 * FRACUNIT
    yintercept = as_i32(shar(y1, MAPBTOFRAC) + fixed_mul(partial, ystep))
    if yt2 > yt1:
        mapystep = 1
        partial = FRACUNIT - (shar(y1, MAPBTOFRAC) & (FRACUNIT - 1))
        xstep = fixed_div(as_i32(x2m - x1), _abs32(as_i32(y2m - y1)))
    elif yt2 < yt1:
        mapystep = -1
        partial = shar(y1, MAPBTOFRAC) & (FRACUNIT - 1)
        xstep = fixed_div(as_i32(x2m - x1), _abs32(as_i32(y2m - y1)))
    else:
        mapystep = 0
        partial = FRACUNIT
        xstep = 256 * FRACUNIT
    xintercept = as_i32(shar(x1, MAPBTOFRAC) + fixed_mul(partial, xstep))
    mapx, mapy = xt1, yt1
    for _count in range(64):
        if flags & PT_ADDLINES:
            if not _block_lines(world, mapx, mapy, _add_line_intercept):
                return False
        if flags & PT_ADDTHINGS:
            if not _block_things(world, mapx, mapy, _add_thing_intercept):
                return False
        if mapx == xt2 and mapy == yt2:
            break
        if shar(yintercept, FRACBITS) == mapy:
            yintercept = as_i32(yintercept + ystep)
            mapx += mapxstep
        elif shar(xintercept, FRACBITS) == mapx:
            xintercept = as_i32(xintercept + xstep)
            mapy += mapystep
    return _traverse_intercepts(trav, FRACUNIT)


def _slide_blocking(thing, line) -> bool:
    """PTR_SlideTraverse: one-sided walls and openings the body cannot pass."""
    if not (line.flags & ML_TWOSIDED):
        return point_on_line_side(thing.x, thing.y, line) == 0
    opentop, openbottom, _low = line_opening(line)
    if opentop - openbottom < thing.height:
        return True
    if opentop - thing.z < thing.height:
        return True
    if openbottom - thing.z > 24 * FRACUNIT:
        return True
    return False


def _slide_trace(world, thing, x1: int, y1: int, x2: int, y2: int, best: list) -> None:
    hits: list[tuple[int, object]] = []
    for ln in world.lines:
        frac = intercept_frac(x1, y1, x2, y2, ln)
        if frac is None or frac < 0 or frac > FRACUNIT:
            continue
        hits.append((frac, ln))
    hits.sort(key=lambda h: h[0])
    for frac, ln in hits:
        if not _slide_blocking(thing, ln):
            continue
        if frac < best[0]:
            best[0] = frac
            best[1] = ln
        return


def _hit_slide_line(thing, line, tmx: int, tmy: int) -> tuple[int, int]:
    """P_HitSlideLine: keep the part of the move that runs along the wall."""
    if line.dy == 0:
        return tmx, 0
    if line.dx == 0:
        return 0, tmy
    side = point_on_line_side(thing.x, thing.y, line)
    lineangle = angle_to(0, 0, line.dx, line.dy)
    if side == 1:
        lineangle = as_u32(lineangle + ANG180)
    moveangle = angle_to(0, 0, tmx, tmy)
    delta = as_u32(moveangle - lineangle)
    if delta > ANG180:
        delta = as_u32(delta + ANG180)
    newlen = fixed_mul(approx_distance(tmx, tmy), fine_cos(delta))
    return fixed_mul(newlen, fine_cos(lineangle)), fixed_mul(newlen, fine_sin(lineangle))


def _stairstep(world, thing, game) -> None:
    if not try_move(world, thing, thing.x, thing.y + thing.momy, game):
        try_move(world, thing, thing.x + thing.momx, thing.y, game)


def slide_move(world, thing, momx: int, momy: int, game=None) -> None:
    """P_SlideMove: ride the wall instead of dropping the blocked axis."""
    if abs(momx) > MAXMOVE:
        momx = MAXMOVE if momx > 0 else -MAXMOVE
    if abs(momy) > MAXMOVE:
        momy = MAXMOVE if momy > 0 else -MAXMOVE
    thing.momx = momx
    thing.momy = momy
    hitcount = 0
    while True:
        hitcount += 1
        if hitcount == 3:
            _stairstep(world, thing, game)
            return
        if thing.momx > 0:
            leadx = thing.x + thing.radius
            trailx = thing.x - thing.radius
        else:
            leadx = thing.x - thing.radius
            trailx = thing.x + thing.radius
        if thing.momy > 0:
            leady = thing.y + thing.radius
            traily = thing.y - thing.radius
        else:
            leady = thing.y - thing.radius
            traily = thing.y + thing.radius
        best = [FRACUNIT + 1, None]

        def _slide_trav(inn, thing=thing, best=best) -> bool:
            li = inn["line"]
            blocking = False
            if not (li.flags & ML_TWOSIDED):
                if point_on_line_side(thing.x, thing.y, li) != 0:
                    return True
                blocking = True
            else:
                opentop, openbottom, _low = line_opening(li)
                if opentop - openbottom < thing.height:
                    blocking = True
                elif opentop - thing.z < thing.height:
                    blocking = True
                elif openbottom - thing.z > 24 * FRACUNIT:
                    blocking = True
            if not blocking:
                return True
            if inn["frac"] < best[0]:
                best[0] = inn["frac"]
                best[1] = li
            return False

        mx, my = thing.momx, thing.momy
        path_traverse(world, leadx, leady, leadx + mx, leady + my, PT_ADDLINES, _slide_trav)
        path_traverse(world, trailx, leady, trailx + mx, leady + my, PT_ADDLINES, _slide_trav)
        path_traverse(world, leadx, traily, leadx + mx, traily + my, PT_ADDLINES, _slide_trav)
        if best[0] == FRACUNIT + 1 or best[1] is None:
            _stairstep(world, thing, game)
            return
        best[0] -= 0x800
        if best[0] > 0:
            newx = fixed_mul(thing.momx, best[0])
            newy = fixed_mul(thing.momy, best[0])
            if not try_move(world, thing, thing.x + newx, thing.y + newy, game):
                _stairstep(world, thing, game)
                return
        best[0] = FRACUNIT - (best[0] + 0x800)
        if best[0] > FRACUNIT:
            best[0] = FRACUNIT
        if best[0] <= 0:
            return
        tmx = fixed_mul(thing.momx, best[0])
        tmy = fixed_mul(thing.momy, best[0])
        tmx, tmy = _hit_slide_line(thing, best[1], tmx, tmy)
        thing.momx = tmx
        thing.momy = tmy
        if try_move(world, thing, thing.x + tmx, thing.y + tmy, game):
            return


def intercept_frac(x1, y1, x2, y2, line) -> int | None:
    """Return 16.16 frac along the trace where it hits the line, or None."""
    ax, ay = x1 / FRACUNIT, y1 / FRACUNIT
    bx, by = x2 / FRACUNIT, y2 / FRACUNIT
    cx, cy = line.v1.x / FRACUNIT, line.v1.y / FRACUNIT
    dx, dy = line.v2.x / FRACUNIT, line.v2.y / FRACUNIT
    den = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
    if abs(den) < 1e-8:
        return None
    t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / den
    u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / den
    if t < 0.0 or t > 1.0 or u < 0.0 or u > 1.0:
        return None
    return int(t * FRACUNIT)


def use_lines(world, player, game) -> None:
    """P_UseLines + PTR_UseTraverse along the blockmap."""
    mo = player.mo
    x1, y1 = mo.x, mo.y
    x2 = x1 + shar(USERANGE, FRACBITS) * fine_cos(mo.angle)
    y2 = y1 + shar(USERANGE, FRACBITS) * fine_sin(mo.angle)

    def _use(inn) -> bool:
        ln = inn["line"]
        if not ln.special:
            opentop, openbottom, _low = line_opening(ln)
            if opentop - openbottom <= 0:
                if game:
                    game.start_sound("noway")
                return False
            return True
        side = 1 if point_on_line_side(mo.x, mo.y, ln) == 1 else 0
        if game:
            game.use_special(ln, mo, side)
        return False

    path_traverse(world, x1, y1, x2, y2, PT_ADDLINES, _use)


def _shot_ends(source, angle: int, attackrange: int) -> tuple[int, int, int]:
    x2 = source.x + shar(attackrange, FRACBITS) * fine_cos(angle)
    y2 = source.y + shar(attackrange, FRACBITS) * fine_sin(angle)
    shootz = source.z + (source.height >> 1) + 8 * FRACUNIT
    return x2, y2, shootz


def _aim(world, source, angle: int, attackrange: int) -> tuple[int, object | None]:
    """PTR_AimTraverse over P_PathTraverse. Returns (aimslope, target)."""
    x2, y2, shootz = _shot_ends(source, angle, attackrange)
    window = (100 * FRACUNIT) // 160
    state = {"top": window, "bottom": -window, "slope": 0, "target": None}

    def _trav(inn) -> bool:
        if inn["isaline"]:
            li = inn["line"]
            if not (li.flags & ML_TWOSIDED):
                return False
            opentop, openbottom, _low = line_opening(li)
            if openbottom >= opentop:
                return False
            dist = fixed_mul(attackrange, inn["frac"])
            front, back = li.frontsector, li.backsector
            if back is None or front.floorheight != back.floorheight:
                slope = fixed_div(openbottom - shootz, dist)
                if slope > state["bottom"]:
                    state["bottom"] = slope
            if back is None or front.ceilingheight != back.ceilingheight:
                slope = fixed_div(opentop - shootz, dist)
                if slope < state["top"]:
                    state["top"] = slope
            return state["top"] > state["bottom"]
        th = inn["thing"]
        if th is source or not (th.flags & MF_SHOOTABLE):
            return True
        dist = fixed_mul(attackrange, inn["frac"])
        thingtop = fixed_div(th.z + th.height - shootz, dist)
        if thingtop < state["bottom"]:
            return True
        thingbot = fixed_div(th.z - shootz, dist)
        if thingbot > state["top"]:
            return True
        if thingtop > state["top"]:
            thingtop = state["top"]
        if thingbot < state["bottom"]:
            thingbot = state["bottom"]
        state["slope"] = (thingtop + thingbot) // 2
        state["target"] = th
        return False

    path_traverse(world, source.x, source.y, x2, y2, PT_ADDLINES | PT_ADDTHINGS, _trav)
    if state["target"] is not None:
        return state["slope"], state["target"]
    return 0, None


def bullet_slope(world, source) -> int:
    """P_BulletSlope: aim straight, then a step left and right."""
    base = source.angle
    span = 16 * 64 * FRACUNIT
    for ang in (base, as_u32(base + (1 << 26)), as_u32(base - (1 << 26))):
        slope, target = _aim(world, source, ang, span)
        if target is not None:
            return slope
    return 0


def line_attack(
    world,
    source,
    damage: int,
    game,
    attackrange: int,
    angle: int | None = None,
    slope: int | None = None,
) -> bool:
    """P_LineAttack. slope None aims along the shot. A passed slope is P_GunShot's bulletslope."""
    ang = source.angle if angle is None else angle
    aimslope = _aim(world, source, ang, attackrange)[0] if slope is None else slope
    x2, y2, shootz = _shot_ends(source, ang, attackrange)
    sky = getattr(getattr(game, "res", None), "skyflatnum", -1) if game is not None else -1
    hit = {"ok": False}

    def _shoot(inn) -> bool:
        if inn["isaline"]:
            li = inn["line"]
            if li.special and game is not None:
                game.shoot_special(li, source)
            hit_line = False
            if not (li.flags & ML_TWOSIDED):
                hit_line = True
            else:
                opentop, openbottom, _low = line_opening(li)
                dist = fixed_mul(attackrange, inn["frac"])
                front, back = li.frontsector, li.backsector
                if back is None:
                    if fixed_div(openbottom - shootz, dist) > aimslope:
                        hit_line = True
                    elif fixed_div(opentop - shootz, dist) < aimslope:
                        hit_line = True
                else:
                    if front.floorheight != back.floorheight and fixed_div(openbottom - shootz, dist) > aimslope:
                        hit_line = True
                    if (
                        not hit_line
                        and front.ceilingheight != back.ceilingheight
                        and fixed_div(opentop - shootz, dist) < aimslope
                    ):
                        hit_line = True
            if not hit_line:
                return True
            frac = inn["frac"] - fixed_div(4 * FRACUNIT, attackrange)
            x = _trace["x"] + fixed_mul(_trace["dx"], frac)
            y = _trace["y"] + fixed_mul(_trace["dy"], frac)
            z = shootz + fixed_mul(aimslope, fixed_mul(frac, attackrange))
            front = li.frontsector
            if front is not None and front.ceilingpic == sky:
                if z > front.ceilingheight:
                    return False
                if li.backsector is not None and li.backsector.ceilingpic == sky:
                    return False
            _spawn_puff(world, x, y, z, game, attackrange)
            return False
        th = inn["thing"]
        if th is source or not (th.flags & MF_SHOOTABLE):
            return True
        dist = fixed_mul(attackrange, inn["frac"])
        if fixed_div(th.z + th.height - shootz, dist) < aimslope:
            return True
        if fixed_div(th.z - shootz, dist) > aimslope:
            return True
        frac = inn["frac"] - fixed_div(10 * FRACUNIT, attackrange)
        x = _trace["x"] + fixed_mul(_trace["dx"], frac)
        y = _trace["y"] + fixed_mul(_trace["dy"], frac)
        z = shootz + fixed_mul(aimslope, fixed_mul(frac, attackrange))
        if th.flags & MF_NOBLOOD:
            _spawn_puff(world, x, y, z, game, attackrange)
        else:
            _spawn_blood(world, x, y, z, game, damage)
        if game is not None and damage:
            game.damage_mobj(th, source, damage, source)
        hit["ok"] = True
        return False

    path_traverse(world, source.x, source.y, x2, y2, PT_ADDLINES | PT_ADDTHINGS, _shoot)
    return hit["ok"]


def _spawn_puff(world, x: int, y: int, z: int, game, attackrange: int) -> None:
    """P_SpawnPuff. The random draws matter even when the puff is only a thinker."""
    from .defs import FRACUNIT, MELEERANGE
    from .enemy import p_random
    from .info import MT_PUFF, S_PUFF3
    from .thinker import set_mobj_state, spawn_mobj

    z += (p_random() - p_random()) * 1024
    th = spawn_mobj(world, x, y, z, MT_PUFF, game)
    th.momz = FRACUNIT
    th.tics -= p_random() & 3
    if th.tics < 1:
        th.tics = 1
    if attackrange == MELEERANGE:
        set_mobj_state(th, S_PUFF3, world, game)


def _spawn_blood(world, x: int, y: int, z: int, game, damage: int) -> None:
    """P_SpawnBlood."""
    from .defs import FRACUNIT
    from .enemy import p_random
    from .info import MT_BLOOD, S_BLOOD2, S_BLOOD3
    from .thinker import set_mobj_state, spawn_mobj

    z += (p_random() - p_random()) * 1024
    th = spawn_mobj(world, x, y, z, MT_BLOOD, game)
    th.momz = FRACUNIT * 2
    th.tics -= p_random() & 3
    if th.tics < 1:
        th.tics = 1
    if damage <= 12 and damage >= 9:
        set_mobj_state(th, S_BLOOD2, world, game)
    elif damage < 9:
        set_mobj_state(th, S_BLOOD3, world, game)


def aim_slope(world, source, angle: int, attackrange: int) -> int:
    """P_AimLineAttack's slope. Zero when nothing is in the window."""
    return _aim(world, source, angle, attackrange)[0]


def aim_line_attack(world, source, angle: int, attackrange: int):
    """P_AimLineAttack: first shootable the slope window can see, or None."""
    _slope, target = _aim(world, source, angle, attackrange)
    return target


def _thing_hit_frac(x1: int, y1: int, x2: int, y2: int, mo) -> int | None:
    vx, vy = x2 - x1, y2 - y1
    wx, wy = mo.x - x1, mo.y - y1
    den = vx * vx + vy * vy
    if den == 0:
        return None
    t_num = wx * vx + wy * vy
    if t_num < 0 or t_num > den:
        return None
    px = x1 + t_num * vx // den
    py = y1 + t_num * vy // den
    if approx_distance(mo.x - px, mo.y - py) > mo.radius + 4 * FRACUNIT:
        return None
    return t_num * FRACUNIT // den


def check_sight(world, t1, t2) -> bool:
    """P_CheckSight: REJECT first, then 1-sided / closed lines along the trace."""
    s1 = point_in_subsector(world, t1.x, t1.y).sector
    s2 = point_in_subsector(world, t2.x, t2.y).sector
    nsec = len(world.sectors)
    rej = getattr(world, "rejectmatrix", b"") or b""
    if nsec and rej:
        pnum = s1.i_sector * nsec + s2.i_sector
        bytenum = pnum >> 3
        bitnum = 1 << (pnum & 7)
        if bytenum < len(rej) and (rej[bytenum] & bitnum):
            return False
    if s1 is s2:
        return True
    x1, y1, x2, y2 = t1.x, t1.y, t2.x, t2.y
    for ln in world.lines:
        if ln.backsector is not None:
            opentop, openbottom, _ = line_opening(ln)
            if opentop - openbottom > 0:
                continue
        frac = intercept_frac(x1, y1, x2, y2, ln)
        if frac is not None and FRACUNIT // 64 < frac < FRACUNIT - FRACUNIT // 64:
            return False
    return True


def thing_height_clip(world, thing) -> bool:
    """P_ThingHeightClip: ride a moving floor / squeeze under a moving ceiling."""
    on_floor = thing.z == thing.floorz
    chk = check_position(world, thing, thing.x, thing.y)
    thing.floorz = chk.floorz
    thing.ceilingz = chk.ceilingz
    if on_floor:
        thing.z = thing.floorz
    elif thing.z + thing.height > thing.ceilingz:
        thing.z = thing.ceilingz - thing.height
    if thing.player is not None:
        thing.player.viewz = thing.z + thing.player.viewheight
    return thing.ceilingz - thing.floorz >= thing.height


def change_sector(world, sector, crush: bool) -> bool:
    """P_ChangeSector: after a floor/ceiling move, carry or crush things in that sector."""
    nofit = False
    for thing in world.mobjs:
        if point_in_subsector(world, thing.x, thing.y).sector is not sector:
            continue
        if thing_height_clip(world, thing):
            continue
        if thing.health <= 0:
            thing.flags &= ~MF_SOLID
            thing.height = 0
            continue
        if not (thing.flags & MF_SHOOTABLE):
            continue
        nofit = True
        if crush:
            thing.health -= 10
            if thing.player is not None:
                thing.player.health = thing.health
            if thing.health <= 0:
                thing.flags &= ~MF_SOLID
                thing.height = 0
    return nofit


def approx_distance(dx: int, dy: int) -> int:
    dx, dy = abs(dx), abs(dy)
    if dx < dy:
        dx, dy = dy, dx
    return dx + dy // 2


def angle_to(x1: int, y1: int, x2: int, y2: int) -> int:
    """R_PointToAngle2."""
    from .defs import ANG90, ANG180
    from .tables import slope_div, tantoangle

    x = as_i32(x2 - x1)
    y = as_i32(y2 - y1)
    if x == 0 and y == 0:
        return 0
    if x >= 0:
        if y >= 0:
            if x > y:
                return tantoangle[slope_div(y, x)]
            return as_u32(ANG90 - 1 - tantoangle[slope_div(x, y)])
        y = -y
        if x > y:
            return as_u32(-tantoangle[slope_div(y, x)])
        return as_u32(0xC0000000 + tantoangle[slope_div(x, y)])
    x = -x
    if y >= 0:
        if x > y:
            return as_u32(ANG180 - 1 - tantoangle[slope_div(y, x)])
        return as_u32(ANG90 + tantoangle[slope_div(x, y)])
    y = -y
    if x > y:
        return as_u32(ANG180 + tantoangle[slope_div(y, x)])
    return as_u32(0xC0000000 - 1 - tantoangle[slope_div(x, y)])
