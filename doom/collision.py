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

from .compat import as_i32, as_u32, fixed_mul, shar
from .defs import (
    ANGLETOFINESHIFT,
    BOXBOTTOM,
    BOXLEFT,
    BOXRIGHT,
    BOXTOP,
    FINEMASK,
    FRACBITS,
    FRACUNIT,
    MAXMOVE,
    MAXSTEP,
    MF_DROPOFF,
    MF_FLOAT,
    MF_MISSILE,
    MF_NOCLIP,
    MF_PICKUP,
    MF_SHOOTABLE,
    MF_SOLID,
    MF_SPECIAL,
    ML_BLOCKING,
    ML_BLOCKMONSTERS,
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


def _thing_blocks(tm, other) -> bool:
    if other is tm:
        return False
    if (tm.flags & MF_MISSILE) and other is getattr(tm, "target", None):
        return False
    flags = other.flags
    if not (flags & (MF_SOLID | MF_SPECIAL | MF_SHOOTABLE)):
        return False
    blockdist = other.radius + tm.radius
    if abs(other.x - tm._tmx) >= blockdist or abs(other.y - tm._tmy) >= blockdist:
        return False
    # PIT_CheckThing: miss if one is fully above the other
    if tm.z >= other.z + other.height:
        return False
    if tm.z + tm.height <= other.z:
        return False
    if flags & MF_SPECIAL:
        if tm.flags & MF_PICKUP:
            tm._pickup = other
        return bool(flags & MF_SOLID)
    return bool(flags & MF_SOLID)


def check_position(world, thing, x: int, y: int) -> MoveCheck:
    chk = MoveCheck()
    thing._tmx, thing._tmy = x, y
    thing._pickup = None
    radius = thing.radius
    bbox = [0, 0, 0, 0]
    bbox[BOXTOP] = y + radius
    bbox[BOXBOTTOM] = y - radius
    bbox[BOXRIGHT] = x + radius
    bbox[BOXLEFT] = x - radius
    sub = point_in_subsector(world, x, y)
    chk.floorz = sub.sector.floorheight
    chk.dropoffz = chk.floorz
    chk.ceilingz = sub.sector.ceilingheight
    if thing.flags & MF_NOCLIP:
        return chk
    for other in world.mobjs:
        if other is thing or not other.alive:
            continue
        if _thing_blocks(thing, other):
            chk.blocked = True
            chk.hit_thing = other
            return chk
        if thing._pickup is not None:
            break
    for ln in world.lines:
        if (
            bbox[BOXRIGHT] <= ln.bbox[BOXLEFT]
            or bbox[BOXLEFT] >= ln.bbox[BOXRIGHT]
            or bbox[BOXTOP] <= ln.bbox[BOXBOTTOM]
            or bbox[BOXBOTTOM] >= ln.bbox[BOXTOP]
        ):
            continue
        if box_on_line_side(bbox, ln) != -1:
            continue
        if ln.backsector is None:
            chk.blocked = True
            return chk
        if not (thing.flags & MF_MISSILE):
            if ln.flags & ML_BLOCKING:
                chk.blocked = True
                return chk
            if thing.player is None and (ln.flags & ML_BLOCKMONSTERS):
                chk.blocked = True
                return chk
        opentop, openbottom, lowfloor = line_opening(ln)
        if opentop < chk.ceilingz:
            chk.ceilingz = opentop
        if openbottom > chk.floorz:
            chk.floorz = openbottom
        if lowfloor < chk.dropoffz:
            chk.dropoffz = lowfloor
        if ln.special:
            chk.spechit.append(ln)
    return chk


def try_move(world, thing, x: int, y: int, game=None) -> bool:
    chk = check_position(world, thing, x, y)
    if chk.blocked:
        return False
    if not (thing.flags & MF_NOCLIP):
        if chk.ceilingz - chk.floorz < thing.height:
            return False
        if chk.ceilingz - thing.z < thing.height:
            return False
        if chk.floorz - thing.z > MAXSTEP:
            return False
        if not (thing.flags & (MF_DROPOFF | MF_FLOAT)):
            if chk.floorz - chk.dropoffz > MAXSTEP:
                return False
    oldx, oldy = thing.x, thing.y
    thing.floorz = chk.floorz
    thing.ceilingz = chk.ceilingz
    thing.x = x
    thing.y = y
    pickup = getattr(thing, "_pickup", None)
    if pickup is not None and game is not None:
        game.touch_special(pickup, thing)
    if game is not None and not (thing.flags & MF_NOCLIP):
        for ln in chk.spechit:
            side = point_on_line_side(thing.x, thing.y, ln)
            oldside = point_on_line_side(oldx, oldy, ln)
            if side != oldside and ln.special:
                game.cross_special(ln, oldside, thing)
    return True


def slide_move(world, thing, momx: int, momy: int, game=None) -> None:
    if abs(momx) > MAXMOVE:
        momx = MAXMOVE if momx > 0 else -MAXMOVE
    if abs(momy) > MAXMOVE:
        momy = MAXMOVE if momy > 0 else -MAXMOVE
    ptryx = thing.x + momx
    ptryy = thing.y + momy
    if try_move(world, thing, ptryx, ptryy, game):
        return
    try_move(world, thing, thing.x + momx, thing.y, game)
    try_move(world, thing, thing.x, thing.y + momy, game)


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
    """P_UseLines + PTR_UseTraverse: walk intercepts, skip open two-sided lines."""
    mo = player.mo
    x1, y1 = mo.x, mo.y
    x2 = x1 + shar(USERANGE, FRACBITS) * fine_cos(mo.angle)
    y2 = y1 + shar(USERANGE, FRACBITS) * fine_sin(mo.angle)
    hits: list[tuple[int, object]] = []
    for ln in world.lines:
        frac = intercept_frac(x1, y1, x2, y2, ln)
        if frac is None or frac < 0 or frac > FRACUNIT:
            continue
        hits.append((frac, ln))
    hits.sort(key=lambda h: h[0])
    for _frac, ln in hits:
        if not ln.special:
            if ln.backsector is None:
                if game:
                    game.start_sound("noway")
                return
            opentop, openbottom, _ = line_opening(ln)
            if opentop - openbottom <= 0:
                if game:
                    game.start_sound("noway")
                return
            continue
        side = point_on_line_side(mo.x, mo.y, ln)
        if game:
            game.use_special(ln, mo, side)
        return


def line_attack(world, source, damage: int, game, attackrange: int) -> bool:
    x1, y1 = source.x, source.y
    x2 = x1 + shar(attackrange, FRACBITS) * fine_cos(source.angle)
    y2 = y1 + shar(attackrange, FRACBITS) * fine_sin(source.angle)
    hits: list[tuple[int, str, object]] = []
    for ln in world.lines:
        frac = intercept_frac(x1, y1, x2, y2, ln)
        if frac is None or frac <= 0 or frac > FRACUNIT:
            continue
        solid = ln.backsector is None
        if not solid:
            opentop, openbottom, _ = line_opening(ln)
            solid = opentop - openbottom <= 32 * FRACUNIT or bool(ln.flags & ML_BLOCKING)
        if solid:
            hits.append((frac, "line", ln))
    for other in world.mobjs:
        if other is source or not (other.flags & MF_SHOOTABLE):
            continue
        frac = _thing_hit_frac(x1, y1, x2, y2, other)
        if frac is not None:
            hits.append((frac, "thing", other))
    hits.sort(key=lambda h: h[0])
    for _frac, kind, obj in hits:
        if kind == "thing":
            if game is not None:
                game.damage_mobj(obj, source, damage)
            return True
        if kind == "line":
            if obj.special == 46 and game is not None:
                game.use_special(obj, source, 0)
            return False
    return False


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
