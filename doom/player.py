"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Player movement and weapons (p_user / p_pspr / d_player).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .collision import (
    angle_to,
    bullet_slope,
    get_bulletslope,
    line_attack,
    point_in_subsector,
    slide_move,
    use_lines,
)
from .compat import as_u32, fixed_mul
from .defs import (
    AM_CELL,
    AM_CLIP,
    AM_MISL,
    AM_SHELL,
    ANG90,
    ANG180,
    BT_ATTACK,
    BT_CHANGE,
    BT_SPECIAL,
    BT_USE,
    BT_WEAPONMASK,
    BT_WEAPONSHIFT,
    FINEANGLES,
    FINEMASK,
    FRACUNIT,
    FRICTION,
    GRAVITY,
    INFRATICS,
    INVERSECOLORMAP,
    INVISTICS,
    INVULNTICS,
    IRONTICS,
    MAXBOB,
    MAXHEALTH,
    MELEERANGE,
    MISSILERANGE,
    MF_DROPOFF,
    MF_JUSTATTACKED,
    MF_NOCLIP,
    MF_PICKUP,
    MF_SHADOW,
    MF_SHOOTABLE,
    MF_SOLID,
    PLAYER_HEIGHT,
    PLAYER_RADIUS,
    PST_DEAD,
    PST_LIVE,
    PST_REBORN,
    PW_INFRARED,
    PW_INVISIBILITY,
    PW_INVULNERABILITY,
    PW_IRONFEET,
    PW_STRENGTH,
    STOPSPEED,
    TICRATE,
    VIEWHEIGHT,
    WP_BFG,
    WP_CHAINGUN,
    WP_CHAINSAW,
    WP_FIST,
    WP_MISSILE,
    WP_NOCHANGE,
    WP_PISTOL,
    WP_PLASMA,
    WP_SHOTGUN,
    WP_SUPERSHOTGUN,
)
from .tables import fine_cos, fine_sin
from .sprites import LOWERSPEED, RAISESPEED, WEAPONBOTTOM, WEAPONTOP


FORWARDMOVE = (0x19, 0x32)
SIDEMOVE = (0x18, 0x28)
ANGLETURN = (640, 1280, 320)

MAXAMMO = (200, 50, 300, 50)
CLIPAMMO = (10, 4, 20, 1)


@dataclass
class Ticcmd:
    forwardmove: int = 0
    sidemove: int = 0
    angleturn: int = 0
    buttons: int = 0


@dataclass(eq=False)
class Mobj:
    x: int = 0
    y: int = 0
    z: int = 0
    angle: int = 0
    momx: int = 0
    momy: int = 0
    momz: int = 0
    radius: int = PLAYER_RADIUS
    height: int = PLAYER_HEIGHT
    floorz: int = 0
    ceilingz: int = 0
    flags: int = MF_SOLID | MF_SHOOTABLE | MF_PICKUP | MF_DROPOFF
    health: int = 100
    player: object | None = None
    type: int = 1
    sprite: str = ""
    info: object | None = None
    alive: bool = True
    reactiontime: int = 0
    lastlook: int = 0
    target: object | None = None
    movedir: int = 0  # DI_EAST; vanilla/Harbour/PHP default (not DI_NODIR)
    movecount: int = 0
    threshold: int = 0  # BASETHRESHOLD after damage (PHP/vanilla)
    ai_state: str = ""
    frame: int = 0
    tics: int = 0
    chase_tics: int = 0
    just_attacked: bool = False
    damage: int = 0
    missile_kind: str = ""
    tracer: object | None = None
    istate: int = 0
    spawnpoint: object | None = None
    doomednum: int = -1
    bnext: object | None = None
    bprev: object | None = None
    blocklinked: bool = False

    @property
    def _tmx(self) -> int:
        return getattr(self, "_tmx_val", self.x)

    @_tmx.setter
    def _tmx(self, v: int) -> None:
        self._tmx_val = v

    @property
    def _tmy(self) -> int:
        return getattr(self, "_tmy_val", self.y)

    @_tmy.setter
    def _tmy(self, v: int) -> None:
        self._tmy_val = v


