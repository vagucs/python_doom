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

from .defs import (
    BUTTONTIME,
    CEILSPEED,
    FLOORSPEED,
    FRACUNIT,
    IT_BLUECARD,
    IT_BLUESKULL,
    IT_REDCARD,
    IT_REDSKULL,
    IT_YELLOWCARD,
    IT_YELLOWSKULL,
    ML_TWOSIDED,
    PLAT_BLAZEDWUS,
    PLAT_DOWN,
    PLAT_DWUS,
    PLAT_UP,
    PLAT_WAITING,
    PLATSPEED,
    PLATWAIT,
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
)


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


def move_plane(sector, speed: int, dest: int, floor_or_ceiling: int, direction: int) -> int:
    if floor_or_ceiling == 0:
        if direction == -1:
            if sector.floorheight - speed < dest:
                sector.floorheight = dest
                return RESULT_PASTDEST
            sector.floorheight -= speed
        else:
            if sector.floorheight + speed > dest:
                sector.floorheight = dest
                return RESULT_PASTDEST
            sector.floorheight += speed
    else:
        if direction == -1:
            if sector.ceilingheight - speed < dest:
                sector.ceilingheight = dest
                return RESULT_PASTDEST
            sector.ceilingheight -= speed
        else:
            if sector.ceilingheight + speed > dest:
                sector.ceilingheight = dest
                return RESULT_PASTDEST
            sector.ceilingheight += speed
    return 0


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
    dead: bool = False


@dataclass
class CeilingMove:
    sector: object
    direction: int
    dest: int
    speed: int
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

    def tick(self) -> None:
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
                if door.type in (VLD_NORMAL, VLD_BLAZERAISE):
                    door.direction = -1
                    self.sound.play("dorcls" if door.type == VLD_NORMAL else "bdcls")
                elif door.type == VLD_CLOSE30:
                    door.direction = 1
                    self.sound.play("doropn")
            return
        dest = door.topheight if door.direction == 1 else door.sector.floorheight
        res = move_plane(door.sector, door.speed, dest, 1, door.direction)
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
        res = move_plane(plat.sector, plat.speed, dest, 0, direction)
        if res == RESULT_PASTDEST:
            if plat.status == PLAT_DOWN:
                plat.status = PLAT_WAITING
                plat.count = plat.wait
                self.sound.play("pstop")
            else:
                plat.sector.specialdata = None
                plat.dead = True
                self.sound.play("pstop")

    def _tick_floor(self, floor: FloorMove) -> None:
        res = move_plane(floor.sector, floor.speed, floor.dest, 0, floor.direction)
        if res == RESULT_PASTDEST:
            floor.sector.specialdata = None
            floor.dead = True

    def _tick_ceiling(self, ceil: CeilingMove) -> None:
        res = move_plane(ceil.sector, ceil.speed, ceil.dest, 1, ceil.direction)
        if res == RESULT_PASTDEST:
            ceil.sector.specialdata = None
            ceil.dead = True

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
            dtype = VLD_OPEN
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

    def do_floor(self, line, dest_fn, direction: int) -> bool:
        ok = False
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            dest = dest_fn(sec)
            floor = FloorMove(sector=sec, direction=direction, dest=dest, speed=FLOORSPEED)
            sec.specialdata = floor
            self.thinkers.append(floor)
            ok = True
        return ok

    def do_ceiling(self, line, dest_fn, direction: int = -1, speed: int | None = None) -> bool:
        ok = False
        spd = CEILSPEED if speed is None else speed
        for sec in sectors_from_tag(self.world, line.tag):
            if sec.specialdata is not None:
                continue
            dest = dest_fn(sec)
            ceil = CeilingMove(sector=sec, direction=direction, dest=dest, speed=spd)
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

    def use_special(self, line, thing, side: int) -> None:
        if side != 0:
            return
        spec = line.special
        if spec in (1, 26, 27, 28, 31, 32, 33, 34, 117, 118):
            self.vertical_door(line, thing)
            return
        if spec == 11:
            self.change_switch(line, 0)
            self.exit_requested = True
            return
        if spec == 51:
            self.change_switch(line, 0)
            self.exit_requested = True
            self.secret_exit = True
            return
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
            101: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1),
            102: lambda: self.do_floor(line, lambda s: s.floorheight - 8 * FRACUNIT, -1),
            7: lambda: self.do_stairs(line, 8 * FRACUNIT, FLOORSPEED // 4),
            127: lambda: self.do_stairs(line, 16 * FRACUNIT, FLOORSPEED * 4),
            41: lambda: self.do_ceiling(line, lambda s: s.floorheight, -1),
            49: lambda: self.do_ceiling(line, lambda s: s.floorheight + 8 * FRACUNIT, -1),
            14: lambda: self.do_plat_dwus(line),
            15: lambda: self.do_plat_dwus(line),
            20: lambda: self.do_plat_dwus(line),
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
            45: lambda: self.do_floor(line, lambda s: s.floorheight - 8 * FRACUNIT, -1),
            60: lambda: self.do_floor(line, lowest_floor, -1),
            64: lambda: self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1),
            70: lambda: self.do_floor(line, highest_floor, -1),
            43: lambda: self.do_ceiling(line, lambda s: s.floorheight, -1),
        }
        if spec in tagged:
            if tagged[spec]():
                self.change_switch(line, 0)
            return
        if spec in retrigger:
            if retrigger[spec]():
                self.change_switch(line, 1)

    def cross_special(self, line, side: int, thing) -> None:
        spec = line.special
        if spec == 2:
            self.do_door(line, VLD_OPEN)
            line.special = 0
        elif spec == 3:
            self.do_door(line, VLD_CLOSE)
            line.special = 0
        elif spec == 4:
            self.do_door(line, VLD_NORMAL)
            line.special = 0
        elif spec == 5:
            self.do_floor(line, lambda s: next_highest_floor(s, s.floorheight), 1)
            line.special = 0
        elif spec == 10:
            self.do_plat_dwus(line)
            line.special = 0
        elif spec == 16:
            self.do_door(line, VLD_CLOSE30, reverse=True)
            line.special = 0
        elif spec == 19:
            self.do_floor(line, lambda s: s.floorheight - 8 * FRACUNIT, -1)
            line.special = 0
        elif spec == 36:
            self.do_floor(line, highest_floor, -1)
            line.special = 0
        elif spec == 38:
            self.do_floor(line, lowest_floor, -1)
            line.special = 0
        elif spec == 52:
            self.exit_requested = True
        elif spec == 88:
            self.do_plat_dwus(line)
        elif spec == 86:
            self.do_door(line, VLD_OPEN)
        elif spec == 90:
            self.do_door(line, VLD_NORMAL)
        elif spec == 105:
            self.do_door(line, VLD_BLAZERAISE)
        elif spec == 106:
            self.do_door(line, VLD_BLAZEOPEN)
        elif spec == 107:
            self.do_door(line, VLD_BLAZECLOSE)
        elif spec == 120:
            self.do_plat_dwus(line, True)
        elif spec == 121:
            self.do_plat_dwus(line, True)
            line.special = 0
        elif spec == 124:
            self.exit_requested = True
            self.secret_exit = True
