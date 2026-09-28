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

from .collision import (
    angle_to,
    approx_distance,
    check_position,
    check_sight,
    line_attack,
    try_move,
)
from .compat import as_u32
from .defs import (
    ANG45,
    ANG90,
    ANG270,
    FRACUNIT,
    MELEERANGE,
    MF_AMBUSH,
    MF_CORPSE,
    MF_DROPOFF,
    MF_MISSILE,
    MF_NOGRAVITY,
    MF_SHOOTABLE,
    MF_SOLID,
    MISSILERANGE,
    ML_SOUNDBLOCK,
    ML_TWOSIDED,
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

# doomednum -> speed, attack, see sfx, death sfx, attack sfx, death frame, n death, walk tics
PROFILE = {
    3004: (8, "hitscan", "posit1", "podth1", "pistol", 7, 5, 4),
    9: (8, "shotgun", "posit2", "podth2", "shotgn", 7, 5, 3),
    3001: (8, "imp", "bgsit1", "bgdth1", "claw", 7, 6, 3),
    3002: (10, "melee", "sgtsit", "sgtdth", "sgtatk", 7, 6, 2),
    58: (10, "melee", "sgtsit", "sgtdth", "sgtatk", 7, 6, 2),
    3003: (8, "baron", "brssit", "brsdth", "claw", 7, 7, 3),
    3005: (8, "caco", "cacsit", "cacdth", "claw", 5, 6, 3),
    3006: (8, "melee", "sklatk", "firxpl", "sklatk", 5, 6, 3),
    16: (16, "hitscan", "cybsit", "cybdth", "pistol", 5, 9, 3),
    7: (12, "shotgun", "spisit", "spidth", "shotgn", 5, 10, 3),
    68: (12, "hitscan", "bspsit", "bspdth", "plasma", 5, 7, 3),
    69: (8, "baron", "kntsit", "kntdth", "claw", 7, 7, 3),
    84: (8, "hitscan", "posit1", "podth1", "pistol", 7, 5, 3),
    2035: (0, "none", None, "barexp", None, 0, 5, 4),
}

_seed = 1


def _walk_tics(mo) -> int:
    prof = PROFILE.get(mo.type)
    if prof and len(prof) > 7:
        return prof[7]
    return 3


def p_random() -> int:
    global _seed
    _seed = (_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return (_seed >> 16) & 255


def tick_enemies(world, game) -> None:
    player = game.player
    if player is None or player.mo is None:
        return
    # copy list: missiles may be added/removed
    for mo in list(world.mobjs):
        if mo is player.mo:
            continue
        if mo.flags & MF_MISSILE:
            _tick_missile(world, mo, game)
            continue
        info = mo.info
        if not info or info[0] != "enemy":
            continue
        if mo.health <= 0:
            _tick_dead(mo)
            continue
        prof = PROFILE.get(mo.type)
        if prof and prof[1] == "none":
            continue
        if mo.ai_state == "attack":
            _tick_attack(world, mo, game)
        elif mo.ai_state == "chase":
            if mo.chase_tics > 0:
                mo.chase_tics -= 1
            else:
                _chase(world, mo, player.mo, game)
                if mo.ai_state == "chase":
                    mo.chase_tics = max(0, _walk_tics(mo) - 1)
        else:
            _tick_stand(mo)
            _look(world, mo, player.mo, game)


def _tick_stand(mo) -> None:
    """S_*_STND / STND2: idle frames 0↔1 every 10 tics while A_Look runs."""
    if mo.tics > 0:
        mo.tics -= 1
        return
    # Cacodemon stand loops on frame 0 only; everyone else breathes A/B.
    n = 1 if mo.type == 3005 else 2
    mo.frame = (int(mo.frame) + 1) % n
    mo.tics = 10


def kill_monster(mo, game, source) -> None:
    mo.health = 0
    mo.flags &= ~(MF_SOLID | MF_SHOOTABLE)
    mo.flags |= MF_CORPSE
    mo.target = None
    mo.ai_state = "die"
    prof = PROFILE.get(mo.type)
    if prof:
        _speed, attack, _see, dsfx, _atk, d0, dn = prof[:7]
        mo.frame = d0
        mo.tics = 5
        if attack == "none":
            mo.sprite = "BEXP"
            mo.frame = 0
        if dsfx:
            game.start_sound(dsfx)
        if mo.type == 2035:
            _explode_barrel(game.world, mo, game)
    else:
        mo.frame = 7
        mo.tics = 5
        game.start_sound("podth1")
    if source and source.player:
        source.player.killcount += 1


def _tick_dead(mo) -> None:
    if mo.ai_state != "die":
        return
    if mo.tics > 0:
        mo.tics -= 1
        return
    prof = PROFILE.get(mo.type)
    d0, dn = (7, 5) if not prof else (prof[5], prof[6])
    if mo.sprite == "BEXP":
        d0, dn = 0, 5
    if mo.frame + 1 < d0 + dn:
        mo.frame += 1
        mo.tics = 5
    else:
        mo.ai_state = "dead"


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

    if player_mo is None or not (player_mo.flags & MF_SHOOTABLE):
        return
    see = False
    sec = point_in_subsector(world, mo.x, mo.y).sector
    targ = sec.soundtarget
    if targ is not None and (getattr(targ, "flags", 0) & MF_SHOOTABLE):
        mo.target = targ
        if mo.flags & MF_AMBUSH:
            see = check_sight(world, mo, targ)
        else:
            see = True
    if not see and not _look_for_players(world, mo, player_mo):
        return
    mo.target = player_mo if mo.target is None else mo.target
    mo.ai_state = "chase"
    mo.movedir = DI_NODIR
    mo.movecount = 0
    prof = PROFILE.get(mo.type)
    if prof and prof[2]:
        game.start_sound(prof[2])
    mo.frame = 0


def _look_for_players(world, mo, player_mo) -> bool:
    """P_LookForPlayers(allaround=False): sight plus 180° field of view."""
    if player_mo.health <= 0 or not (player_mo.flags & MF_SHOOTABLE):
        return False
    if not check_sight(world, mo, player_mo):
        return False
    an = (angle_to(mo.x, mo.y, player_mo.x, player_mo.y) - mo.angle) & 0xFFFFFFFF
    if an > ANG90 and an < ANG270:
        dist = approx_distance(player_mo.x - mo.x, player_mo.y - mo.y)
        if dist > MELEERANGE:
            return False
    mo.target = player_mo
    return True


def _chase(world, mo, player_mo, game) -> None:
    if mo.reactiontime:
        mo.reactiontime -= 1
    target = mo.target if mo.target is not None else player_mo
    if target is None or target.health <= 0 or not (target.flags & MF_SHOOTABLE):
        mo.target = None
        mo.ai_state = "look"
        mo.frame = 0
        mo.tics = 10
        return
    mo.target = target
    if mo.just_attacked:
        mo.just_attacked = False
        _new_chase_dir(world, mo, game)
        return
    if mo.movedir == DI_NODIR:
        _new_chase_dir(world, mo, game)
    _face_movedir(mo)
    dist = approx_distance(target.x - mo.x, target.y - mo.y)
    prof = PROFILE.get(mo.type, (8, "hitscan", None, None, None, 7, 5, 3))
    speed, attack, _see, _dth, atksfx, _d0, _dn = prof[:7]
    if attack == "none":
        return
    melee = attack in ("melee", "imp", "baron", "caco")
    missile = attack in ("hitscan", "shotgun", "imp", "baron", "caco")
    melee_range = MELEERANGE - 20 * FRACUNIT + getattr(target, "radius", 16 * FRACUNIT)
    if melee and dist < melee_range and check_sight(world, mo, target):
        if atksfx:
            game.start_sound(atksfx)
        _start_attack(mo, "melee")
        return
    if missile and mo.movecount == 0 and _missile_ok(world, mo, target, dist, has_melee=melee):
        _start_attack(mo, attack)
        mo.just_attacked = True
        return
    mo.movecount -= 1
    if mo.movecount < 0 or not _move(world, mo, speed, game):
        _new_chase_dir(world, mo, game)
    mo.frame = (mo.frame + 1) % 4


def _missile_ok(world, mo, target, dist: int, has_melee: bool) -> bool:
    if not check_sight(world, mo, target):
        return False
    if mo.reactiontime:
        return False
    d = dist - 64 * FRACUNIT
    if not has_melee:
        d -= 128 * FRACUNIT
    d >>= 16
    if d < 0:
        return True
    if d > 200:
        d = 200
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
        mo.ai_state = "chase"
        mo.frame = 0
        mo.movecount = 15 + (p_random() & 15)


def _do_attack(world, mo, game) -> None:
    kind = getattr(mo, "_attack_kind", "hitscan")
    saved = mo.angle
    _face_target(mo, mo.target)
    if kind == "melee":
        dist = approx_distance(mo.target.x - mo.x, mo.target.y - mo.y)
        if dist < MELEERANGE + mo.radius:
            game.damage_mobj(mo.target, mo, ((p_random() % 8) + 1) * 3)
    elif kind == "shotgun":
        game.start_sound("shotgn")
        for _ in range(3):
            mo.angle = as_u32(saved + ((p_random() - p_random()) << 20))
            line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE)
        mo.angle = saved
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
            _spawn_missile(world, mo, mo.target, sprite, speed, dmg)
    else:
        game.start_sound("pistol")
        mo.angle = as_u32(saved + ((p_random() - p_random()) << 20))
        line_attack(world, mo, ((p_random() % 5) + 1) * 3, game, MISSILERANGE)
        mo.angle = saved


def _face_target(mo, target) -> None:
    mo.angle = angle_to(mo.x, mo.y, target.x, target.y)


def _face_movedir(mo) -> None:
    if 0 <= mo.movedir < 8:
        want = as_u32(mo.movedir * ANG45)
        delta = (want - mo.angle) & 0xFFFFFFFF
        if delta == 0:
            return
        step = ANG45 // 2
        if delta < 0x80000000:
            mo.angle = as_u32(mo.angle + min(step, delta))
        else:
            mo.angle = as_u32(mo.angle - min(step, (0x100000000 - delta)))


def _move(world, mo, speed: int, game) -> bool:
    if mo.movedir < 0 or mo.movedir >= 8:
        return False
    nx = mo.x + speed * XSPEED[mo.movedir]
    ny = mo.y + speed * YSPEED[mo.movedir]
    chk = check_position(world, mo, nx, ny)
    if not try_move(world, mo, nx, ny, game):
        if game:
            for ln in chk.spechit:
                if ln.special:
                    game.use_special(ln, mo, 0)
        return False
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
    prof = PROFILE.get(mo.type, (8, "hitscan", None, None, None, 7, 5))
    speed = prof[0]
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


def _spawn_missile(world, source, dest, sprite: str, speed: int, damage: int) -> None:
    from .compat import fixed_mul

    ang = angle_to(source.x, source.y, dest.x, dest.y)
    dist = approx_distance(dest.x - source.x, dest.y - source.y)
    steps = dist // speed if speed else 1
    if steps < 1:
        steps = 1
    mo = Mobj(
        x=source.x + fixed_mul(12 * FRACUNIT, fine_cos(ang)),
        y=source.y + fixed_mul(12 * FRACUNIT, fine_sin(ang)),
        z=source.z + 32 * FRACUNIT,
        angle=ang,
        radius=6 * FRACUNIT,
        height=8 * FRACUNIT,
        floorz=source.floorz,
        ceilingz=source.ceilingz,
        flags=MF_MISSILE | MF_DROPOFF | MF_NOGRAVITY,
        health=1000,
        type=0,
        sprite=sprite,
        info=("missile", None),
        alive=True,
        damage=damage,
        ai_state="missile",
        frame=0,
        target=source,
        momx=fixed_mul(speed, fine_cos(ang)),
        momy=fixed_mul(speed, fine_sin(ang)),
        momz=int((dest.z - source.z) / steps),
    )
    # P_CheckMissileSpawn: step halfway, explode if already stuck
    mo.x += mo.momx >> 1
    mo.y += mo.momy >> 1
    mo.z += mo.momz >> 1
    world.mobjs.append(mo)


def _tick_missile(world, mo, game) -> None:
    nx = mo.x + mo.momx
    ny = mo.y + mo.momy
    chk = check_position(world, mo, nx, ny)
    if chk.blocked or not try_move(world, mo, nx, ny, game):
        hit = chk.hit_thing if chk.hit_thing is not None and chk.hit_thing is not mo else None
        _explode_missile(world, mo, game, hit=hit)
        return
    mo.z += mo.momz
    if mo.z <= mo.floorz or mo.z + mo.height > mo.ceilingz:
        _explode_missile(world, mo, game, hit=None)
        return
    mo.frame = (mo.frame + 1) & 1


def _explode_missile(world, mo, game, hit) -> None:
    if hit is not None:
        src = mo.target if mo.target is not None else mo
        game.damage_mobj(hit, src, mo.damage * ((p_random() % 8) + 1), inflictor=mo)
    game.start_sound("firxpl")
    if mo in world.mobjs:
        world.mobjs.remove(mo)


def _explode_barrel(world, barrel, game) -> None:
    for other in list(world.mobjs):
        if other is barrel or not (other.flags & MF_SHOOTABLE):
            continue
        dist = approx_distance(other.x - barrel.x, other.y - barrel.y) - other.radius
        if dist < 0:
            dist = 0
        if dist >= 128 * FRACUNIT:
            continue
        game.damage_mobj(other, barrel, (128 * FRACUNIT - dist) >> 16)
