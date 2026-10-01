"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Monster AI (p_enemy.prg condensed): look, chase, hitscan, melee, fireballs.
"""

from __future__ import annotations

from . import collision as cmap
from .collision import (
    aim_line_attack,
    aim_slope,
    angle_to,
    approx_distance,
    check_position,
    check_sight,
    line_attack,
    point_in_subsector,
    try_move,
)
from .compat import as_i32, as_u32, fixed_mul, shar
from .defs import (
    ANG45,
    ANG90,
    ANG270,
    FRACUNIT,
    FRICTION,
    GRAVITY,
    MAXMOVE,
    MELEERANGE,
    MF_AMBUSH,
    MF_CORPSE,
    MF_DROPPED,
    MF_COUNTKILL,
    MF_DROPOFF,
    MF_FLOAT,
    MF_INFLOAT,
    MF_JUSTHIT,
    MF_JUSTATTACKED,
    MF_MISSILE,
    MF_NOCLIP,
    MF_NOGRAVITY,
    MF_SHADOW,
    MF_SHOOTABLE,
    MF_SKULLFLY,
    MF_SOLID,
    MISSILERANGE,
    ML_SOUNDBLOCK,
    ML_TWOSIDED,
    SK_EASY,
    SK_NIGHTMARE,
    SKULLSPEED,
    STOPSPEED,
    VLD_BLAZEOPEN,
)
from .info import (
    MI_ACTIVESOUND,
    MI_ATTACKSOUND,
    MI_DAMAGE,
    MI_DEATHSOUND,
    MI_DEATHSTATE,
    MI_FLAGS,
    MI_HEIGHT,
    MI_MELEESTATE,
    MI_MISSILESTATE,
    MI_PAINCHANCE,
    MI_PAINSOUND,
    MI_PAINSTATE,
    MI_RADIUS,
    MI_RAISESTATE,
    MI_SEESOUND,
    MI_SEESTATE,
    MI_SPAWNHEALTH,
    MI_SPAWNSTATE,
    MI_SPEED,
    MI_XDEATHSTATE,
    MOBJINFO,
    MT_ARACHPLAZ,
    MT_BABY,
    MT_BARREL,
    MT_BOSSBRAIN,
    MT_BOSSSPIT,
    MT_BOSSTARGET,
    MT_BRUISER,
    MT_BRUISERSHOT,
    MT_CHAINGUN,
    MT_CHAINGUY,
    MT_CLIP,
    MT_CYBORG,
    MT_FATSHOT,
    MT_FATSO,
    MT_FIRE,
    MT_HEADSHOT,
    MT_KEEN,
    MT_PAIN,
    MT_POSSESSED,
    MT_ROCKET,
    MT_SHADOWS,
    MT_SHOTGUN,
    MT_SHOTGUY,
    MT_SKULL,
    MT_SPAWNSHOT,
    MT_SPIDER,
    MT_TRACER,
    MT_TROOP,
    MT_TROOPSHOT,
    MT_SERGEANT,
    MT_HEAD,
    MT_UNDEAD,
    MT_VILE,
    MT_KNIGHT,
    S_VILE_HEAL1,
)
from .player import Mobj
from .tables import fine_cos, fine_sin

DI_EAST, DI_NE, DI_NORTH, DI_NW = 0, 1, 2, 3
DI_WEST, DI_SW, DI_SOUTH, DI_SE = 4, 5, 6, 7
DI_NODIR = 8

XSPEED = (FRACUNIT, 47000, 0, -47000, -FRACUNIT, -47000, 0, 47000)
YSPEED = (0, 47000, FRACUNIT, 47000, 0, -47000, -FRACUNIT, -47000)
OPPOSITE = (4, 5, 6, 7, 0, 1, 2, 3, 8)
DIAGS = (DI_NW, DI_NE, DI_SW, DI_SE)

TRACEANGLE = 0xC000000
FATSPREAD = ANG90 // 8
MAX_SKULLS = 21
FLOATSPEED = 4 * FRACUNIT

_brain_target_on = 0
_brain_targets: list = []

# m_random.prg rndtable. P_Random increments first, so index 0 is never the first draw.
RNDTABLE = (
    0, 8, 109, 220, 222, 241, 149, 107, 75, 248, 254, 140, 16, 66,
    74, 21, 211, 47, 80, 242, 154, 27, 205, 128, 161, 89, 77, 36,
    95, 110, 85, 48, 212, 140, 211, 249, 22, 79, 200, 50, 28, 188,
    52, 140, 202, 120, 68, 145, 62, 70, 184, 190, 91, 197, 152, 224,
    149, 104, 25, 178, 252, 182, 202, 182, 141, 197, 4, 81, 181, 242,
    145, 42, 39, 227, 156, 198, 225, 193, 219, 93, 122, 175, 249, 0,
    175, 143, 70, 239, 46, 246, 163, 53, 163, 109, 168, 135, 2, 235,
    25, 92, 20, 145, 138, 77, 69, 166, 78, 176, 173, 212, 166, 113,
    94, 161, 41, 50, 239, 49, 111, 164, 70, 60, 2, 37, 171, 75,
    136, 156, 11, 56, 42, 146, 138, 229, 73, 146, 77, 61, 98, 196,
    135, 106, 63, 197, 195, 86, 96, 203, 113, 101, 170, 247, 181, 113,
    80, 250, 108, 7, 255, 237, 129, 226, 79, 107, 112, 166, 103, 241,
    24, 223, 239, 120, 198, 58, 60, 82, 128, 3, 184, 66, 143, 224,
    145, 224, 81, 206, 163, 45, 63, 90, 168, 114, 59, 33, 159, 95,
    28, 139, 123, 98, 125, 196, 15, 70, 194, 253, 54, 14, 109, 226,
    71, 17, 161, 93, 186, 87, 244, 138, 20, 52, 123, 251, 26, 36,
    17, 46, 52, 231, 232, 76, 31, 221, 84, 37, 216, 165, 212, 106,
    197, 242, 98, 43, 39, 175, 254, 145, 190, 84, 118, 222, 187, 136,
    120, 163, 236, 249,
)
assert len(RNDTABLE) == 256
_prndindex = 0


def _mi(mo) -> list:
    return MOBJINFO[mo.type]


def clear_random() -> None:
    global _prndindex
    _prndindex = 0


def p_random() -> int:
    """P_Random: vanilla 256-byte table, index advances before the read."""
    global _prndindex
    _prndindex = (_prndindex + 1) & 255
    return RNDTABLE[_prndindex]


def tick_enemies(world, game) -> None:
    from .thinker import mobj_thinker

    player = game.player
    if player is None or player.mo is None:
        return
    for mo in list(world.mobjs):
        if mo is player.mo:
            continue
        mobj_thinker(world, mo, game)


def kill_monster(mo, game, source) -> None:
    from .thinker import set_mobj_state

    info = _mi(mo)
    mo.flags &= ~(MF_SHOOTABLE | MF_FLOAT | MF_SKULLFLY)
    mo.flags |= MF_CORPSE | MF_DROPOFF
    mo.height >>= 2
    if source is not None and getattr(source, "player", None) is not None and (mo.flags & MF_COUNTKILL):
        source.player.killcount += 1
    xds = info[MI_XDEATHSTATE]
    st = xds if mo.health < -info[MI_SPAWNHEALTH] and xds else info[MI_DEATHSTATE]
    set_mobj_state(mo, st, game.world, game)
    if mo.alive:
        mo.tics -= p_random() & 3
        if mo.tics < 1:
            mo.tics = 1
        drop = {MT_POSSESSED: MT_CLIP, MT_SHOTGUY: MT_SHOTGUN, MT_CHAINGUY: MT_CHAINGUN}.get(mo.type)
        if drop is not None:
            from .thinker import ONFLOORZ, spawn_mobj

            item = spawn_mobj(game.world, mo.x, mo.y, ONFLOORZ, drop, game)
            item.flags |= MF_DROPPED


def noise_alert(world, emitter, game=None) -> None:
    """P_NoiseAlert: flood soundtarget through open two-sided lines (A_Look wakes)."""
    from .collision import point_in_subsector

    if emitter is None:
        return
    sec = point_in_subsector(world, emitter.x, emitter.y).sector
    world.validcount += 1
    _recursive_sound(world, sec, 0, emitter)


def _recursive_sound(world, sec, soundblocks: int, target) -> None:
    from .collision import line_opening

    if sec.validcount == world.validcount and sec.soundtraversed <= soundblocks + 1:
        return
    sec.validcount = world.validcount
    sec.soundtraversed = soundblocks + 1
    sec.soundtarget = target
    for check in sec.lines:
        if not (check.flags & ML_TWOSIDED):
            continue
        opentop, openbottom, _ = line_opening(check)
        if opentop - openbottom <= 0:
            continue
        other = check.backsector if check.frontsector is sec else check.frontsector
        if other is None:
            continue
        if check.flags & ML_SOUNDBLOCK:
            if soundblocks == 0:
                _recursive_sound(world, other, 1, target)
        else:
            _recursive_sound(world, other, soundblocks, target)


def _look(world, mo, player_mo, game) -> None:
    """A_Look: idle until the player is in front (or a gunshot reaches this sector)."""
    from .collision import point_in_subsector
    from .thinker import set_mobj_state

    mo.threshold = getattr(mo, "threshold", 0)
    mo.threshold = 0
    see = False
    sec = point_in_subsector(world, mo.x, mo.y).sector
    targ = sec.soundtarget
    if targ is not None and (getattr(targ, "flags", 0) & MF_SHOOTABLE):
        mo.target = targ
        if mo.flags & MF_AMBUSH:
            see = check_sight(world, mo, targ)
        else:
            see = True
    if not see:
        if not _look_for_players(world, mo, player_mo, False):
            return
    mo.movedir = DI_NODIR
    mo.movecount = 0
    _play_see_sound(mo, game)
    set_mobj_state(mo, _mi(mo)[MI_SEESTATE], world, game)


def _play_see_sound(mo, game) -> None:
    s = _mi(mo)[MI_SEESOUND]
    if not s:
        return
    if s == "posit1":
        s = ("posit1", "posit2", "posit3")[p_random() % 3]
    elif s == "bgsit1":
        s = ("bgsit1", "bgsit2")[p_random() % 2]
    game.start_sound(s)


def _play_death_sound(mo, game) -> None:
    s = _mi(mo)[MI_DEATHSOUND]
    if not s:
        return
    if s == "podth1":
        s = ("podth1", "podth2", "podth3")[p_random() % 3]
    elif s == "bgdth1":
        s = ("bgdth1", "bgdth2")[p_random() % 2]
    game.start_sound(s)


def _look_for_players(world, mo, player_mo, allaround: bool) -> bool:
    """P_LookForPlayers. Single player: only slot 0 is in the game."""
    if player_mo is None:
        return False
    c = 0
    stop = (mo.lastlook - 1) & 3
    while True:
        if mo.lastlook != 0:
            mo.lastlook = (mo.lastlook + 1) & 3
            continue
        if c == 2 or mo.lastlook == stop:
            return False
        c += 1
        if player_mo.health <= 0 or not (player_mo.flags & MF_SHOOTABLE):
            mo.lastlook = (mo.lastlook + 1) & 3
            continue
        if not check_sight(world, mo, player_mo):
            mo.lastlook = (mo.lastlook + 1) & 3
            continue
        if not allaround:
            an = (angle_to(mo.x, mo.y, player_mo.x, player_mo.y) - mo.angle) & 0xFFFFFFFF
            if an > ANG90 and an < ANG270:
                dist = approx_distance(player_mo.x - mo.x, player_mo.y - mo.y)
                if dist > MELEERANGE:
                    mo.lastlook = (mo.lastlook + 1) & 3
                    continue
        mo.target = player_mo
        return True


def _chase(world, mo, player_mo, game) -> None:
    from .thinker import set_mobj_state

    info = _mi(mo)
    if mo.reactiontime:
        mo.reactiontime -= 1
    if getattr(mo, "threshold", 0):
        target = mo.target
        if target is None or target.health <= 0:
            mo.threshold = 0
        else:
            mo.threshold -= 1
    if mo.movedir < 8:
        _face_movedir(mo)
    target = mo.target
    if target is None or not (target.flags & MF_SHOOTABLE):
        if _look_for_players(world, mo, player_mo, True):
            return
        set_mobj_state(mo, info[MI_SPAWNSTATE], world, game)
        return
    if mo.flags & MF_JUSTATTACKED:
        mo.flags &= ~MF_JUSTATTACKED
        if game.skill != SK_NIGHTMARE and not getattr(game, "fastparm", False):
            _new_chase_dir(world, mo, game)
        return
    melee_st = info[MI_MELEESTATE]
    miss_st = info[MI_MISSILESTATE]
    dist = approx_distance(target.x - mo.x, target.y - mo.y)
    melee_range = MELEERANGE - 20 * FRACUNIT + target.radius
    if melee_st and dist < melee_range and check_sight(world, mo, target):
        if info[MI_ATTACKSOUND]:
            game.start_sound(info[MI_ATTACKSOUND])
        set_mobj_state(mo, melee_st, world, game)
        return
    if miss_st:
        skip = game.skill < SK_NIGHTMARE and not getattr(game, "fastparm", False) and mo.movecount != 0
        if not skip and _missile_ok(world, mo, target, dist, has_melee=bool(melee_st)):
            set_mobj_state(mo, miss_st, world, game)
            mo.flags |= MF_JUSTATTACKED
            return
    mo.movecount -= 1
    if mo.movecount < 0 or not _move(world, mo, info[MI_SPEED], game):
        _new_chase_dir(world, mo, game)
    if info[MI_ACTIVESOUND] and p_random() < 3:
        game.start_sound(info[MI_ACTIVESOUND])


def _missile_ok(world, mo, target, dist: int, has_melee: bool) -> bool:
    if not check_sight(world, mo, target):
        return False
    if mo.flags & MF_JUSTHIT:
        mo.flags &= ~MF_JUSTHIT
        return True
    if mo.reactiontime:
        return False
    d = dist - 64 * FRACUNIT
    if not has_melee:
        d -= 128 * FRACUNIT
    d >>= 16
    if mo.type == MT_VILE and d > 14 * 64:
        return False
    if mo.type == MT_UNDEAD:
        if d < 196:
            return False
        d >>= 1
    if mo.type in (MT_CYBORG, MT_SPIDER, MT_SKULL):
        d >>= 1
    if d > 200:
        d = 200
    if mo.type == MT_CYBORG and d > 160:
        d = 160
    return p_random() >= d


def _start_attack(mo, kind: str) -> None:
    mo.ai_state = "attack"
    mo.tics = 26
    mo.frame = 4
    mo._attack_kind = kind
    mo._did_fire = False


def _tick_attack(world, mo, game) -> None:
    target = mo.target
    if target is None or target.health <= 0:
        mo.ai_state = "look"
        mo.frame = 0
        mo.tics = 10
        return
    _face_target(mo, target)
    if not getattr(mo, "_did_fire", False) and mo.tics <= 16:
        _do_attack(world, mo, game)
        mo._did_fire = True
        mo.frame = 5
    mo.tics -= 1
    if mo.tics <= 0:
        kind = getattr(mo, "_attack_kind", "")
        if kind in ("chaingun", "spider") and _refire_ok(world, mo, 40 if kind == "chaingun" else 10):
            mo.tics = 8
            mo._did_fire = False
            return
        mo.ai_state = "chase"
        mo.frame = 0
        mo.movecount = 15 + (p_random() & 15)


def _do_attack(world, mo, game) -> None:
    kind = getattr(mo, "_attack_kind", "hitscan")
    _face_target(mo, mo.target)
    if kind == "melee":
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 3)
    elif kind == "shotgun":
        game.start_sound("shotgn")
        faced = mo.angle
        slope = aim_slope(world, mo, faced, MISSILERANGE)
        for _ in range(3):
            mo.angle = as_u32(faced + ((p_random() - p_random()) << 20))
            line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE, mo.angle, slope)
        mo.angle = faced
    elif kind in ("imp", "baron", "caco"):
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.start_sound("claw")
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 3)
        else:
            game.start_sound("firsht")
            sprite = "BAL2" if kind == "baron" else "BAL1"
            dmg = 8 if kind == "baron" else 3
            speed = 15 * FRACUNIT if kind == "baron" else 10 * FRACUNIT
            _spawn_missile(world, mo, mo.target, sprite, speed, dmg, "ball")
    elif kind == "rocket":
        game.start_sound("rlaunc")
        _spawn_missile(world, mo, mo.target, "MISL", 20 * FRACUNIT, 20, "rocket")
    elif kind == "plasma":
        game.start_sound("plasma")
        _spawn_missile(world, mo, mo.target, "APLS", 25 * FRACUNIT, 5, "plasma")
    elif kind == "skull":
        _skull_attack(mo, game)
    elif kind == "chaingun":
        game.start_sound("shotgn")
        faced = mo.angle
        slope = aim_slope(world, mo, faced, MISSILERANGE)
        mo.angle = as_u32(faced + ((p_random() - p_random()) << 20))
        line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE, mo.angle, slope)
        mo.angle = faced
    elif kind == "spider":
        game.start_sound("shotgn")
        faced = mo.angle
        slope = aim_slope(world, mo, faced, MISSILERANGE)
        for _ in range(3):
            mo.angle = as_u32(faced + ((p_random() - p_random()) << 20))
            line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE, mo.angle, slope)
        mo.angle = faced
    elif kind == "revenant":
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.start_sound("skeswg")
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 6)
        else:
            game.start_sound("skeatk")
            miss = _spawn_missile(world, mo, mo.target, "FATB", 10 * FRACUNIT, 10, "tracer")
            miss.tracer = mo.target
    elif kind == "mancubus":
        game.start_sound("firsht")
        for da in (-FATSPREAD, 0, FATSPREAD):
            _spawn_missile(world, mo, mo.target, "MANF", 20 * FRACUNIT, 8, "fat", ang=as_u32(mo.angle + da))
    elif kind == "pain":
        game.start_sound("sklatk")
        _pain_shoot_skull(world, mo, game, mo.angle)
    elif kind == "vile":
        _vile_attack(world, mo, game)
    else:
        game.start_sound("pistol")
        faced = mo.angle
        slope = aim_slope(world, mo, faced, MISSILERANGE)
        mo.angle = as_u32(faced + ((p_random() - p_random()) << 20))
        line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE, mo.angle, slope)
        mo.angle = faced


def _refire_ok(world, mo, keep_chance: int) -> bool:
    """A_CPosRefire / A_SpidRefire: keep shooting or drop back to chase."""
    if p_random() < keep_chance:
        return True
    t = mo.target
    return t is not None and t.health > 0 and check_sight(world, mo, t)


def _skull_attack(mo, game) -> None:
    dest = mo.target
    if dest is None:
        return
    mo.flags |= MF_SKULLFLY
    game.start_sound("sklatk")
    _face_target(mo, dest)
    mo.momx = fixed_mul(SKULLSPEED, fine_cos(mo.angle))
    mo.momy = fixed_mul(SKULLSPEED, fine_sin(mo.angle))
    dist = approx_distance(dest.x - mo.x, dest.y - mo.y)
    steps = dist // SKULLSPEED if SKULLSPEED else 1
    if steps < 1:
        steps = 1
    mo.momz = int((dest.z + (dest.height >> 1) - mo.z) / steps)


def _tick_skull_fly(world, mo, game) -> None:
    if mo.momx == 0 and mo.momy == 0:
        mo.flags &= ~MF_SKULLFLY
        mo.momz = 0
        from .thinker import set_mobj_state

        set_mobj_state(mo, _mi(mo)[MI_SPAWNSTATE], world, game)
        return
    if not try_move(world, mo, mo.x + mo.momx, mo.y + mo.momy, game):
        if mo.flags & MF_SKULLFLY:
            mo.momx = mo.momy = 0
        return
    mo.z += mo.momz
    if mo.z <= mo.floorz or mo.z + mo.height > mo.ceilingz:
        mo.flags &= ~MF_SKULLFLY
        mo.momx = mo.momy = mo.momz = 0
        from .thinker import set_mobj_state

        set_mobj_state(mo, _mi(mo)[MI_SPAWNSTATE], world, game)


def _face_target(mo, target) -> None:
    mo.angle = angle_to(mo.x, mo.y, target.x, target.y)
    if target.flags & MF_SHADOW:
        mo.angle = as_u32(mo.angle + (p_random() - p_random()) * 2097152)


def _face_movedir(mo) -> None:
    """A_Chase angle step: snap to 45° and turn one step toward movedir."""
    if not (0 <= mo.movedir < 8):
        return
    mo.angle = as_u32(mo.angle & 3758096384)
    delta = as_i32(mo.angle - mo.movedir * ANG45)
    if delta > 0:
        mo.angle = as_u32(mo.angle - ANG45)
    elif delta < 0:
        mo.angle = as_u32(mo.angle + ANG45)


def _move(world, mo, speed: int, game) -> bool:
    """P_Move: one TryMove, float step, or open a special and count that as success."""
    if mo.movedir < 0 or mo.movedir >= 8:
        return False
    nx = mo.x + speed * XSPEED[mo.movedir]
    ny = mo.y + speed * YSPEED[mo.movedir]
    if not try_move(world, mo, nx, ny, game):
        if (mo.flags & MF_FLOAT) and cmap.floatok:
            if mo.z < cmap.tmfloorz:
                mo.z += FLOATSPEED
            else:
                mo.z -= FLOATSPEED
            mo.flags |= MF_INFLOAT
            return True
        hits = cmap.last_spechit
        if not hits:
            return False
        mo.movedir = DI_NODIR
        good = False
        for ln in reversed(hits):
            if ln.special and game is not None and game.use_special(ln, mo, 0):
                good = True
        return good
    mo.flags &= ~MF_INFLOAT
    if not (mo.flags & MF_FLOAT):
        mo.z = mo.floorz
    return True


def _new_chase_dir(world, mo, game) -> None:
    target = mo.target
    if target is None:
        return
    old = mo.movedir
    turn = OPPOSITE[old] if 0 <= old < 8 else DI_NODIR
    dx = target.x - mo.x
    dy = target.y - mo.y
    d2 = DI_EAST if dx > 10 * FRACUNIT else DI_WEST if dx < -10 * FRACUNIT else DI_NODIR
    d3 = DI_SOUTH if dy < -10 * FRACUNIT else DI_NORTH if dy > 10 * FRACUNIT else DI_NODIR
    speed = _mi(mo)[MI_SPEED]
    if d2 != DI_NODIR and d3 != DI_NODIR:
        mo.movedir = DIAGS[(2 if dy < 0 else 0) + (1 if dx > 0 else 0)]
        if mo.movedir != turn and _move(world, mo, speed, game):
            mo.movecount = p_random() & 15
            return
    if p_random() > 200 or abs(dy) > abs(dx):
        d2, d3 = d3, d2
    if d2 == turn:
        d2 = DI_NODIR
    if d3 == turn:
        d3 = DI_NODIR
    if d2 != DI_NODIR:
        mo.movedir = d2
        if _move(world, mo, speed, game):
            mo.movecount = p_random() & 15
            return
    if d3 != DI_NODIR:
        mo.movedir = d3
        if _move(world, mo, speed, game):
            mo.movecount = p_random() & 15
            return
    if old != DI_NODIR:
        mo.movedir = old
        if _move(world, mo, speed, game):
            mo.movecount = p_random() & 15
            return
    start = p_random() & 1
    dirs = range(8) if start else range(7, -1, -1)
    for tdir in dirs:
        if tdir != turn:
            mo.movedir = tdir
            if _move(world, mo, speed, game):
                mo.movecount = p_random() & 15
                return
    if turn != DI_NODIR:
        mo.movedir = turn
        if _move(world, mo, speed, game):
            mo.movecount = p_random() & 15
            return
    mo.movedir = DI_NODIR
    mo.movecount = p_random() & 15


def spawn_missile_mt(world, source, dest, typ: int, game, ang=None):
    """P_SpawnMissile using mobjinfo speed/damage/states."""
    from .thinker import spawn_mobj

    info = MOBJINFO[typ]
    speed = info[MI_SPEED]
    if dest is None:
        dest = source
    if ang is None:
        ang = angle_to(source.x, source.y, dest.x, dest.y)
        if dest.flags & MF_SHADOW:
            ang = as_u32(ang + (p_random() - p_random()) * 1048576)
    dist = approx_distance(dest.x - source.x, dest.y - source.y)
    steps = dist // speed if speed else 1
    if steps < 1:
        steps = 1
    mo = spawn_mobj(world, source.x, source.y, source.z + 32 * FRACUNIT, typ, game)
    mo.target = source
    mo.angle = ang
    mo.momx = fixed_mul(speed, fine_cos(ang))
    mo.momy = fixed_mul(speed, fine_sin(ang))
    mo.momz = int((dest.z - source.z) / steps)
    _check_missile_spawn(mo)
    return mo


def _check_missile_spawn(mo) -> None:
    """P_CheckMissileSpawn: burn one P_Random, then nudge out of the shooter."""
    mo.tics -= p_random() & 3
    if mo.tics < 1:
        mo.tics = 1
    mo.x += mo.momx >> 1
    mo.y += mo.momy >> 1
    mo.z += mo.momz >> 1


def spawn_player_missile(world, source, sprite: str, speed: int, damage: int, kind: str) -> None:
    """P_SpawnPlayerMissile: fire along the player's current angle."""
    from .info import MT_BFG, MT_PLASMA

    typ = MT_ROCKET if kind == "rocket" else MT_PLASMA if kind == "plasma" else MT_BFG
    ang = source.angle
    from .thinker import spawn_mobj

    info = MOBJINFO[typ]
    spd = info[MI_SPEED]
    mo = spawn_mobj(world, source.x, source.y, source.z + 32 * FRACUNIT, typ, game=None)
    mo.target = source
    mo.angle = ang
    mo.momx = fixed_mul(spd, fine_cos(ang))
    mo.momy = fixed_mul(spd, fine_sin(ang))
    mo.momz = 0
    _check_missile_spawn(mo)