@dataclass
class Player:
    mo: Mobj | None = None
    cmd: Ticcmd = field(default_factory=Ticcmd)
    playerstate: int = PST_LIVE
    viewz: int = 0
    viewheight: int = VIEWHEIGHT
    deltaviewheight: int = 0
    bob: int = 0
    health: int = 100
    armorpoints: int = 0
    armortype: int = 0
    ammo: list = field(default_factory=lambda: [50, 0, 0, 0])
    maxammo: list = field(default_factory=lambda: list(MAXAMMO))
    weaponowned: list = field(default_factory=lambda: [True, True] + [False] * 7)
    pendingweapon: int = WP_NOCHANGE
    readyweapon: int = WP_PISTOL
    cards: list = field(default_factory=lambda: [False] * 6)
    cheats: int = 0
    message: str = ""
    message_tics: int = 0
    attackdown: bool = False
    usedown: bool = False
    damagecount: int = 0
    bonuscount: int = 0
    attacker: object | None = None
    extralight: int = 0
    fixedcolormap: int = 0
    refire: int = 0
    killcount: int = 0
    itemcount: int = 0
    secretcount: int = 0
    didsecret: bool = False
    psprite_y: int = 32
    psprite_sy: int = 128 * FRACUNIT
    psprite_state: str = "up"
    psprite_tics: int = 0
    psprite_step: int = 0
    psprite_body: str = ""
    psprite_flash: str = ""
    flash_tics: int = 0
    powers: list = field(default_factory=lambda: [0] * 6)

    def set_message(self, text: str) -> None:
        from .deh import deh_string

        self.message = deh_string(text)
        self.message_tics = 4 * TICRATE


def give_power(player: Player, power: int) -> bool:
    """P_GivePower: timed powers refresh; allmap is once-only."""
    if power == PW_INVULNERABILITY:
        player.powers[power] = INVULNTICS
        return True
    if power == PW_INVISIBILITY:
        player.powers[power] = INVISTICS
        if player.mo is not None:
            player.mo.flags |= MF_SHADOW
        return True
    if power == PW_INFRARED:
        player.powers[power] = INFRATICS
        return True
    if power == PW_IRONFEET:
        player.powers[power] = IRONTICS
        return True
    if power == PW_STRENGTH:
        if player.health < MAXHEALTH:
            player.health = min(MAXHEALTH, player.health + 100)
            if player.mo is not None:
                player.mo.health = player.health
        player.powers[power] = 1
        return True
    if player.powers[power]:
        return False
    player.powers[power] = 1
    return True


