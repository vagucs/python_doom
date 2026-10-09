"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

P_SetMobjState / P_MobjThinker / P_SpawnMobj (p_mobj.prg).
"""

from __future__ import annotations

from .collision import check_position, point_in_subsector, try_move
from .compat import as_u32, fixed_mul
from .defs import (
    FRACUNIT,
    MF_CORPSE,
    MF_COUNTKILL,
    MF_FLOAT,
    MF_MISSILE,
    MF_NOGRAVITY,
    MF_SHOOTABLE,
    MF_SKULLFLY,
    MF_SOLID,
    MF_SPAWNCEILING,
    MTF_AMBUSH,
    SK_NIGHTMARE,
    TICRATE,
)
from .info import (
    ACTIONS,
    FF_FRAMEMASK,
    MI_DAMAGE,
    MI_DEATHSTATE,
    MI_DOOMEDNUM,
    MI_FLAGS,
    MI_HEIGHT,
    MI_RADIUS,
    MI_REACTIONTIME,
    MI_SPAWNHEALTH,
    MI_SPAWNSTATE,
    MI_SPEED,
    MOBJINFO,
    MT_SKULL,
    MT_TFOG,
    S_NULL,
    SPRNAMES,
    STATES,
    mobj_type_for_doomednum,
)
from .player import Mobj
from .tables import fine_cos, fine_sin

ONFLOORZ = -0x80000000
ONCEILINGZ = 0x7FFFFFFF


def _info(mo) -> list:
    return MOBJINFO[mo.type]


def spawn_mobj(world, x: int, y: int, z: int, typ: int, game=None) -> Mobj:
    """P_SpawnMobj."""
    info = MOBJINFO[typ]
    sub = point_in_subsector(world, x, y)
    mo = Mobj(
        x=x,
        y=y,
        z=0,
        radius=info[MI_RADIUS],
        height=info[MI_HEIGHT],
        floorz=sub.sector.floorheight,
        ceilingz=sub.sector.ceilingheight,
        flags=info[MI_FLAGS],
        health=info[MI_SPAWNHEALTH],
        type=typ,
        doomednum=info[MI_DOOMEDNUM],
        alive=True,
        damage=info[MI_DAMAGE],
    )
    if game is not None and getattr(game, "skill", 2) != SK_NIGHTMARE:
        mo.reactiontime = info[MI_REACTIONTIME]
    from .enemy import p_random

    mo.lastlook = p_random() % 4
    if z == ONCEILINGZ or (info[MI_FLAGS] & MF_SPAWNCEILING and z == ONFLOORZ):
        mo.z = mo.ceilingz - mo.height
    elif z == ONFLOORZ:
        mo.z = mo.floorz
    else:
        mo.z = z
    world.mobjs.append(mo)
    from .collision import set_thing_position

    set_thing_position(world, mo)
    # Vanilla does not call P_SetMobjState here: A_Look must wait until the
    # thinker advances, after P_SpawnMapThing has set the facing angle.
    state = info[MI_SPAWNSTATE]
    st = STATES[state]
    mo.istate = state
    mo.tics = st[2]
    mo.sprite = SPRNAMES[st[0]]
    mo.frame = st[1]
    return mo


def remove_mobj(world, mo) -> None:
    from .collision import unset_thing_position

    unset_thing_position(world, mo)
    mo.alive = False
    mo.istate = S_NULL
    mo.flags = 0
    if mo in world.mobjs:
        world.mobjs.remove(mo)


def set_mobj_state(mo, state: int, world, game) -> bool:
    """P_SetMobjState. Returns False if the mobj was removed."""
    from . import enemy as en

    safety = 0
    while True:
        if state == S_NULL or mo is None:
            if mo is not None and world is not None:
                remove_mobj(world, mo)
            return False
        st = STATES[state]
        mo.istate = state
        mo.tics = st[2]
        mo.sprite = SPRNAMES[st[0]]
        mo.frame = st[1]
        act = ACTIONS[st[3]]
        if act:
            en.call_action(act, mo, world, game)
            if not mo.alive:
                return False
        state = st[4]
        if mo.tics != 0:
            return True
        safety += 1
        if safety > 100:
            return True


def mobj_thinker(world, mo, game) -> None:
    """P_MobjThinker."""
    from . import enemy as en

    if mo.momx or mo.momy or (mo.flags & MF_SKULLFLY):
        en.p_xy_movement(world, mo, game)
        if not mo.alive:
            return
    if mo.z != mo.floorz or mo.momz:
        en.mobj_z(mo, world, game)
        if not mo.alive:
            return
    if mo.tics != -1:
        mo.tics -= 1
        if mo.tics <= 0:
            set_mobj_state(mo, STATES[mo.istate][4], world, game)
        return
    if (mo.flags & MF_COUNTKILL) == 0:
        return
    if not getattr(game, "respawnmonsters", False):
        return
    mo.movecount += 1
    if mo.movecount < 12 * TICRATE:
        return
    if (game.leveltime & 31) != 0:
        return
    if en.p_random() > 4:
        return
    nightmare_respawn(world, mo, game)


def nightmare_respawn(world, mo, game) -> None:
    sp = mo.spawnpoint
    if sp is None:
        return
    x, y = sp.x * FRACUNIT, sp.y * FRACUNIT
    chk = check_position(world, mo, x, y)
    if chk.blocked:
        return
    fog = spawn_mobj(world, mo.x, mo.y, mo.floorz, MT_TFOG, game)
    game.start_sound("telept")
    sub = point_in_subsector(world, x, y)
    spawn_mobj(world, x, y, sub.sector.floorheight, MT_TFOG, game)
    game.start_sound("telept")
    z = ONCEILINGZ if (_info(mo)[MI_FLAGS] & MF_SPAWNCEILING) else ONFLOORZ
    spawned = spawn_mobj(world, x, y, z, mo.type, game)
    spawned.spawnpoint = sp
    spawned.angle = as_u32((sp.angle // 45) * 0x20000000)
    if sp.options & MTF_AMBUSH:
        spawned.flags |= 32
    spawned.reactiontime = 18
    remove_mobj(world, mo)


def apply_fast(game) -> None:
    from .info import (
        MI_SPEED,
        MT_BRUISERSHOT,
        MT_HEADSHOT,
        MT_TROOPSHOT,
        S_SARG_PAIN2,
        S_SARG_RUN1,
    )

    want = bool(getattr(game, "fastparm", False) or game.skill == SK_NIGHTMARE)
    game.respawnmonsters = game.skill == SK_NIGHTMARE or bool(getattr(game, "respawnparm", False))
    if getattr(game, "_fast_on", None) == want:
        return
    if not hasattr(game, "_sarg_tics"):
        game._sarg_tics = [STATES[i][2] for i in range(S_SARG_RUN1, S_SARG_PAIN2 + 1)]
        game._shot_speed = {
            MT_BRUISERSHOT: MOBJINFO[MT_BRUISERSHOT][MI_SPEED],
            MT_HEADSHOT: MOBJINFO[MT_HEADSHOT][MI_SPEED],
            MT_TROOPSHOT: MOBJINFO[MT_TROOPSHOT][MI_SPEED],
        }
    game._fast_on = want
    for i, st in enumerate(range(S_SARG_RUN1, S_SARG_PAIN2 + 1)):
        STATES[st][2] = max(1, game._sarg_tics[i] // 2) if want else game._sarg_tics[i]
    fast = 20 * FRACUNIT
    for mt, spd in game._shot_speed.items():
        MOBJINFO[mt][MI_SPEED] = fast if want else spd