def _trunc2(n: int) -> int:
    n = as_i32(n)
    if n < 0:
        return -((-n) // 2)
    return n // 2


def p_xy_movement(world, mo, game) -> None:
    """P_XYMovement: half-steps above MAXMOVE/2, then friction on the floor."""
    from .defs import CF_NOMOMENTUM, MF_CORPSE, MF_NOCLIP
    from .info import S_PLAY, S_PLAY_RUN1
    from .thinker import remove_mobj, set_mobj_state

    if mo.momx == 0 and mo.momy == 0:
        if mo.flags & MF_SKULLFLY:
            mo.flags &= ~MF_SKULLFLY
            mo.momx = mo.momy = mo.momz = 0
            set_mobj_state(mo, _mi(mo)[MI_SPAWNSTATE], world, game)
        return
    if mo.momx > MAXMOVE:
        mo.momx = MAXMOVE
    elif mo.momx < -MAXMOVE:
        mo.momx = -MAXMOVE
    if mo.momy > MAXMOVE:
        mo.momy = MAXMOVE
    elif mo.momy < -MAXMOVE:
        mo.momy = -MAXMOVE
    xmove, ymove = mo.momx, mo.momy
    half = MAXMOVE // 2
    while xmove != 0 or ymove != 0:
        if xmove > half or ymove > half:
            ptryx = mo.x + _trunc2(xmove)
            ptryy = mo.y + _trunc2(ymove)
            xmove = _trunc2(xmove)
            ymove = _trunc2(ymove)
        else:
            ptryx = mo.x + xmove
            ptryy = mo.y + ymove
            xmove = ymove = 0
        if mo.flags & MF_NOCLIP:
            from .collision import set_thing_position, unset_thing_position

            unset_thing_position(world, mo)
            mo.x, mo.y = ptryx, ptryy
            set_thing_position(world, mo)
            continue
        if try_move(world, mo, ptryx, ptryy, game):
            continue
        if mo.player is not None:
            from .collision import slide_move

            slide_move(world, mo, mo.momx, mo.momy, game)
        elif mo.flags & MF_MISSILE:
            line = cmap.ceilingline
            sky = getattr(getattr(game, "res", None), "skyflatnum", -1)
            if line is not None and line.backsector is not None and line.backsector.ceilingpic == sky:
                remove_mobj(world, mo)
                return
            explode_missile(world, mo, game, hit=None)
            return
        else:
            mo.momx = mo.momy = 0
    player = mo.player
    if player is not None and (player.cheats & CF_NOMOMENTUM):
        mo.momx = mo.momy = 0
        return
    if mo.flags & (MF_MISSILE | MF_SKULLFLY):
        return
    if mo.z > mo.floorz:
        return
    if mo.flags & MF_CORPSE:
        if (
            mo.momx > FRACUNIT // 4
            or mo.momx < -(FRACUNIT // 4)
            or mo.momy > FRACUNIT // 4
            or mo.momy < -(FRACUNIT // 4)
        ):
            sec = point_in_subsector(world, mo.x, mo.y).sector
            if mo.floorz != sec.floorheight:
                return
    if (
        -STOPSPEED < mo.momx < STOPSPEED
        and -STOPSPEED < mo.momy < STOPSPEED
        and (player is None or (player.cmd.forwardmove == 0 and player.cmd.sidemove == 0))
    ):
        if player is not None:
            n = mo.istate - S_PLAY_RUN1
            if 0 <= n < 4:
                set_mobj_state(mo, S_PLAY, world, game)
        mo.momx = mo.momy = 0
    else:
        mo.momx = fixed_mul(mo.momx, FRICTION)
        mo.momy = fixed_mul(mo.momy, FRICTION)


def missile_xy(world, mo, game) -> None:
    p_xy_movement(world, mo, game)


def skull_xy(world, mo, game) -> None:
    p_xy_movement(world, mo, game)


def ground_xy(world, mo, game) -> None:
    p_xy_movement(world, mo, game)


def mobj_z(mo, world, game) -> None:
    """P_ZMovement. Gravity applies only while airborne, and the first tic is doubled."""
    from .defs import MF_NOCLIP, VIEWHEIGHT

    player = mo.player
    if player is not None and mo.z < mo.floorz:
        player.viewheight -= mo.floorz - mo.z
        player.deltaviewheight = shar(VIEWHEIGHT - player.viewheight, 3)
    mo.z += mo.momz
    if (mo.flags & MF_FLOAT) and mo.target is not None and not (mo.flags & (MF_SKULLFLY | MF_INFLOAT)):
        dist = approx_distance(mo.x - mo.target.x, mo.y - mo.target.y)
        delta = (mo.target.z + shar(mo.height, 1)) - mo.z
        if delta < 0 and dist < -(delta * 3):
            mo.z -= FLOATSPEED
        elif delta > 0 and dist < (delta * 3):
            mo.z += FLOATSPEED
    if mo.z <= mo.floorz:
        if mo.momz < 0:
            if player is not None and mo.momz < -GRAVITY * 8:
                player.deltaviewheight = shar(mo.momz, 3)
                if game is not None:
                    game.start_sound("oof")
            mo.momz = 0
        mo.z = mo.floorz
        if (mo.flags & MF_SKULLFLY) and not (mo.flags & MF_MISSILE):
            mo.momz = -mo.momz
        if (mo.flags & MF_MISSILE) and not (mo.flags & MF_NOCLIP):
            explode_missile(world, mo, game, hit=None)
            return
    elif not (mo.flags & MF_NOGRAVITY):
        if mo.momz == 0:
            mo.momz = -GRAVITY * 2
        else:
            mo.momz -= GRAVITY
    if mo.z + mo.height > mo.ceilingz:
        if mo.momz > 0:
            mo.momz = 0
        mo.z = mo.ceilingz - mo.height
        if mo.flags & MF_SKULLFLY:
            mo.momz = -mo.momz
        if (mo.flags & MF_MISSILE) and not (mo.flags & MF_NOCLIP):
            explode_missile(world, mo, game, hit=None)


def explode_missile(world, mo, game, hit) -> None:
    from .thinker import set_mobj_state

    if hit is not None:
        src = mo.target if mo.target is not None else mo
        dmg = mo.damage or _mi(mo)[MI_DAMAGE]
        game.damage_mobj(hit, src, dmg * ((p_random() % 8) + 1), inflictor=mo)
    mo.momx = mo.momy = mo.momz = 0
    mo.flags &= ~MF_MISSILE
    set_mobj_state(mo, _mi(mo)[MI_DEATHSTATE], world, game)


def _radius_attack(world, spot, source, damage: int, game) -> None:
    """P_RadiusAttack: vanilla manhattan-ish falloff; cyborg/spider immune."""
    for other in list(world.mobjs):
        if other is spot or not (other.flags & MF_SHOOTABLE):
            continue
        if other.type in (MT_CYBORG, MT_SPIDER):
            continue
        dx = abs(other.x - spot.x)
        dy = abs(other.y - spot.y)
        dist = (dx if dx > dy else dy) - other.radius
        if dist < 0:
            dist = 0
        dist >>= 16
        if dist >= damage:
            continue
        if check_sight(world, other, spot):
            game.damage_mobj(other, source if source is not None else spot, damage - dist, inflictor=spot)


def _bfg_spray(world, ball, game) -> None:
    """A_BFGSpray: 40 traces from the shooter, 15d8 each."""
    shooter = ball.target
    if shooter is None:
        return
    for i in range(40):
        an = as_u32(shooter.angle - ANG90 // 2 + (ANG90 // 40) * i)
        target = aim_line_attack(world, shooter, an, 16 * 64 * FRACUNIT)
        if target is None:
            continue
        damage = 0
        for _ in range(15):
            damage += (p_random() & 7) + 1
        game.damage_mobj(target, shooter, damage, inflictor=ball)


def _tracer_home(mo) -> None:
    dest = mo.tracer
    if dest is None or dest.health <= 0:
        return
    exact = angle_to(mo.x, mo.y, dest.x, dest.y)
    diff = (exact - mo.angle) & 0xFFFFFFFF
    if diff > 0x80000000:
        mo.angle = as_u32(mo.angle - TRACEANGLE)
        if ((exact - mo.angle) & 0xFFFFFFFF) < 0x80000000:
            mo.angle = exact
    else:
        mo.angle = as_u32(mo.angle + TRACEANGLE)
        if ((exact - mo.angle) & 0xFFFFFFFF) > 0x80000000:
            mo.angle = exact
    speed = _mi(mo)[MI_SPEED]
    mo.momx = fixed_mul(speed, fine_cos(mo.angle))
    mo.momy = fixed_mul(speed, fine_sin(mo.angle))
    dist = approx_distance(dest.x - mo.x, dest.y - mo.y)
    steps = dist // speed if speed else 1
    if steps < 1:
        steps = 1
    mo.momz = int((dest.z + 40 * FRACUNIT - mo.z) / steps)


def _vile_chase(world, mo, game) -> bool:
    """A_VileChase: raise a nearby corpse instead of walking."""
    from .thinker import set_mobj_state

    for other in world.mobjs:
        if other is mo or not (other.flags & MF_CORPSE):
            continue
        if other.health > 0:
            continue
        info = MOBJINFO[other.type]
        if not info[MI_RAISESTATE]:
            continue
        maxdist = mo.radius + other.radius
        if abs(other.x - mo.x) > maxdist or abs(other.y - mo.y) > maxdist:
            continue
        set_mobj_state(mo, S_VILE_HEAL1, world, game)
        game.start_sound("slop")
        set_mobj_state(other, info[MI_RAISESTATE], world, game)
        other.flags = info[MI_FLAGS]
        other.health = info[MI_SPAWNHEALTH]
        other.height = info[MI_HEIGHT]
        other.radius = info[MI_RADIUS]
        other.target = None
        other.alive = True
        other.z = other.floorz
        return True
    return False


def _vile_attack(world, mo, game) -> None:
    dest = mo.target
    if dest is None or not check_sight(world, mo, dest):
        return
    game.start_sound("vilatk")
    game.damage_mobj(dest, mo, 20)
    _radius_attack(world, dest, mo, 70, game)


def _pain_shoot_skull(world, actor, game, ang: int) -> None:
    from .thinker import spawn_mobj

    n = 0
    for other in world.mobjs:
        if other.type == MT_SKULL and other.health > 0:
            n += 1
    if n >= MAX_SKULLS:
        return
    pre = 4 * FRACUNIT + 3 * actor.radius // 2
    x = actor.x + fixed_mul(pre, fine_cos(ang))
    y = actor.y + fixed_mul(pre, fine_sin(ang))
    skull = spawn_mobj(world, x, y, actor.z, MT_SKULL, game)
    skull.angle = ang
    chk = check_position(world, skull, skull.x, skull.y)
    if chk.blocked:
        game.damage_mobj(skull, actor, 10000, inflictor=actor)
        return
    skull.target = actor.target
    _skull_attack(skull, game)


def _pain_die(world, mo, game) -> None:
    for da in (ANG90, ANG90 * 2, ANG270):
        _pain_shoot_skull(world, mo, game, as_u32(mo.angle + da))


def _alive_of_type(world, typ: int) -> bool:
    for other in world.mobjs:
        if other.type == typ and other.health > 0:
            return True
    return False


def _commercial(game) -> bool:
    return game.wad.check_num_for_name("MAP01") >= 0


def _boss_death(world, mo, game) -> None:
    """A_BossDeath: MAP07 floors, E1M8 baron floor, E2M8/E3M8 exit."""
    if _alive_of_type(world, mo.type):
        return
    commercial = _commercial(game)
    spec = game.specials
    if commercial and game.mapn == 7:
        if mo.type == MT_FATSO:
            from .specials import lowest_floor

            spec.do_floor_tag(666, lowest_floor, -1)
        elif mo.type == MT_BABY:
            spec.raise_to_texture_tag(667)
        return
    if commercial:
        return
    if game.episode == 1 and game.mapn == 8 and mo.type == MT_BRUISER:
        from .specials import lowest_floor

        spec.do_floor_tag(666, lowest_floor, -1)
    elif game.episode == 2 and game.mapn == 8 and mo.type == MT_CYBORG:
        spec.exit_requested = True
    elif game.episode == 3 and game.mapn == 8 and mo.type == MT_SPIDER:
        spec.exit_requested = True
    elif game.episode == 4 and game.mapn == 6 and mo.type == MT_CYBORG:
        from .specials import lowest_floor

        spec.do_floor_tag(666, lowest_floor, -1)
    elif game.episode == 4 and game.mapn == 8 and mo.type == MT_BRUISER:
        from .specials import lowest_floor

        spec.do_floor_tag(666, lowest_floor, -1)


def _keen_die(world, mo, game) -> None:
    if _alive_of_type(world, MT_KEEN):
        return
    game.specials.do_door_tag(666, VLD_BLAZEOPEN)


def _brain_die(game) -> None:
    game.specials.exit_requested = True


def _brain_awake(world, mo, game) -> None:
    global _brain_targets, _brain_target_on
    _brain_targets = [m for m in world.mobjs if m.type == MT_BOSSTARGET]
    _brain_target_on = 0
    game.start_sound("bossit")


def _brain_spit(world, actor, game) -> None:
    global _brain_target_on, _brain_targets
    if getattr(game, "skill", 2) <= SK_EASY:
        actor._easy_skip = not getattr(actor, "_easy_skip", False)
        if actor._easy_skip:
            return
    targs = _brain_targets or [m for m in world.mobjs if m.type == MT_BOSSTARGET]
    if not targs:
        return
    dest = targs[_brain_target_on % len(targs)]
    _brain_target_on += 1
    game.start_sound("bospit")
    miss = spawn_missile_mt(world, actor, dest, MT_SPAWNSHOT, game)
    miss.target = dest
    st = miss.tics if miss.tics else 1
    if miss.momy:
        miss.reactiontime = ((dest.y - actor.y) // miss.momy) // st


def _spawn_fly(world, cube, game) -> None:
    from .thinker import remove_mobj, spawn_mobj

    dest = cube.target if cube.target is not None else cube
    r = p_random()
    if r < 50:
        typ = MT_TROOP
    elif r < 90:
        typ = MT_SERGEANT
    elif r < 120:
        typ = MT_SHADOWS
    elif r < 130:
        typ = MT_PAIN
    elif r < 160:
        typ = MT_HEAD
    elif r < 162:
        typ = MT_VILE
    elif r < 172:
        typ = MT_UNDEAD
    elif r < 192:
        typ = MT_BABY
    elif r < 222:
        typ = MT_FATSO
    elif r < 246:
        typ = MT_KNIGHT
    else:
        typ = MT_BRUISER
    game.start_sound("telept")
    spawned = spawn_mobj(world, dest.x, dest.y, dest.z, typ, game)
    spawned.angle = dest.angle
    remove_mobj(world, cube)


def call_action(name: str, mo, world, game) -> None:
    """Dispatch info.c A_* for the current state frame."""
    from .thinker import set_mobj_state

    pl = game.player.mo if game is not None and game.player is not None else None
    if name == "Look":
        _look(world, mo, pl, game)
    elif name == "Chase":
        _chase(world, mo, pl, game)
    elif name == "FaceTarget":
        if mo.target is not None:
            _face_target(mo, mo.target)
    elif name == "Fall":
        mo.flags &= ~MF_SOLID
    elif name == "Scream":
        _play_death_sound(mo, game)
    elif name == "XScream":
        game.start_sound("slop")
    elif name == "Pain":
        s = _mi(mo)[MI_PAINSOUND]
        if s:
            game.start_sound(s)
    elif name == "Explode":
        _radius_attack(world, mo, mo.target, 128, game)
    elif name == "PosAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        slope = aim_slope(world, mo, mo.angle, MISSILERANGE)
        game.start_sound("pistol")
        saved = mo.angle
        mo.angle = as_u32(saved + ((p_random() - p_random()) << 20))
        line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE, mo.angle, slope)
        mo.angle = saved
    elif name == "SPosAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        slope = aim_slope(world, mo, mo.angle, MISSILERANGE)
        game.start_sound("shotgn")
        saved = mo.angle
        for _ in range(3):
            mo.angle = as_u32(saved + ((p_random() - p_random()) << 20))
            line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE, mo.angle, slope)
        mo.angle = saved
    elif name == "CPosAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        slope = aim_slope(world, mo, mo.angle, MISSILERANGE)
        game.start_sound("shotgn")
        saved = mo.angle
        mo.angle = as_u32(saved + ((p_random() - p_random()) << 20))
        line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE, mo.angle, slope)
        mo.angle = saved
    elif name == "CPosRefire":
        if mo.target is not None:
            _face_target(mo, mo.target)
        if p_random() < 40:
            return
        if mo.target is None or mo.target.health <= 0 or not check_sight(world, mo, mo.target):
            set_mobj_state(mo, _mi(mo)[MI_SEESTATE], world, game)
    elif name == "SpidRefire":
        if mo.target is not None:
            _face_target(mo, mo.target)
        if p_random() < 10:
            return
        if mo.target is None or mo.target.health <= 0 or not check_sight(world, mo, mo.target):
            set_mobj_state(mo, _mi(mo)[MI_SEESTATE], world, game)
    elif name == "TroopAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.start_sound("claw")
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 3)
        else:
            spawn_missile_mt(world, mo, mo.target, MT_TROOPSHOT, game)
    elif name == "SargAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 4)
    elif name == "HeadAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 10)
        else:
            spawn_missile_mt(world, mo, mo.target, MT_HEADSHOT, game)
    elif name == "BruisAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 10)
        else:
            spawn_missile_mt(world, mo, mo.target, MT_BRUISERSHOT, game)
    elif name == "SkullAttack":
        _skull_attack(mo, game)
    elif name == "CyberAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        spawn_missile_mt(world, mo, mo.target, MT_ROCKET, game)
    elif name == "BspiAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        spawn_missile_mt(world, mo, mo.target, MT_ARACHPLAZ, game)
    elif name == "Metal":
        game.start_sound("metal")
        _chase(world, mo, pl, game)
    elif name == "BabyMetal":
        game.start_sound("bspwlk")
        _chase(world, mo, pl, game)
    elif name == "Hoof":
        game.start_sound("hoof")
        _chase(world, mo, pl, game)
    elif name == "PainAttack":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        _pain_shoot_skull(world, mo, game, mo.angle)
    elif name == "PainDie":
        mo.flags &= ~MF_SOLID
        _pain_die(world, mo, game)
    elif name == "KeenDie":
        mo.flags &= ~MF_SOLID
        _keen_die(world, mo, game)
    elif name == "BossDeath":
        _boss_death(world, mo, game)
    elif name == "VileChase":
        if not _vile_chase(world, mo, game):
            _chase(world, mo, pl, game)
    elif name == "VileStart":
        game.start_sound("vilatk")
    elif name == "VileTarget":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        from .thinker import spawn_mobj

        fog = spawn_mobj(world, mo.target.x, mo.target.y, mo.target.z, MT_FIRE, game)
        mo.tracer = fog
        fog.target = mo
        fog.tracer = mo.target
    elif name == "VileAttack":
        _vile_attack(world, mo, game)
    elif name in ("StartFire", "Fire", "FireCrackle"):
        if name == "StartFire":
            game.start_sound("flamst")
        elif name == "FireCrackle":
            game.start_sound("flame")
        dest = mo.tracer
        targ = mo.target
        if dest is None or targ is None:
            return
        mo.x = dest.x
        mo.y = dest.y
        mo.z = dest.z
    elif name == "Tracer":
        if game.leveltime & 3:
            return
        if mo.tracer is None:
            mo.tracer = getattr(mo, "tracer", None)
        _tracer_home(mo)
    elif name == "SkelWhoosh":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        game.start_sound("skeswg")
    elif name == "SkelFist":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.start_sound("skepch")
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 6)
    elif name == "SkelMissile":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        miss = spawn_missile_mt(world, mo, mo.target, MT_TRACER, game)
        miss.tracer = mo.target
        miss.z += 16 * FRACUNIT
    elif name == "FatRaise":
        _face_target(mo, mo.target) if mo.target is not None else None
        game.start_sound("manatk")
    elif name == "FatAttack1":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        mo.angle = as_u32(mo.angle + FATSPREAD)
        spawn_missile_mt(world, mo, mo.target, MT_FATSHOT, game)
        miss = spawn_missile_mt(world, mo, mo.target, MT_FATSHOT, game)
        miss.angle = as_u32(miss.angle + FATSPREAD)
        miss.momx = fixed_mul(_mi(miss)[MI_SPEED], fine_cos(miss.angle))
        miss.momy = fixed_mul(_mi(miss)[MI_SPEED], fine_sin(miss.angle))
    elif name == "FatAttack2":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        mo.angle = as_u32(mo.angle - FATSPREAD)
        spawn_missile_mt(world, mo, mo.target, MT_FATSHOT, game)
        miss = spawn_missile_mt(world, mo, mo.target, MT_FATSHOT, game)
        miss.angle = as_u32(miss.angle - FATSPREAD * 2)
        miss.momx = fixed_mul(_mi(miss)[MI_SPEED], fine_cos(miss.angle))
        miss.momy = fixed_mul(_mi(miss)[MI_SPEED], fine_sin(miss.angle))
    elif name == "FatAttack3":
        if mo.target is None:
            return
        _face_target(mo, mo.target)
        miss = spawn_missile_mt(world, mo, mo.target, MT_FATSHOT, game)
        miss.angle = as_u32(mo.angle - FATSPREAD // 2)
        miss.momx = fixed_mul(_mi(miss)[MI_SPEED], fine_cos(miss.angle))
        miss.momy = fixed_mul(_mi(miss)[MI_SPEED], fine_sin(miss.angle))
        miss = spawn_missile_mt(world, mo, mo.target, MT_FATSHOT, game)
        miss.angle = as_u32(mo.angle + FATSPREAD // 2)
        miss.momx = fixed_mul(_mi(miss)[MI_SPEED], fine_cos(miss.angle))
        miss.momy = fixed_mul(_mi(miss)[MI_SPEED], fine_sin(miss.angle))
    elif name == "BrainPain":
        game.start_sound("bospn")
    elif name == "BrainScream":
        game.start_sound("bosdth")
    elif name == "BrainDie":
        _brain_die(game)
    elif name == "BrainAwake":
        _brain_awake(world, mo, game)
    elif name == "BrainSpit":
        _brain_spit(world, mo, game)
    elif name == "SpawnSound":
        game.start_sound("boscub")
        _a_spawn_fly(world, mo, game)
    elif name == "SpawnFly":
        _a_spawn_fly(world, mo, game)
    elif name == "BrainExplode":
        pass
    elif name == "BFGSpray":
        _bfg_spray(world, mo, game)
    elif name == "PlayerScream":
        if game:
            game.start_sound("pldeth")


def _a_spawn_fly(world, mo, game) -> None:
    mo.reactiontime -= 1
    if mo.reactiontime != 0:
        return
    _spawn_fly(world, mo, game)