def spawn_player(world, start, cheats: int = 0) -> Player:
    from .collision import set_thing_position
    from .deh import deh
    from .enemy import p_random
    from .info import MI_SPAWNSTATE, MOBJINFO, MT_PLAYER, SPRNAMES, STATES

    sub = point_in_subsector(world, start.x * FRACUNIT, start.y * FRACUNIT)
    mo = Mobj(
        x=start.x * FRACUNIT,
        y=start.y * FRACUNIT,
        z=sub.sector.floorheight,
        angle=as_u32((start.angle // 45) * 0x20000000),
        floorz=sub.sector.floorheight,
        ceilingz=sub.sector.ceilingheight,
        type=MT_PLAYER,
    )
    player = Player(mo=mo, cheats=cheats)
    mo.player = player
    player.health = deh.initial_health
    mo.health = deh.initial_health
    player.ammo = [deh.initial_bullets, 0, 0, 0]
    player.maxammo = list(deh.maxammo)
    if cheats & 1:
        mo.flags |= MF_NOCLIP
    player.viewz = mo.z + VIEWHEIGHT
    # Must set S_PLAY before mobj_thinker runs: istate 0 is S_NULL and would remove us.
    state = MOBJINFO[MT_PLAYER][MI_SPAWNSTATE]
    st = STATES[state]
    mo.istate = state
    mo.tics = st[2]
    mo.sprite = SPRNAMES[st[0]]
    mo.frame = st[1]
    mo.lastlook = p_random() % 4
    world.mobjs.append(mo)
    set_thing_position(world, mo)
    return player


def thrust(mo: Mobj, angle: int, move: int) -> None:
    mo.momx += fixed_mul(move, fine_cos(angle))
    mo.momy += fixed_mul(move, fine_sin(angle))


def calc_height(player: Player, leveltime: int) -> None:
    mo = player.mo
    assert mo is not None
    player.bob = (fixed_mul(mo.momx, mo.momx) + fixed_mul(mo.momy, mo.momy)) // 4
    if player.bob > MAXBOB:
        player.bob = MAXBOB
    onground = mo.z <= mo.floorz
    if not onground:
        player.viewz = mo.z + player.viewheight
        if player.viewz > mo.ceilingz - 4 * FRACUNIT:
            player.viewz = mo.ceilingz - 4 * FRACUNIT
        return
    from .defs import FINEANGLES
    from .tables import finesine

    angle = (FINEANGLES // 20 * leveltime) & FINEMASK
    bob = fixed_mul(player.bob // 2, finesine[angle] if finesine else 0)
    if player.playerstate == PST_LIVE:
        player.viewheight += player.deltaviewheight
        if player.viewheight > VIEWHEIGHT:
            player.viewheight = VIEWHEIGHT
            player.deltaviewheight = 0
        if player.viewheight < VIEWHEIGHT // 2:
            player.viewheight = VIEWHEIGHT // 2
            if player.deltaviewheight <= 0:
                player.deltaviewheight = 1
        if player.deltaviewheight:
            player.deltaviewheight += FRACUNIT // 4 or 1
    player.viewz = mo.z + player.viewheight + bob
    if player.viewz > mo.ceilingz - 4 * FRACUNIT:
        player.viewz = mo.ceilingz - 4 * FRACUNIT


def xy_movement(world, mo: Mobj, game) -> None:
    from .enemy import p_xy_movement

    p_xy_movement(world, mo, game)


def z_movement(mo: Mobj, world=None, game=None) -> None:
    from .enemy import mobj_z

    mobj_z(mo, world, game)


def _special_sector(world, player: Player, game, leveltime: int) -> None:
    """P_PlayerInSpecialSector — Harbour p_spec.prg (mo.subsector, short-circuit OR)."""
    from .enemy import p_random

    mo = player.mo
    if mo is None:
        return
    # Harbour: sector := player:mo:subsector:sector (not a fresh point query).
    sub = getattr(mo, "subsector", None) or point_in_subsector(world, mo.x, mo.y)
    sector = sub.sector
    if mo.z != sector.floorheight or not sector.special:
        return
    spec = sector.special
    if spec == 9:
        player.secretcount += 1
        sector.special = 0
        return
    if spec == 11:
        from .defs import CF_GODMODE

        player.cheats &= ~CF_GODMODE
        if (leveltime & 0x1F) == 0:
            game.damage_mobj(mo, None, 20)
        if player.health <= 10 and game.specials:
            game.specials.exit_requested = True
        return
    if spec not in (5, 7, 4, 16):
        return
    # CASE 4/16: ironfeet==0 .OR. P_Random()<5 (P_Random only when suit is on).
    if spec in (4, 16):
        if player.powers[PW_IRONFEET] and p_random() >= 5:
            return
    elif player.powers[PW_IRONFEET]:
        return
    if (leveltime & 0x1F) == 0:
        damage = 5 if spec == 7 else (10 if spec == 5 else 20)
        game.damage_mobj(mo, None, damage)


def _death_think(world, player: Player, game, leveltime: int) -> None:
    mo = player.mo
    assert mo is not None
    cmd = player.cmd
    if player.viewheight > 6 * FRACUNIT:
        player.viewheight -= FRACUNIT
    if player.viewheight < 6 * FRACUNIT:
        player.viewheight = 6 * FRACUNIT
    player.deltaviewheight = 0
    # XY/Z run in mobj_thinker (tick_enemies), not here.
    calc_height(player, leveltime)
    if player.attacker is not None and player.attacker is not mo:
        angle = angle_to(mo.x, mo.y, player.attacker.x, player.attacker.y)
        delta = as_u32(angle - mo.angle)
        ang5 = ANG90 // 18
        if delta < as_u32(ang5) or delta > as_u32(-ang5):
            mo.angle = angle
            if player.damagecount:
                player.damagecount -= 1
        elif delta < as_u32(ANG180):
            mo.angle = as_u32(mo.angle + ang5)
        else:
            mo.angle = as_u32(mo.angle - ang5)
    elif player.damagecount:
        player.damagecount -= 1
    _weapon_think(player, game)
    if cmd.buttons & BT_USE:
        player.playerstate = PST_REBORN


def player_think(world, player: Player, game, leveltime: int) -> None:
    mo = player.mo
    assert mo is not None
    cmd = player.cmd
    if mo.flags & MF_JUSTATTACKED:
        cmd.angleturn = 0
        cmd.forwardmove = 0xC800 // 512
        cmd.sidemove = 0
        mo.flags &= ~MF_JUSTATTACKED
    if player.playerstate == PST_DEAD:
        _death_think(world, player, game, leveltime)
        return
    if mo.reactiontime:
        mo.reactiontime -= 1
    else:
        mo.angle = as_u32(mo.angle + (cmd.angleturn << 16))
        if mo.z <= mo.floorz:
            if cmd.forwardmove:
                thrust(mo, mo.angle, cmd.forwardmove * 2048)
            if cmd.sidemove:
                thrust(mo, as_u32(mo.angle - ANG90), cmd.sidemove * 2048)
        # XY/Z run in mobj_thinker (tick_enemies), not here.
        from .info import S_PLAY, S_PLAY_RUN1
        from .thinker import set_mobj_state

        if (cmd.forwardmove or cmd.sidemove) and mo.istate == S_PLAY:
            set_mobj_state(mo, S_PLAY_RUN1, world, game)
    calc_height(player, leveltime)
    _special_sector(world, player, game, leveltime)
    # P_PlayerThink: BT_SPECIAL clears other buttons; then weapon change; then use.
    if cmd.buttons & BT_SPECIAL:
        cmd.buttons = 0
    if cmd.buttons & BT_CHANGE:
        # Fist↔chainsaw and shotgun↔SSG remaps (vanilla / demos).
        neww = (cmd.buttons & BT_WEAPONMASK) >> BT_WEAPONSHIFT
        if (
            neww == WP_FIST
            and player.weaponowned[WP_CHAINSAW]
            and not (player.readyweapon == WP_CHAINSAW and player.powers[PW_STRENGTH])
        ):
            neww = WP_CHAINSAW
        wad = getattr(game, "wad", None)
        commercial = wad is not None and wad.check_num_for_name("MAP01") >= 0
        shareware = (not commercial) and wad is not None and wad.check_num_for_name("E2M1") < 0
        if (
            commercial
            and neww == WP_SHOTGUN
            and player.weaponowned[WP_SUPERSHOTGUN]
            and player.readyweapon != WP_SUPERSHOTGUN
        ):
            neww = WP_SUPERSHOTGUN
        if (
            player.weaponowned[neww]
            and neww != player.readyweapon
            and 0 <= neww <= WP_SUPERSHOTGUN
            and ((neww != WP_PLASMA and neww != WP_BFG) or not shareware)
        ):
            player.pendingweapon = neww
    if cmd.buttons & BT_USE:
        if not player.usedown:
            use_lines(world, player, game)
            player.usedown = True
    else:
        player.usedown = False
    _weapon_think(player, game)
    if player.powers[PW_STRENGTH]:
        player.powers[PW_STRENGTH] += 1
    if player.powers[PW_INVULNERABILITY]:
        player.powers[PW_INVULNERABILITY] -= 1
    if player.powers[PW_INVISIBILITY]:
        player.powers[PW_INVISIBILITY] -= 1
        if player.powers[PW_INVISIBILITY] == 0 and player.mo is not None:
            player.mo.flags &= ~MF_SHADOW
    if player.powers[PW_INFRARED]:
        player.powers[PW_INFRARED] -= 1
    if player.powers[PW_IRONFEET]:
        player.powers[PW_IRONFEET] -= 1
    inv = player.powers[PW_INVULNERABILITY]
    ir = player.powers[PW_INFRARED]
    if inv:
        player.fixedcolormap = INVERSECOLORMAP if inv > 4 * 32 or (inv & 8) else 0
    elif ir:
        player.fixedcolormap = 1 if ir > 4 * 32 or (ir & 8) else 0
    else:
        player.fixedcolormap = 0
    if player.damagecount:
        player.damagecount -= 1
    if player.bonuscount:
        player.bonuscount -= 1
    if player.message_tics:
        player.message_tics -= 1
        if player.message_tics <= 0:
            player.message = ""


WEAPON_AMMO = {
    WP_PISTOL: AM_CLIP,
    WP_SHOTGUN: AM_SHELL,
    WP_SUPERSHOTGUN: AM_SHELL,
    WP_CHAINGUN: AM_CLIP,
    WP_MISSILE: AM_MISL,
    WP_PLASMA: AM_CELL,
    WP_BFG: AM_CELL,
}

WEAPON_SHOT = {
    WP_FIST: (2, MELEERANGE, None),
    WP_CHAINSAW: (3, MELEERANGE, "sawful"),
    WP_PISTOL: (5, MISSILERANGE, "pistol"),
    WP_SHOTGUN: (7, MISSILERANGE, "shotgn"),
    WP_SUPERSHOTGUN: (8, MISSILERANGE, "dshtgn"),
    WP_CHAINGUN: (5, MISSILERANGE, "pistol"),
    WP_MISSILE: (20, MISSILERANGE, "rlaunc"),
    WP_PLASMA: (5, MISSILERANGE, "plasma"),
    WP_BFG: (100, MISSILERANGE, "bfg"),
}

WEAPON_PATCH = {
    WP_FIST: "PUNGA0",
    WP_PISTOL: "PISGA0",
    WP_SHOTGUN: "SHTGA0",
    WP_CHAINGUN: "CHGGA0",
    WP_MISSILE: "MISGA0",
    WP_PLASMA: "PLSGA0",
    WP_BFG: "BFGGA0",
    WP_CHAINSAW: "SAWGC0",
    WP_SUPERSHOTGUN: "SHT2A0",
}

WEAPON_FIRE_PATCH = {
    WP_PISTOL: "PISFA0",
    WP_SHOTGUN: "SHTFA0",
    WP_CHAINGUN: "CHGFA0",
    WP_MISSILE: "MISFA0",
    WP_PLASMA: "PLSFA0",
    WP_BFG: "BFGFA0",
    WP_CHAINSAW: "SAWGB0",
    WP_SUPERSHOTGUN: "SHT2B0",
}

# Gun body while the muzzle flash is up (info.prg attack frame, not the idle A).
WEAPON_FIRE_BODY = {
    WP_FIST: "PUNGC0",
    WP_PISTOL: "PISGB0",
    WP_SHOTGUN: "SHTGA0",
    WP_CHAINGUN: "CHGGB0",
    WP_MISSILE: "MISGB0",
    WP_PLASMA: "PLSGA0",
    WP_BFG: "BFGGB0",
    WP_CHAINSAW: "SAWGA0",
    WP_SUPERSHOTGUN: "SHT2A0",
}

# Attack states: (body, tics, do_fire, flash, flash_tics, light[, refire])
# Trailing True = A_ReFire (bump refire before CheckAmmo / restart).
WEAPON_ATK = {
    WP_FIST: (
        ("PUNGB0", 4, False, "", 0, 0),
        ("PUNGC0", 4, True, "", 0, 0),
        ("PUNGD0", 5, False, "", 0, 0),
        ("PUNGC0", 4, False, "", 0, 0),
        ("PUNGB0", 5, False, "", 0, 0, True),
    ),
    WP_PISTOL: (
        ("PISGA0", 4, False, "", 0, 0),
        ("PISGB0", 6, True, "PISFA0", 7, 1),
        ("PISGC0", 4, False, "", 0, 0),
        ("PISGB0", 5, False, "", 0, 0, True),
    ),
    WP_SHOTGUN: (
        ("SHTGA0", 3, False, "", 0, 0),
        ("SHTGA0", 7, True, "SHTFA0", 7, 1),
        ("SHTGB0", 5, False, "", 0, 0),
        ("SHTGC0", 5, False, "", 0, 0),
        ("SHTGD0", 4, False, "", 0, 0),
        ("SHTGC0", 5, False, "", 0, 0),
        ("SHTGB0", 5, False, "", 0, 0),
        ("SHTGA0", 3, False, "", 0, 0),
        ("SHTGA0", 7, False, "", 0, 0, True),
    ),
    # S_CHAIN1 Fire, S_CHAIN2 Fire, S_CHAIN3 ReFire (tics 0).
    WP_CHAINGUN: (
        ("CHGGA0", 4, True, "CHGFA0", 5, 1),
        ("CHGGB0", 4, True, "CHGFB0", 5, 2),
        ("CHGGA0", 0, False, "", 0, 0, True),
    ),
    # S_MISSILE1 flash 3, S_MISSILE2 Fire, S_MISSILE3 ReFire 0
    WP_MISSILE: (
        ("MISGB0", 8, False, "MISFA0", 3, 1),
        ("MISGB0", 12, True, "", 0, 2),
        ("MISGA0", 0, False, "", 0, 0, True),
    ),
    WP_PLASMA: (
        ("PLSGA0", 3, True, "PLSFA0", 4, 1),
        ("PLSGB0", 20, False, "", 0, 0, True),
    ),
    WP_BFG: (
        ("BFGGA0", 20, False, "", 0, 0),
        ("BFGGB0", 10, False, "BFGFA0", 11, 1),
        ("BFGGB0", 10, True, "", 0, 2),
        ("BFGGB0", 20, False, "", 0, 0, True),
    ),
    # S_SAW2/S_SAW3: A_Saw loops with no A_ReFire.
    WP_CHAINSAW: (
        ("SAWGA0", 4, True, "", 0, 0),
        ("SAWGB0", 4, True, "", 0, 0),
    ),
    # Vanilla S_DSGUN*: CloseShotgun2 calls A_ReFire (skips DSGUN9/10 when holding fire).
    # step[6]: True = A_ReFire; "checkreload" = A_CheckReload (P_CheckAmmo).
    WP_SUPERSHOTGUN: (
        ("SHT2A0", 3, False, "", 0, 0),  # S_DSGUN1
        ("SHT2A0", 7, True, "SHT2I0", 9, 1),  # S_DSGUN2 A_FireShotgun2
        ("SHT2B0", 7, False, "", 0, 0),  # S_DSGUN3
        ("SHT2C0", 7, False, "", 0, 0, "checkreload"),  # S_DSGUN4 A_CheckReload
        ("SHT2D0", 7, False, "", 0, 0),  # S_DSGUN5 A_OpenShotgun2
        ("SHT2E0", 7, False, "", 0, 0),  # S_DSGUN6
        ("SHT2F0", 7, False, "", 0, 0),  # S_DSGUN7 A_LoadShotgun2
        ("SHT2G0", 6, False, "", 0, 0),  # S_DSGUN8
        ("SHT2H0", 6, False, "", 0, 0, True),  # S_DSGUN9 A_CloseShotgun2 → A_ReFire
        ("SHT2A0", 5, False, "", 0, 0, True),  # S_DSGUN10 A_ReFire
    ),
}

# Idle ready cycle (info.prg A_WeaponReady). Chainsaw breathes C↔D; others stay on A.
WEAPON_READY = {
    WP_CHAINSAW: (("SAWGC0", 4, "sawidl"), ("SAWGD0", 4, "")),
}


def _select_fallback(player: Player, game) -> None:
    """P_CheckAmmo: Harbour preference order when the ready weapon is empty."""
    wad = getattr(game, "wad", None)
    commercial = wad is not None and wad.check_num_for_name("MAP01") >= 0
    shareware = (not commercial) and wad is not None and wad.check_num_for_name("E2M1") < 0
    if player.weaponowned[WP_PLASMA] and player.ammo[AM_CELL] != 0 and not shareware:
        player.pendingweapon = WP_PLASMA
    elif player.weaponowned[WP_SUPERSHOTGUN] and player.ammo[AM_SHELL] > 2 and commercial:
        player.pendingweapon = WP_SUPERSHOTGUN
    elif player.weaponowned[WP_CHAINGUN] and player.ammo[AM_CLIP] != 0:
        player.pendingweapon = WP_CHAINGUN
    elif player.weaponowned[WP_SHOTGUN] and player.ammo[AM_SHELL] != 0:
        player.pendingweapon = WP_SHOTGUN
    elif player.ammo[AM_CLIP] != 0:
        player.pendingweapon = WP_PISTOL
    elif player.weaponowned[WP_CHAINSAW]:
        player.pendingweapon = WP_CHAINSAW
    elif player.weaponowned[WP_MISSILE] and player.ammo[AM_MISL] != 0:
        player.pendingweapon = WP_MISSILE
    elif player.weaponowned[WP_BFG] and player.ammo[AM_CELL] > 40 and not shareware:
        player.pendingweapon = WP_BFG
    else:
        player.pendingweapon = WP_FIST


def _weapon_ready_bob(player: Player, game) -> None:
    """A_WeaponReady bob into psp->sy (Harbour: finesine[(angle & halfmask)])."""
    from .tables import finesine

    lt = int(getattr(game, "leveltime", 0) or 0)
    angle = (128 * lt) & FINEMASK
    angle &= FINEANGLES // 2 - 1
    player.psprite_sy = WEAPONTOP + fixed_mul(player.bob or 0, finesine[angle])


def _weapon_think(player: Player, game) -> None:
    if player.playerstate == PST_DEAD or player.health <= 0:
        _lower_weapon(player, game)
        return
    cmd = player.cmd
    firing = bool(cmd.buttons & BT_ATTACK)
    ammo_type = WEAPON_AMMO.get(player.readyweapon)
    need = _ammo_needed(player.readyweapon)
    can_fire = ammo_type is None or player.ammo[ammo_type] >= need
    if player.flash_tics > 0:
        player.flash_tics -= 1
        if player.flash_tics <= 0:
            player.psprite_flash = ""
            player.extralight = 0
    if player.psprite_state == "fire":
        player.psprite_state = "atk"
    if player.psprite_state == "atk":
        if firing:
            player.attackdown = True
        if player.psprite_tics > 0:
            player.psprite_tics -= 1
        if player.psprite_tics > 0:
            return
        player.psprite_step += 1
        _enter_atk_step(player, game, ammo_type, firing, can_fire)
        return
    # A_Raise ignores pending; only A_WeaponReady starts the lower (PHP/vanilla).
    if player.psprite_state == "up":
        _raise_weapon(player, game)
        return
    if player.pendingweapon != WP_NOCHANGE or player.psprite_state == "down":
        _lower_weapon(player, game)
        return
    if firing and not can_fire:
        _select_fallback(player, game)
        _lower_weapon(player, game)
        return
    if firing and can_fire:
        ready_gate = (not player.attackdown) or player.readyweapon not in (WP_MISSILE, WP_BFG)
        if ready_gate:
            player.psprite_state = "atk"
            player.psprite_step = 0
            # Harbour P_FireWeapon keeps psp->sy (bobbed); do not snap to WEAPONTOP.
            player.attackdown = True
            _enter_atk_step(player, game, ammo_type, firing, can_fire)
            return
    if player.psprite_state != "ready":
        _start_ready(player, game)
        _weapon_ready_bob(player, game)
        if not firing:
            player.attackdown = False
            player.refire = 0
        return
    _tick_ready(player, game)
    # A_WeaponReady: bob into psp->sy so A_Lower starts from WEAPONTOP+bob.
    _weapon_ready_bob(player, game)
    if not firing:
        player.attackdown = False
        player.refire = 0


def _lower_weapon(player: Player, game) -> None:
    """A_Lower: drop the current gun, then P_BringUpWeapon."""
    player.psprite_state = "down"
    if not player.psprite_body:
        player.psprite_body = WEAPON_PATCH.get(player.readyweapon, "PISGA0")
    player.psprite_sy += LOWERSPEED
    if player.psprite_sy < WEAPONBOTTOM:
        return
    player.psprite_sy = WEAPONBOTTOM
    if player.playerstate == PST_DEAD or player.health <= 0:
        return
    if player.pendingweapon != WP_NOCHANGE:
        player.readyweapon = player.pendingweapon
        player.pendingweapon = WP_NOCHANGE
    if player.readyweapon == WP_CHAINSAW:
        game.start_sound("sawup")
    player.psprite_state = "up"
    player.psprite_body = WEAPON_PATCH.get(player.readyweapon, "PISGA0")
    # A_Lower calls P_BringUpWeapon, which runs A_Raise on the same tic.
    _raise_weapon(player, game)


def _raise_weapon(player: Player, game) -> None:
    """A_Raise: slide up from WEAPONBOTTOM to WEAPONTOP; then A_WeaponReady same tic."""
    player.psprite_sy -= RAISESPEED
    if not player.psprite_body:
        player.psprite_body = WEAPON_PATCH.get(player.readyweapon, "PISGA0")
    if player.psprite_sy > WEAPONTOP:
        return
    player.psprite_sy = WEAPONTOP
    # Harbour A_Raise → P_SetPsprite(readystate) → A_WeaponReady immediately.
    if player.pendingweapon != WP_NOCHANGE or player.health <= 0:
        _lower_weapon(player, game)
        return
    _start_ready(player, game)
    cmd = player.cmd
    firing = bool(cmd.buttons & BT_ATTACK)
    ammo_type = WEAPON_AMMO.get(player.readyweapon)
    can_fire = ammo_type is None or player.ammo[ammo_type] >= _ammo_needed(player.readyweapon)
    if firing and not can_fire:
        _select_fallback(player, game)
        _lower_weapon(player, game)
        return
    if firing and can_fire and (
        (not player.attackdown) or player.readyweapon not in (WP_MISSILE, WP_BFG)
    ):
        player.psprite_state = "atk"
        player.psprite_step = 0
        player.attackdown = True
        _enter_atk_step(player, game, ammo_type, firing, can_fire)
        return
    _weapon_ready_bob(player, game)
    if not firing:
        player.attackdown = False
        player.refire = 0


def _start_ready(player: Player, game) -> None:
    player.psprite_state = "ready"
    player.psprite_step = 0
    seq = WEAPON_READY.get(player.readyweapon)
    if not seq:
        player.psprite_body = WEAPON_PATCH.get(player.readyweapon, "PISGA0")
        player.psprite_tics = 0
        return
    body, tics, sfx = seq[0]
    player.psprite_body = body
    player.psprite_tics = tics
    if sfx:
        game.start_sound(sfx)


def _tick_ready(player: Player, game) -> None:
    seq = WEAPON_READY.get(player.readyweapon)
    if not seq:
        player.psprite_body = WEAPON_PATCH.get(player.readyweapon, "PISGA0")
        return
    if player.psprite_tics > 0:
        player.psprite_tics -= 1
        if player.psprite_tics > 0:
            return
        player.psprite_step = (player.psprite_step + 1) % len(seq)
    body, tics, sfx = seq[player.psprite_step]
    player.psprite_body = body
    player.psprite_tics = tics
    if sfx:
        game.start_sound(sfx)


def _enter_atk_step(player: Player, game, ammo_type, firing: bool, can_fire: bool) -> None:
    from .enemy import noise_alert

    seq = WEAPON_ATK.get(player.readyweapon) or WEAPON_ATK[WP_PISTOL]
    for _guard in range(64):
        if player.psprite_step >= len(seq):
            if player.pendingweapon != WP_NOCHANGE:
                _lower_weapon(player, game)
                return
            if firing and not can_fire:
                # Harbour A_ReFire / end-of-atk: P_CheckAmmo preference order.
                _select_fallback(player, game)
                _lower_weapon(player, game)
                return
            if firing and can_fire and player.pendingweapon == WP_NOCHANGE:
                player.psprite_step = 0
                continue
            _start_ready(player, game)
            if not firing:
                player.attackdown = False
                player.refire = 0
            return
        if player.psprite_step == 0 and player.mo is not None:
            noise_alert(game.world, player.mo, game)
        step = seq[player.psprite_step]
        body, tics, do_fire, flash, flash_tics, light = step[:6]
        action = step[6] if len(step) > 6 else None
        # A_CheckReload: P_CheckAmmo mid-anim (SSG); lower if empty.
        if action == "checkreload":
            if not can_fire:
                _select_fallback(player, game)
                _lower_weapon(player, game)
                return
        # A_ReFire (and A_CloseShotgun2→A_ReFire): bump refire; held fire skips remaining tics.
        elif action:
            if firing and player.pendingweapon == WP_NOCHANGE and player.health > 0:
                player.refire += 1
                if can_fire:
                    player.psprite_step = 0
                    continue
                _select_fallback(player, game)
                _lower_weapon(player, game)
                return
            player.refire = 0
            if not can_fire:
                _select_fallback(player, game)
                _lower_weapon(player, game)
                return
        player.psprite_body = body
        player.psprite_tics = tics
        if flash_tics:
            player.psprite_flash = flash
            player.flash_tics = flash_tics
        if light:
            player.extralight = light
        if do_fire:
            _do_shot(player, game, ammo_type)
        if tics > 0:
            return
        player.psprite_step += 1


def _ammo_needed(weapon: int) -> int:
    """P_CheckAmmo / DecreaseAmmo: BFG cells, SSG 2 shells, else 1."""
    if weapon == WP_BFG:
        from .deh import deh

        return deh.bfg_cells_per_shot
    if weapon == WP_SUPERSHOTGUN:
        return 2
    return 1


def _gun_shot(player: Player, game, accurate: bool, slope: int | None = None) -> bool:
    """P_GunShot — re-reads global bulletslope each call (InterceptsOverrun)."""
    from .enemy import p_random

    mo = player.mo
    damage = 5 * ((p_random() % 3) + 1)
    angle = mo.angle
    if not accurate:
        angle = as_u32(angle + (p_random() - p_random()) * 262144)
    # Vanilla reads the global each pellet; PathTraverse may clobber it.
    aim = get_bulletslope() if slope is None else slope
    return line_attack(game.world, mo, damage, game, MISSILERANGE, angle, aim)


def _do_shot(player: Player, game, ammo_type) -> None:
    need = _ammo_needed(player.readyweapon)
    if ammo_type is not None:
        if player.ammo[ammo_type] < need:
            return
        player.ammo[ammo_type] -= need
    from .enemy import noise_alert, p_random, spawn_player_missile

    mo = player.mo
    weapon = player.readyweapon
    hit = False
    if mo and weapon in (WP_MISSILE, WP_PLASMA, WP_BFG):
        if weapon == WP_PLASMA:
            player.psprite_flash = "PLSFB0" if (p_random() & 1) else "PLSFA0"
            player.flash_tics = 4
        if weapon == WP_MISSILE:
            spawn_player_missile(game.world, mo, "MISL", 20 * FRACUNIT, 20, "rocket", game)
            game.start_sound("rlaunc")
        elif weapon == WP_PLASMA:
            spawn_player_missile(game.world, mo, "PLSS", 25 * FRACUNIT, 5, "plasma", game)
            game.start_sound("plasma")
        else:
            spawn_player_missile(game.world, mo, "BFS1", 25 * FRACUNIT, 100, "bfg", game)
            game.start_sound("bfg")
        # refire is only bumped in A_ReFire, not here.
        player.attackdown = True
        noise_alert(game.world, mo, game)
        return
    if mo and weapon == WP_FIST:
        damage = ((p_random() % 10) + 1) * 2
        if player.powers[PW_STRENGTH]:
            damage *= 10
        angle = as_u32(mo.angle + (p_random() - p_random()) * 262144)
        hit = line_attack(game.world, mo, damage, game, MELEERANGE, angle)
        if hit:
            game.start_sound("punch")
    elif mo and weapon == WP_CHAINSAW:
        damage = 2 * ((p_random() % 10) + 1)
        angle = as_u32(mo.angle + (p_random() - p_random()) * 262144)
        hit = line_attack(game.world, mo, damage, game, MELEERANGE + 1, angle)
        game.start_sound("sawhit" if hit else "sawful")
    elif mo and weapon == WP_SHOTGUN:
        # A_FireShotgun: one P_BulletSlope, then 7× P_GunShot reading global.
        game.start_sound("shotgn")
        bullet_slope(game.world, mo)
        for _ in range(7):
            if _gun_shot(player, game, False):
                hit = True
    elif mo and weapon == WP_SUPERSHOTGUN:
        game.start_sound("dshtgn")
        bullet_slope(game.world, mo)
        for _ in range(20):
            damage = 5 * ((p_random() % 3) + 1)
            angle = as_u32(mo.angle + (p_random() - p_random()) * 524288)
            pellet = get_bulletslope() + (p_random() - p_random()) * 32
            if line_attack(game.world, mo, damage, game, MISSILERANGE, angle, pellet):
                hit = True
    elif mo:
        game.start_sound("pistol")
        bullet_slope(game.world, mo)
        _gun_shot(player, game, player.refire == 0)
    # refire is only bumped in A_ReFire, not here (P_FireWeapon / A_FirePistol).
    player.attackdown = True
    if mo:
        noise_alert(game.world, mo, game)


def weapon_patch(player: Player) -> str:
    if player.psprite_body:
        return player.psprite_body
    if player.psprite_state in ("atk", "fire"):
        return WEAPON_FIRE_BODY.get(player.readyweapon, WEAPON_PATCH.get(player.readyweapon, "PISGA0"))
    return WEAPON_PATCH.get(player.readyweapon, "PISGA0")
