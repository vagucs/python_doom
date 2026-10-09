"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Doors, plats, floors, switches (p_spec / p_doors / p_plats / p_floor / p_switch).
"""

from __future__ import annotations

from dataclasses import dataclass

from .collision import change_sector, point_in_subsector
from .defs import (
    BUTTONTIME,
    CEIL_CRUSHANDRAISE,
    CEIL_FASTCRUSH,
    CEIL_LOWERANDCRUSH,
    CEIL_LOWERTOFLOOR,
    CEIL_RAISETOHIGHEST,
    CEIL_SILENTCRUSH,
    CEILSPEED,
    FASTDARK,
    FLOORSPEED,
    FRACUNIT,
    GLOWSPEED,
    IT_BLUECARD,
    IT_BLUESKULL,
    IT_REDCARD,
    IT_REDSKULL,
    IT_YELLOWCARD,
    IT_YELLOWSKULL,
    ML_TWOSIDED,
    MF_MISSILE,
    PLAT_BLAZEDWUS,
    PLAT_DOWN,
    PLAT_DWUS,
    PLAT_PERPETUAL,
    PLAT_UP,
    PLAT_WAITING,
    PLATSPEED,
    PLATWAIT,
    RESULT_CRUSHED,
    RESULT_PASTDEST,
    TICRATE,
    VDOORSPEED,
    VDOORWAIT,
    VLD_BLAZECLOSE,
    VLD_BLAZEOPEN,
    VLD_BLAZERAISE,
    VLD_CLOSE,
    VLD_CLOSE30,
    VLD_NORMAL,
    VLD_OPEN,
    VLD_RAISEIN5,
    SLOWDARK,
    STROBEBRIGHT,
)
from .enemy import p_random


SWITCH_PAIRS = [
    ("SW1BRCOM", "SW2BRCOM"),
    ("SW1BRN1", "SW2BRN1"),
    ("SW1BRN2", "SW2BRN2"),
    ("SW1BRNGN", "SW2BRNGN"),
    ("SW1BROWN", "SW2BROWN"),
    ("SW1COMM", "SW2COMM"),
    ("SW1COMP", "SW2COMP"),
    ("SW1DIRT", "SW2DIRT"),
    ("SW1EXIT", "SW2EXIT"),
    ("SW1GRAY", "SW2GRAY"),
    ("SW1GRAY1", "SW2GRAY1"),
    ("SW1METAL", "SW2METAL"),
    ("SW1PIPE", "SW2PIPE"),
    ("SW1SLAD", "SW2SLAD"),
    ("SW1STARG", "SW2STARG"),
    ("SW1STON1", "SW2STON1"),
    ("SW1STON2", "SW2STON2"),
    ("SW1STONE", "SW2STONE"),
    ("SW1STRTN", "SW2STRTN"),
    ("SW1BLUE", "SW2BLUE"),
    ("SW1CMT", "SW2CMT"),
    ("SW1GARG", "SW2GARG"),
    ("SW1GSTON", "SW2GSTON"),
    ("SW1HOT", "SW2HOT"),
    ("SW1LION", "SW2LION"),
    ("SW1SATYR", "SW2SATYR"),
    ("SW1SKIN", "SW2SKIN"),
    ("SW1VINE", "SW2VINE"),
    ("SW1WOOD", "SW2WOOD"),
    ("SW1PANEL", "SW2PANEL"),
    ("SW1ROCK", "SW2ROCK"),
    ("SW1MET2", "SW2MET2"),
    ("SW1WDMET", "SW2WDMET"),
    ("SW1BRIK", "SW2BRIK"),
    ("SW1MOD1", "SW2MOD1"),
    ("SW1ZIM", "SW2ZIM"),
    ("SW1STON6", "SW2STON6"),
    ("SW1TEK", "SW2TEK"),
    ("SW1MARB", "SW2MARB"),
    ("SW1SKULL", "SW2SKULL"),
]


def move_plane(world, sector, speed: int, dest: int, floor_or_ceiling: int, direction: int, crush: bool = False) -> int:
    last = sector.floorheight if floor_or_ceiling == 0 else sector.ceilingheight
    past = False
    if direction == -1:
        if last - speed < dest:
            next_h = dest
            past = True
        else:
            next_h = last - speed
    elif last + speed > dest:
        next_h = dest
        past = True
    else:
        next_h = last + speed
    if floor_or_ceiling == 0:
        sector.floorheight = next_h
    else:
        sector.ceilingheight = next_h
    nofit = change_sector(world, sector, crush)
    if nofit:
        if not crush or past:
            if floor_or_ceiling == 0:
                sector.floorheight = last
            else:
                sector.ceilingheight = last
            change_sector(world, sector, crush)
        return RESULT_PASTDEST if past else RESULT_CRUSHED
    return RESULT_PASTDEST if past else 0


def surrounding_sectors(sector):
    seen = []
    for ln in sector.lines:
        other = ln.backsector if ln.frontsector is sector else ln.frontsector
        if other is not None and other is not sector and other not in seen:
            seen.append(other)
    return seen


def lowest_ceiling(sector) -> int:
    h = 0x7FFFFFFF
    for other in surrounding_sectors(sector):
        if other.ceilingheight < h:
            h = other.ceilingheight
    return h if h != 0x7FFFFFFF else sector.ceilingheight


def lowest_floor(sector) -> int:
    h = sector.floorheight
    for other in surrounding_sectors(sector):
        if other.floorheight < h:
            h = other.floorheight
    return h


def highest_floor(sector) -> int:
    h = -500 * FRACUNIT
    for other in surrounding_sectors(sector):
        if other.floorheight > h:
            h = other.floorheight
    return h


def next_highest_floor(sector, current: int) -> int:
    height = current
    min_h = 0x7FFFFFFF
    found = False
    for other in surrounding_sectors(sector):
        if other.floorheight > height and other.floorheight < min_h:
            min_h = other.floorheight
            found = True
    return min_h if found else current


def highest_ceiling(sector) -> int:
    h = sector.ceilingheight
    for other in surrounding_sectors(sector):
        if other.ceilingheight > h:
            h = other.ceilingheight
    return h


def raise_floor_dest(sector) -> int:
    dest = lowest_ceiling(sector)
    return dest if dest <= sector.ceilingheight else sector.ceilingheight


def raise_floor_crush_dest(sector) -> int:
    return raise_floor_dest(sector) - 8 * FRACUNIT


def min_surrounding_light(sector, maxlight: int) -> int:
    low = maxlight
    for other in surrounding_sectors(sector):
        if other.lightlevel < low:
            low = other.lightlevel
    return low


def max_surrounding_light(sector) -> int:
    high = sector.lightlevel
    for other in surrounding_sectors(sector):
        if other.lightlevel > high:
            high = other.lightlevel
    return high


def sectors_from_tag(world, tag: int):
    if tag == 0:
        return []
    return [s for s in world.sectors if s.tag == tag]


@dataclass
class VerticalDoor:
    sector: object
    type: int
    direction: int
    topheight: int
    speed: int
    topwait: int
    topcountdown: int = 0
    dead: bool = False


@dataclass
class Plat:
    sector: object
    type: int
    status: int
    speed: int
    low: int
    high: int
    wait: int
    count: int = 0
    dead: bool = False


@dataclass
class FloorMove:
    sector: object
    direction: int
    dest: int
    speed: int
    crush: bool = False
    floorpic: int | None = None
    dead: bool = False


@dataclass
class CeilingMove:
    sector: object
    direction: int
    dest: int
    speed: int
    crush: bool = False
    ctype: int = 0
    topheight: int = 0
    bottomheight: int = 0
    dead: bool = False


@dataclass
class LightThinker:
    sector: object
    kind: str
    count: int = 0
    minlight: int = 0
    maxlight: int = 0
    darktime: int = 0
    brighttime: int = 0
    maxtime: int = 64
    mintime: int = 7
    direction: int = -1
    dead: bool = False


@dataclass
class Button:
    line: object
    where: str
    texture: int
    timer: int


class Specials:
    def __init__(self, world, res, sound) -> None:
        self.world = world
        self.res = res
        self.sound = sound
        self.thinkers: list = []
        self.lights: list[LightThinker] = []
        self.scroll_lines: list = []
        self.buttons: list[Button] = []
        self.exit_requested = False
        self.secret_exit = False
        self.switch_map: dict[int, int] = {}
        for a, b in SWITCH_PAIRS:
            ia = res.texture_num_for_name(a)
            ib = res.texture_num_for_name(b)
            if ia or ib:
                self.switch_map[ia] = ib
                self.switch_map[ib] = ia
        self.spawn_specials()

    def spawn_specials(self) -> None:
        """P_SpawnSpecials: sector lights / delayed doors and scrolling walls (48)."""
        for sector in self.world.sectors:
            spec = sector.special
            if spec == 1:
                self._spawn_light_flash(sector)
            elif spec == 2:
                self._spawn_strobe(sector, FASTDARK, False)
            elif spec == 3:
                self._spawn_strobe(sector, SLOWDARK, False)
            elif spec == 4:
                self._spawn_strobe(sector, FASTDARK, False)
                sector.special = 4
            elif spec == 8:
                self._spawn_glow(sector)
            elif spec == 10:
                self._spawn_door_close_in_30(sector)
            elif spec == 12:
                self._spawn_strobe(sector, SLOWDARK, True)
            elif spec == 13:
                self._spawn_strobe(sector, FASTDARK, True)
            elif spec == 14:
                self._spawn_door_raise_in_5(sector)
            elif spec == 17:
                self._spawn_fire_flicker(sector)
        for ln in self.world.lines:
            if ln.special == 48:
                self.scroll_lines.append(ln)

    def tick(self) -> None:
        self._tick_lights()
        for ln in self.scroll_lines:
            side = ln.sides[0] if ln.sides else None
            if side is not None:
                side.textureoffset += FRACUNIT
        alive = []
        for th in self.thinkers:
            if getattr(th, "dead", False):
                continue
            if isinstance(th, VerticalDoor):
                self._tick_door(th)
            elif isinstance(th, Plat):
                self._tick_plat(th)
            elif isinstance(th, FloorMove):
                self._tick_floor(th)
            elif isinstance(th, CeilingMove):
                self._tick_ceiling(th)
            if not getattr(th, "dead", False):
                alive.append(th)
        self.thinkers = alive
        for btn in list(self.buttons):
            btn.timer -= 1
            if btn.timer <= 0:
                side = btn.line.sides[0]
                if side is not None:
                    if btn.where == "top":
                        side.toptexture = btn.texture
                    elif btn.where == "mid":
                        side.midtexture = btn.texture
                    else:
                        side.bottomtexture = btn.texture
                self.buttons.remove(btn)

    def _tick_door(self, door: VerticalDoor) -> None:
        if door.direction == 0:
            door.topcountdown -= 1
            if door.topcountdown <= 0:
                if door.type in (VLD_NORMAL, VLD_BLAZERAISE, VLD_CLOSE):
                    door.direction = -1
                    self.sound.play("dorcls" if door.type != VLD_BLAZERAISE else "bdcls")
                elif door.type in (VLD_CLOSE30, VLD_RAISEIN5):
                    door.direction = 1
                    self.sound.play("doropn")
            return
        dest = door.topheight if door.direction == 1 else door.sector.floorheight
        res = move_plane(self.world, door.sector, door.speed, dest, 1, door.direction)
        if res != RESULT_PASTDEST:
            return
        if door.direction == 1:
            if door.type in (VLD_NORMAL, VLD_BLAZERAISE):
                door.direction = 0
                door.topcountdown = door.topwait
            else:
                door.sector.specialdata = None
                door.dead = True
        else:
            if door.type == VLD_CLOSE30:
                door.direction = 0
                door.topcountdown = TICRATE * 30
            else:
                door.sector.specialdata = None
                door.dead = True

    def _tick_plat(self, plat: Plat) -> None:
        if plat.status == PLAT_WAITING:
            plat.count -= 1
            if plat.count <= 0:
                plat.status = PLAT_UP if plat.sector.floorheight <= plat.low else PLAT_DOWN
                self.sound.play("pstart")
            return
        dest = plat.high if plat.status == PLAT_UP else plat.low
        direction = 1 if plat.status == PLAT_UP else -1
        res = move_plane(self.world, plat.sector, plat.speed, dest, 0, direction)
        if res == RESULT_PASTDEST:
            if plat.status == PLAT_DOWN or plat.type == PLAT_PERPETUAL:
                plat.status = PLAT_WAITING
                plat.count = plat.wait
                self.sound.play("pstop")
            else:
                plat.sector.specialdata = None
                plat.dead = True
                self.sound.play("pstop")

    def _tick_floor(self, floor: FloorMove) -> None:
        res = move_plane(self.world, floor.sector, floor.speed, floor.dest, 0, floor.direction, floor.crush)
        if res == RESULT_PASTDEST:
            if floor.floorpic is not None:
                floor.sector.floorpic = floor.floorpic
            floor.sector.specialdata = None
            floor.dead = True

    def _tick_ceiling(self, ceil: CeilingMove) -> None:
        dest = ceil.dest
        if ceil.ctype:
            dest = ceil.topheight if ceil.direction == 1 else ceil.bottomheight
        res = move_plane(self.world, ceil.sector, ceil.speed, dest, 1, ceil.direction, ceil.crush)
        bounce = ceil.ctype in (CEIL_CRUSHANDRAISE, CEIL_FASTCRUSH, CEIL_SILENTCRUSH)
        if res == RESULT_PASTDEST:
            if bounce:
                if ceil.direction == -1:
                    ceil.direction = 1
                    ceil.speed = CEILSPEED * (2 if ceil.ctype == CEIL_FASTCRUSH else 1)
                    if ceil.ctype == CEIL_SILENTCRUSH:
                        self.sound.play("pstop")
                else:
                    ceil.direction = -1
                    if ceil.ctype == CEIL_SILENTCRUSH:
                        self.sound.play("pstop")
            else:
                ceil.sector.specialdata = None
                ceil.dead = True
        elif res == RESULT_CRUSHED and bounce:
            ceil.speed = max(1, CEILSPEED // 8)

    def _spawn_door(self, sector, dtype: int, reverse: bool = False) -> bool:
        if sector.specialdata is not None:
            door = sector.specialdata
            if isinstance(door, VerticalDoor) and dtype in (VLD_NORMAL, VLD_BLAZERAISE):
                door.direction = 1 if door.direction == -1 else -1
                return True
            return False
        door = VerticalDoor(
            sector=sector,
            type=dtype,
            direction=-1 if reverse or dtype in (VLD_CLOSE, VLD_BLAZECLOSE, VLD_CLOSE30) else 1,
            topheight=lowest_ceiling(sector) - 4 * FRACUNIT,
            speed=VDOORSPEED * (4 if dtype >= VLD_BLAZERAISE else 1),
            topwait=VDOORWAIT,
        )
        if dtype == VLD_CLOSE30:
            door.topheight = sector.ceilingheight
        sector.specialdata = door
        self.thinkers.append(door)
        if door.direction == 1:
            self.sound.play("doropn" if dtype < VLD_BLAZERAISE else "bdopn")
        else:
            self.sound.play("dorcls" if dtype < VLD_BLAZERAISE else "bdcls")
        return True

    def do_door(self, line, dtype: int, reverse: bool = False) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if self._spawn_door(sec, dtype, reverse):
                ok = True
        return ok

    def locked_blaze_door(self, line, thing, spec: int) -> None:
        """EV_DoLockedDoor: every sector with this line's tag, not only the back sector."""
        player = thing.player
        if player is None:
            return
        if spec in (99, 133):
            card, skull, name = IT_BLUECARD, IT_BLUESKULL, "blue"
        elif spec in (134, 135):
            card, skull, name = IT_REDCARD, IT_REDSKULL, "red"
        else:
            card, skull, name = IT_YELLOWCARD, IT_YELLOWSKULL, "yellow"
        if not (player.cards[card] or player.cards[skull]):
            player.message = f"You need a {name} key to open this door"
            self.sound.play("oof")
            return
        if self.do_door(line, VLD_BLAZEOPEN):
            self.change_switch(line, 1 if spec in (99, 134, 136) else 0)

    def vertical_door(self, line, thing) -> None:
        player = thing.player
        spec = line.special
        if spec in (26, 32) and player and not (player.cards[IT_BLUECARD] or player.cards[IT_BLUESKULL]):
            player.message = "You need a blue key to open this door"
            self.sound.play("oof")
            return
        if spec in (27, 34) and player and not (player.cards[IT_YELLOWCARD] or player.cards[IT_YELLOWSKULL]):
            player.message = "You need a yellow key to open this door"
            self.sound.play("oof")
            return
        if spec in (28, 33) and player and not (player.cards[IT_REDCARD] or player.cards[IT_REDSKULL]):
            player.message = "You need a red key to open this door"
            self.sound.play("oof")
            return
        side = line.sides[1]
        if side is None or side.sector is None:
            return
        sec = side.sector
        if spec in (1, 26, 27, 28):
            dtype = VLD_NORMAL
        elif spec in (31, 32, 33, 34):
            dtype = VLD_OPEN
            line.special = 0
        elif spec == 117:
            dtype = VLD_BLAZERAISE
        elif spec == 118:
            dtype = VLD_BLAZEOPEN
            line.special = 0
        else:
            dtype = VLD_NORMAL
        self._spawn_door(sec, dtype)

    def do_plat_dwus(self, line, blaze: bool = False) -> bool:
        ok = False
        speed = PLATSPEED * (8 if blaze else 1)
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            plat = Plat(
                sector=sec,
                type=PLAT_BLAZEDWUS if blaze else PLAT_DWUS,
                status=PLAT_DOWN,
                speed=speed,
                low=lowest_floor(sec),
                high=sec.floorheight,
                wait=PLATWAIT * TICRATE,
            )
            if plat.low == plat.high:
                plat.low = plat.high - 8 * FRACUNIT
            sec.specialdata = plat
            self.thinkers.append(plat)
            self.sound.play("pstart")
            ok = True
        return ok

    def _tag_line(self, tag: int):
        class _L:
            pass

        ln = _L()
        ln.tag = tag
        return ln

    def do_floor_tag(self, tag: int, dest_fn, direction: int, speed: int | None = None, crush: bool = False) -> bool:
        return self.do_floor(self._tag_line(tag), dest_fn, direction, speed, crush)

    def do_door_tag(self, tag: int, dtype: int) -> bool:
        return self.do_door(self._tag_line(tag), dtype)

    def raise_to_texture_tag(self, tag: int) -> bool:
        return self.raise_to_texture(self._tag_line(tag))

    def do_floor(self, line, dest_fn, direction: int, speed: int | None = None, crush: bool = False) -> bool:
        ok = False
        spd = FLOORSPEED if speed is None else speed
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            dest = dest_fn(sec)
            floor = FloorMove(sector=sec, direction=direction, dest=dest, speed=spd, crush=crush)
            sec.specialdata = floor
            self.thinkers.append(floor)
            ok = True
        return ok

    def do_ceiling(self, line, dest_fn, direction: int = -1, speed: int | None = None, crush: bool = False) -> bool:
        ok = False
        spd = CEILSPEED if speed is None else speed
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            dest = dest_fn(sec)
            ceil = CeilingMove(sector=sec, direction=direction, dest=dest, speed=spd, crush=crush)
            sec.specialdata = ceil
            self.thinkers.append(ceil)
            ok = True
        return ok

    def do_stairs(self, line, step: int, speed: int) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            height = sec.floorheight + step
            floor = FloorMove(sector=sec, direction=1, dest=height, speed=speed)
            sec.specialdata = floor
            self.thinkers.append(floor)
            ok = True
            texture = sec.floorpic
            cur = sec
            while True:
                nxt = None
                for ln in cur.lines:
                    if not (ln.flags & ML_TWOSIDED):
                        continue
                    other = ln.backsector if ln.frontsector is cur else ln.frontsector
                    if other is None or other is cur:
                        continue
                    if other.floorpic != texture or other.specialdata is not None:
                        continue
                    nxt = other
                    break
                if nxt is None:
                    break
                height += step
                floor = FloorMove(sector=nxt, direction=1, dest=height, speed=speed)
                nxt.specialdata = floor
                self.thinkers.append(floor)
                cur = nxt
        return ok

    def _start_floor(self, sec, dest: int, direction: int, speed: int, crush: bool = False, floorpic: int | None = None) -> bool:
        if sec.specialdata is not None:
            return False
        floor = FloorMove(sector=sec, direction=direction, dest=dest, speed=speed, crush=crush, floorpic=floorpic)
        sec.specialdata = floor
        self.thinkers.append(floor)
        return True

    def do_crusher(self, line, ctype: int) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            top = sec.ceilingheight
            bottom = sec.floorheight
            crush = ctype != CEIL_RAISETOHIGHEST
            speed = CEILSPEED * (2 if ctype == CEIL_FASTCRUSH else 1)
            direction = -1
            dest = bottom
            if ctype == CEIL_RAISETOHIGHEST:
                dest = highest_ceiling(sec)
                direction = 1
                crush = False
            elif ctype != CEIL_LOWERTOFLOOR:
                bottom += 8 * FRACUNIT
                dest = bottom
            ceil = CeilingMove(
                sector=sec, direction=direction, dest=dest, speed=speed,
                crush=crush, ctype=ctype, topheight=top, bottomheight=bottom,
            )
            sec.specialdata = ceil
            self.thinkers.append(ceil)
            ok = True
        return ok

    def do_donut(self, line) -> bool:
        ok = False
        for s1 in sectors_from_tag(self.world, line.tag):
            if s1.specialdata is not None or not s1.lines:
                continue
            s2 = s1.lines[0].backsector if s1.lines[0].frontsector is s1 else s1.lines[0].frontsector
            if s2 is None:
                continue
            s3 = None
            for ln in s2.lines:
                other = ln.backsector
                if other is None or other is s1:
                    continue
                s3 = other
                break
            if s3 is None:
                continue
            if self._start_floor(s2, s3.floorheight, 1, FLOORSPEED // 2, floorpic=s3.floorpic):
                ok = True
            if self._start_floor(s1, s3.floorheight, -1, FLOORSPEED // 2):
                ok = True
        return ok

    def do_plat_perpetual(self, line) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            low = lowest_floor(sec)
            high = highest_floor(sec)
            if low > sec.floorheight:
                low = sec.floorheight
            if high < sec.floorheight:
                high = sec.floorheight
            plat = Plat(
                sector=sec, type=PLAT_PERPETUAL, status=p_random() & 1,
                speed=PLATSPEED, low=low, high=high, wait=PLATWAIT * TICRATE,
            )
            sec.specialdata = plat
            self.thinkers.append(plat)
            self.sound.play("pstart")
            ok = True
        return ok

    def do_plat_raise(self, line, amount: int = 0, change: bool = True) -> bool:
        ok = False
        pic = None
        if change and line.sides[0] is not None and line.sides[0].sector is not None:
            pic = line.sides[0].sector.floorpic
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            high = sec.floorheight + amount if amount else next_highest_floor(sec, sec.floorheight)
            if pic is not None:
                sec.floorpic = pic
            plat = Plat(
                sector=sec, type=PLAT_DWUS, status=PLAT_UP,
                speed=PLATSPEED // 2, low=sec.floorheight, high=high, wait=0,
            )
            sec.specialdata = plat
            self.thinkers.append(plat)
            self.sound.play("pstart")
            ok = True
        return ok

    def stop_plat(self, line) -> bool:
        ok = False
        for th in self.thinkers:
            if isinstance(th, Plat) and not th.dead and th.sector.tag == line.tag:
                th.status = PLAT_WAITING
                th.count = 0x7FFFFFFF
                ok = True
        return ok

    def raise_to_texture(self, line) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            minsize = 0x7FFFFFFF
            for ln in sec.lines:
                if not (ln.flags & ML_TWOSIDED):
                    continue
                for side in ln.sides:
                    if side is None or side.bottomtexture <= 0:
                        continue
                    h = self.res.texture_height(side.bottomtexture)
                    if 0 < h < minsize:
                        minsize = h
            if minsize == 0x7FFFFFFF:
                minsize = 64 * FRACUNIT
            if self._start_floor(sec, sec.floorheight + minsize, 1, FLOORSPEED):
                ok = True
        return ok

    def lower_and_change(self, line) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            dest = lowest_floor(sec)
            pic = sec.floorpic
            for other in surrounding_sectors(sec):
                if other.floorheight == dest:
                    pic = other.floorpic
                    break
            if self._start_floor(sec, dest, -1, FLOORSPEED, floorpic=pic):
                ok = True
        return ok

    def light_turn_on(self, line, bright: int) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            sec.lightlevel = bright if bright else max_surrounding_light(sec)
            ok = True
        return ok

    def turn_tag_lights_off(self, line) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            sec.lightlevel = min_surrounding_light(sec, sec.lightlevel)
            ok = True
        return ok

    def start_light_strobing(self, line) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            self._spawn_strobe(sec, SLOWDARK, False)
            ok = True
        return ok

    def _spawn_light_flash(self, sector) -> None:
        sector.special = 0
        flash = LightThinker(
            sector=sector, kind="flash", maxlight=sector.lightlevel,
            minlight=min_surrounding_light(sector, sector.lightlevel),
            maxtime=64, mintime=7,
        )
        flash.count = (p_random() & flash.maxtime) + 1
        self.lights.append(flash)

    def _spawn_strobe(self, sector, darktime: int, synced: bool) -> None:
        sector.special = 0
        minl = min_surrounding_light(sector, sector.lightlevel)
        if minl == sector.lightlevel:
            minl = 0
        flash = LightThinker(
            sector=sector, kind="strobe", maxlight=sector.lightlevel, minlight=minl,
            darktime=darktime, brighttime=STROBEBRIGHT,
            count=1 if synced else (p_random() & 7) + 1,
        )
        self.lights.append(flash)

    def _spawn_glow(self, sector) -> None:
        sector.special = 0
        self.lights.append(LightThinker(
            sector=sector, kind="glow", maxlight=sector.lightlevel,
            minlight=min_surrounding_light(sector, sector.lightlevel), direction=-1,
        ))

    def _spawn_fire_flicker(self, sector) -> None:
        sector.special = 0
        self.lights.append(LightThinker(
            sector=sector, kind="fire", maxlight=sector.lightlevel,
            minlight=min_surrounding_light(sector, sector.lightlevel) + 16, count=4,
        ))

    def _spawn_door_close_in_30(self, sector) -> None:
        if sector.specialdata is not None:
            return
        sector.special = 0
        door = VerticalDoor(
            sector=sector, type=VLD_CLOSE, direction=0,
            topheight=sector.ceilingheight, speed=VDOORSPEED, topwait=VDOORWAIT,
            topcountdown=30 * TICRATE,
        )
        sector.specialdata = door
        self.thinkers.append(door)

    def _spawn_door_raise_in_5(self, sector) -> None:
        if sector.specialdata is not None:
            return
        sector.special = 0
        door = VerticalDoor(
            sector=sector, type=VLD_RAISEIN5, direction=0,
            topheight=lowest_ceiling(sector) - 4 * FRACUNIT, speed=VDOORSPEED,
            topwait=VDOORWAIT, topcountdown=5 * 60 * TICRATE,
        )
        sector.specialdata = door
        self.thinkers.append(door)

    def _tick_lights(self) -> None:
        for light in self.lights:
            if light.kind == "glow":
                if light.direction == -1:
                    light.sector.lightlevel -= GLOWSPEED
                    if light.sector.lightlevel <= light.minlight:
                        light.sector.lightlevel += GLOWSPEED
                        light.direction = 1
                else:
                    light.sector.lightlevel += GLOWSPEED
                    if light.sector.lightlevel >= light.maxlight:
                        light.sector.lightlevel -= GLOWSPEED
                        light.direction = -1
                continue
            light.count -= 1
            if light.count != 0:
                continue
            if light.kind == "flash":
                if light.sector.lightlevel == light.maxlight:
                    light.sector.lightlevel = light.minlight
                    light.count = (p_random() & light.mintime) + 1
                else:
                    light.sector.lightlevel = light.maxlight
                    light.count = (p_random() & light.maxtime) + 1
            elif light.kind == "strobe":
                if light.sector.lightlevel == light.minlight:
                    light.sector.lightlevel = light.maxlight
                    light.count = light.brighttime
                else:
                    light.sector.lightlevel = light.minlight
                    light.count = light.darktime
            elif light.kind == "fire":
                amount = (p_random() & 3) * 16
                if light.sector.lightlevel - amount < light.minlight:
                    light.sector.lightlevel = light.minlight
                else:
                    light.sector.lightlevel = light.maxlight - amount
                light.count = 4

    def change_switch(self, line, use_again: int) -> None:
        side = line.sides[0]
        if side is None:
            return
        if not use_again:
            line.special = 0
        sound = "swtchx" if line.special == 11 else "swtchn"
        for attr in ("toptexture", "midtexture", "bottomtexture"):
            tex = getattr(side, attr)
            if tex in self.switch_map:
                new = self.switch_map[tex]
                if use_again:
                    self.buttons.append(Button(line, attr.replace("texture", ""), tex, BUTTONTIME))
                setattr(side, attr, new)
                self.sound.play(sound)
                return
        self.sound.play(sound)

    def use_special(self, line, thing, side: int) -> bool:
        if side != 0:
            return False
        spec = line.special
        if spec in (1, 26, 27, 28, 31, 32, 33, 34, 117, 118):
            self.vertical_door(line, thing)
            return True
        if spec in (99, 133, 134, 135, 136, 137):
            self.locked_blaze_door(line, thing, spec)
            return True
        if spec == 11:
            self.change_switch(line, 0)
            self.exit_requested = True
            return True
        if spec == 51:
            self.change_switch(line, 0)
            self.exit_requested = True
            self.secret_exit = True
            return True
        tagged = {
            29: lambda: self.do_door(line, VLD_NORMAL),
            50: lambda: self.do_door(line, VLD_CLOSE),
            103: lambda: self.do_door(line, VLD_OPEN),
            111: lambda: self.do_door(line, VLD_BLAZERAISE),
            112: lambda: self.do_door(line, VLD_BLAZEOPEN),
            113: lambda: self.do_door(line, VLD_BLAZECLOSE),
            21: lambda: self.do_plat_dwus(line),
            122: lambda: self.do_plat_dwus(line, True),
            18: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1),
            23: lambda: self.do_floor(line, lowest_floor, -1),
            71: lambda: self.do_floor(line, highest_floor, -1),
            101: lambda: self.do_floor(line, raise_floor_dest, 1),
            102: lambda: self.do_floor(line, highest_floor, -1),
            7: lambda: self.do_stairs(line, 8 * FRACUNIT, FLOORSPEED // 4),
            127: lambda: self.do_stairs(line, 16 * FRACUNIT, FLOORSPEED * 4),
            41: lambda: self.do_crusher(line, CEIL_LOWERTOFLOOR),
            49: lambda: self.do_crusher(line, CEIL_CRUSHANDRAISE),
            9: lambda: self.do_donut(line),
            14: lambda: self.do_plat_raise(line, 32 * FRACUNIT),
            15: lambda: self.do_plat_raise(line, 24 * FRACUNIT),
            20: lambda: self.do_plat_raise(line, 0),
            55: lambda: self.do_floor(line, raise_floor_crush_dest, 1, crush=True),
            131: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1, FLOORSPEED * 4),
            140: lambda: self.do_floor(line, lambda s: s.floorheight + 512 * FRACUNIT, 1),
        }
        retrigger = {
            42: lambda: self.do_door(line, VLD_CLOSE),
            61: lambda: self.do_door(line, VLD_OPEN),
            63: lambda: self.do_door(line, VLD_NORMAL),
            62: lambda: self.do_plat_dwus(line),
            114: lambda: self.do_door(line, VLD_BLAZERAISE),
            115: lambda: self.do_door(line, VLD_BLAZEOPEN),
            116: lambda: self.do_door(line, VLD_BLAZECLOSE),
            120: lambda: self.do_plat_dwus(line, True),
            123: lambda: self.do_plat_dwus(line, True),
            45: lambda: self.do_floor(line, highest_floor, -1),
            60: lambda: self.do_floor(line, lowest_floor, -1),
            64: lambda: self.do_floor(line, raise_floor_dest, 1),
            70: lambda: self.do_floor(line, highest_floor, -1, FLOORSPEED * 4),
            43: lambda: self.do_crusher(line, CEIL_LOWERTOFLOOR),
            65: lambda: self.do_floor(line, raise_floor_crush_dest, 1, crush=True),
            66: lambda: self.do_plat_raise(line, 24 * FRACUNIT),
            67: lambda: self.do_plat_raise(line, 32 * FRACUNIT),
            68: lambda: self.do_plat_raise(line, 0),
            69: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1),
            132: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1, FLOORSPEED * 4),
            138: lambda: self.light_turn_on(line, 255),
            139: lambda: self.light_turn_on(line, 35),
        }
        if spec in tagged:
            ok = bool(tagged[spec]())
            if ok:
                self.change_switch(line, 0)
            return ok
        if spec in retrigger:
            ok = bool(retrigger[spec]())
            if ok:
                self.change_switch(line, 1)
            return ok
        return False

    def shoot_special(self, line, thing) -> None:
        spec = line.special
        if spec == 24:
            if self.do_floor(line, raise_floor_dest, 1):
                self.change_switch(line, 0)
        elif spec == 46:
            self.do_door(line, VLD_OPEN)
            self.change_switch(line, 1)
        elif spec == 47:
            if self.do_plat_raise(line, 0):
                self.change_switch(line, 0)

    def cross_special(self, line, side: int, thing) -> None:
        spec = line.special
        once = {
            2: lambda: self.do_door(line, VLD_OPEN),
            3: lambda: self.do_door(line, VLD_CLOSE),
            4: lambda: self.do_door(line, VLD_NORMAL),
            5: lambda: self.do_floor(line, raise_floor_dest, 1),
            6: lambda: self.do_crusher(line, CEIL_FASTCRUSH),
            8: lambda: self.do_stairs(line, 8 * FRACUNIT, FLOORSPEED // 4),
            10: lambda: self.do_plat_dwus(line),
            12: lambda: self.light_turn_on(line, 0),
            13: lambda: self.light_turn_on(line, 255),
            16: lambda: self.do_door(line, VLD_CLOSE30, reverse=True),
            17: lambda: self.start_light_strobing(line),
            19: lambda: self.do_floor(line, highest_floor, -1),
            22: lambda: self.do_plat_raise(line, 0),
            25: lambda: self.do_crusher(line, CEIL_CRUSHANDRAISE),
            30: lambda: self.raise_to_texture(line),
            35: lambda: self.light_turn_on(line, 35),
            36: lambda: self.do_floor(line, highest_floor, -1, FLOORSPEED * 4),
            37: lambda: self.lower_and_change(line),
            38: lambda: self.do_floor(line, lowest_floor, -1),
            39: lambda: self.teleport(line, side, thing) or True,
            40: lambda: (self.do_crusher(line, CEIL_RAISETOHIGHEST), self.do_floor(line, lowest_floor, -1)),
            44: lambda: self.do_crusher(line, CEIL_LOWERANDCRUSH),
            53: lambda: self.do_plat_perpetual(line),
            54: lambda: self.stop_plat(line),
            56: lambda: self.do_floor(line, raise_floor_crush_dest, 1, crush=True),
            57: lambda: self.stop_plat(line),
            58: lambda: self.do_floor(line, lambda s: s.floorheight + 24 * FRACUNIT, 1),
            59: lambda: self.do_floor(line, lambda s: s.floorheight + 24 * FRACUNIT, 1),
            100: lambda: self.do_stairs(line, 16 * FRACUNIT, FLOORSPEED * 4),
            104: lambda: self.turn_tag_lights_off(line),
            108: lambda: self.do_door(line, VLD_BLAZERAISE),
            109: lambda: self.do_door(line, VLD_BLAZEOPEN),
            110: lambda: self.do_door(line, VLD_BLAZECLOSE),
            119: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1),
            121: lambda: self.do_plat_dwus(line, True),
            125: lambda: (thing.player is None and self.teleport(line, side, thing)) or True,
            130: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1, FLOORSPEED * 4),
            141: lambda: self.do_crusher(line, CEIL_SILENTCRUSH),
        }
        again = {
            72: lambda: self.do_crusher(line, CEIL_LOWERANDCRUSH),
            73: lambda: self.do_crusher(line, CEIL_CRUSHANDRAISE),
            74: lambda: self.stop_plat(line),
            75: lambda: self.do_door(line, VLD_CLOSE),
            76: lambda: self.do_door(line, VLD_CLOSE30, reverse=True),
            77: lambda: self.do_crusher(line, CEIL_FASTCRUSH),
            79: lambda: self.light_turn_on(line, 35),
            80: lambda: self.light_turn_on(line, 0),
            81: lambda: self.light_turn_on(line, 255),
            82: lambda: self.do_floor(line, lowest_floor, -1),
            83: lambda: self.do_floor(line, highest_floor, -1),
            84: lambda: self.lower_and_change(line),
            86: lambda: self.do_door(line, VLD_OPEN),
            87: lambda: self.do_plat_perpetual(line),
            88: lambda: self.do_plat_dwus(line),
            89: lambda: self.stop_plat(line),
            90: lambda: self.do_door(line, VLD_NORMAL),
            91: lambda: self.do_floor(line, raise_floor_dest, 1),
            92: lambda: self.do_floor(line, lambda s: s.floorheight + 24 * FRACUNIT, 1),
            93: lambda: self.do_floor(line, lambda s: s.floorheight + 24 * FRACUNIT, 1),
            94: lambda: self.do_floor(line, raise_floor_crush_dest, 1, crush=True),
            95: lambda: self.do_plat_raise(line, 0),
            96: lambda: self.raise_to_texture(line),
            97: lambda: self.teleport(line, side, thing),
            98: lambda: self.do_floor(line, highest_floor, -1, FLOORSPEED * 4),
            105: lambda: self.do_door(line, VLD_BLAZERAISE),
            106: lambda: self.do_door(line, VLD_BLAZEOPEN),
            107: lambda: self.do_door(line, VLD_BLAZECLOSE),
            120: lambda: self.do_plat_dwus(line, True),
            126: lambda: thing.player is None and self.teleport(line, side, thing),
            128: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1),
            129: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1, FLOORSPEED * 4),
        }
        if spec == 52:
            self.exit_requested = True
            return
        if spec == 124:
            self.exit_requested = True
            self.secret_exit = True
            return
        if spec in once:
            once[spec]()
            line.special = 0
        elif spec in again:
            again[spec]()

    def teleport(self, line, side: int, thing) -> None:
        """EV_Teleport: walk special 39/97 onto MT_TELEPORTMAN (thing 14)."""
        if side == 1 or (thing.flags & MF_MISSILE):
            return
        tag = line.tag
        for i, sector in enumerate(self.world.sectors):
            if sector.tag != tag:
                continue
            for dest in self.world.mobjs:
                from .info import MT_TELEPORTMAN

                if dest.type != MT_TELEPORTMAN:
                    continue
                dest_sector = point_in_subsector(self.world, dest.x, dest.y).sector
                if dest_sector is not sector and dest_sector.i_sector != i:
                    continue
                from .collision import set_thing_position, unset_thing_position

                thing.momx = thing.momy = thing.momz = 0
                unset_thing_position(self.world, thing)
                thing.x = dest.x
                thing.y = dest.y
                ss = point_in_subsector(self.world, thing.x, thing.y)
                thing.floorz = ss.sector.floorheight
                thing.ceilingz = ss.sector.ceilingheight
                thing.z = thing.floorz
                thing.angle = dest.angle
                set_thing_position(self.world, thing)
                if thing.player is not None:
                    thing.player.viewz = thing.z + thing.player.viewheight
                    thing.reactiontime = 18
                self.sound.play("telept")
                return
