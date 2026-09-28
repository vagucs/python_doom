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

from .collision import line_attack, point_in_subsector, slide_move, use_lines
from .compat import as_u32, fixed_mul
from .defs import (
    AM_CELL,
    AM_CLIP,
    AM_MISL,
    AM_SHELL,
    ANG90,
    BT_ATTACK,
    BT_CHANGE,
    BT_USE,
    BT_WEAPONMASK,
    BT_WEAPONSHIFT,
    FINEMASK,
    FRACUNIT,
    FRICTION,
    GRAVITY,
    MAXBOB,
    MELEERANGE,
    MISSILERANGE,
    MF_DROPOFF,
    MF_NOCLIP,
    MF_PICKUP,
    MF_SHOOTABLE,
    MF_SOLID,
    PLAYER_HEIGHT,
    PLAYER_RADIUS,
    PST_DEAD,
    PST_LIVE,
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


@dataclass
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
    target: object | None = None
    movedir: int = 8
    movecount: int = 0
    ai_state: str = ""
    frame: int = 0
    tics: int = 0
    chase_tics: int = 0
    just_attacked: bool = False
    damage: int = 0

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
    extralight: int = 0
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

    def set_message(self, text: str) -> None:
        self.message = text
        self.message_tics = 4 * TICRATE


def spawn_player(world, start, cheats: int = 0) -> Player:
    sub = point_in_subsector(world, start.x * FRACUNIT, start.y * FRACUNIT)
    mo = Mobj(
        x=start.x * FRACUNIT,
        y=start.y * FRACUNIT,
        z=sub.sector.floorheight,
        angle=as_u32((start.angle // 45) * 0x20000000),
        floorz=sub.sector.floorheight,
        ceilingz=sub.sector.ceilingheight,
    )
    player = Player(mo=mo, cheats=cheats)
    mo.player = player
    if cheats & 1:
        mo.flags |= MF_NOCLIP
    player.viewz = mo.z + VIEWHEIGHT
    world.mobjs.append(mo)
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
    if mo.momx == 0 and mo.momy == 0:
        return
    slide_move(world, mo, mo.momx, mo.momy, game)
    if mo.player and abs(mo.momx) < STOPSPEED and abs(mo.momy) < STOPSPEED:
        cmd = mo.player.cmd
        if cmd.forwardmove == 0 and cmd.sidemove == 0:
            mo.momx = mo.momy = 0
            return
    mo.momx = fixed_mul(mo.momx, FRICTION)
    mo.momy = fixed_mul(mo.momy, FRICTION)


def z_movement(mo: Mobj) -> None:
    mo.z += mo.momz
    if mo.z <= mo.floorz:
        mo.z = mo.floorz
        mo.momz = 0
    else:
        mo.momz -= GRAVITY
    if mo.z + mo.height > mo.ceilingz:
        mo.z = mo.ceilingz - mo.height
        mo.momz = 0


def _special_sector(world, player: Player, game, leveltime: int) -> None:
    """P_PlayerInSpecialSector: secrets and damaging floors."""
    mo = player.mo
    if mo is None:
        return
    sector = point_in_subsector(world, mo.x, mo.y).sector
    if mo.z != sector.floorheight or not sector.special:
        return
    spec = sector.special
    if spec == 9:
        player.secretcount += 1
        sector.special = 0
        return
    if spec in (5, 7, 4, 16, 11):
        if (leveltime & 0x1F) != 0:
            return
        if spec == 5:
            game.damage_mobj(mo, None, 10)
        elif spec == 7:
            game.damage_mobj(mo, None, 5)
        elif spec in (4, 16):
            game.damage_mobj(mo, None, 20)
        elif spec == 11:
            game.damage_mobj(mo, None, 20)
            if player.health <= 10 and game.specials:
                game.specials.exit_requested = True


def player_think(world, player: Player, game, leveltime: int) -> None:
    mo = player.mo
    assert mo is not None
    cmd = player.cmd
    if player.playerstate == PST_DEAD:
        if player.viewheight > 6 * FRACUNIT:
            player.viewheight -= FRACUNIT
        calc_height(player, leveltime)
        if cmd.buttons & BT_USE:
            player.playerstate = PST_LIVE
            player.health = 100
            mo.health = 100
            mo.alive = True
            mo.flags |= MF_SHOOTABLE | MF_SOLID
        return
    mo.angle = as_u32(mo.angle + (cmd.angleturn << 16))
    onground = mo.z <= mo.floorz
    if cmd.forwardmove and onground:
        thrust(mo, mo.angle, cmd.forwardmove * 2048)
    if cmd.sidemove and onground:
        thrust(mo, as_u32(mo.angle - ANG90), cmd.sidemove * 2048)
    xy_movement(world, mo, game)
    z_movement(mo)
    calc_height(player, leveltime)
    _special_sector(world, player, game, leveltime)
    if cmd.buttons & BT_USE:
        if not player.usedown:
            use_lines(world, player, game)
            player.usedown = True
    else:
        player.usedown = False
    if cmd.buttons & BT_CHANGE:
        neww = (cmd.buttons & BT_WEAPONMASK) >> BT_WEAPONSHIFT
        if 0 <= neww <= WP_SUPERSHOTGUN and player.weaponowned[neww] and neww != player.readyweapon:
            player.pendingweapon = neww
    _weapon_think(player, game)
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

# info.prg attack states: (body, tics, do_fire, flash, flash_tics, light)
# A_ReFire is the end of the list (restart while held).
WEAPON_ATK = {
    WP_FIST: (
        ("PUNGB0", 4, False, "", 0, 0),
        ("PUNGC0", 4, True, "", 0, 0),
        ("PUNGD0", 5, False, "", 0, 0),
        ("PUNGC0", 4, False, "", 0, 0),
        ("PUNGB0", 5, False, "", 0, 0),
    ),
    WP_PISTOL: (
        ("PISGA0", 4, False, "", 0, 0),
        ("PISGB0", 6, True, "PISFA0", 7, 1),
        ("PISGC0", 4, False, "", 0, 0),
        ("PISGB0", 5, False, "", 0, 0),
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
        ("SHTGA0", 7, False, "", 0, 0),
    ),
    WP_CHAINGUN: (
        ("CHGGA0", 4, True, "CHGFA0", 5, 1),
        ("CHGGB0", 4, True, "CHGFB0", 5, 2),
    ),
    WP_MISSILE: (
        ("MISGB0", 8, False, "MISFA0", 15, 1),
        ("MISGB0", 12, True, "", 0, 2),
    ),
    WP_PLASMA: (
        ("PLSGA0", 3, True, "PLSFA0", 4, 1),
        ("PLSGB0", 20, False, "", 0, 0),
    ),
    WP_BFG: (
        ("BFGGA0", 20, False, "", 0, 0),
        ("BFGGB0", 10, False, "BFGFA0", 17, 1),
        ("BFGGB0", 10, True, "", 0, 2),
        ("BFGGB0", 20, False, "", 0, 0),
    ),
    WP_CHAINSAW: (
        ("SAWGA0", 4, True, "", 0, 0),
        ("SAWGB0", 4, True, "", 0, 0),
    ),
    WP_SUPERSHOTGUN: (
        ("SHT2A0", 3, False, "", 0, 0),
        ("SHT2A0", 7, True, "SHT2I0", 9, 1),
        ("SHT2B0", 7, False, "", 0, 0),
        ("SHT2C0", 7, False, "", 0, 0),
        ("SHT2D0", 7, False, "", 0, 0),
        ("SHT2E0", 7, False, "", 0, 0),
        ("SHT2F0", 7, False, "", 0, 0),
        ("SHT2G0", 6, False, "", 0, 0),
        ("SHT2H0", 6, False, "", 0, 0),
        ("SHT2A0", 5, False, "", 0, 0),
    ),
}

# Idle ready cycle (info.prg A_WeaponReady). Chainsaw breathes C↔D; others stay on A.
WEAPON_READY = {
    WP_CHAINSAW: (("SAWGC0", 4, "sawidl"), ("SAWGD0", 4, "")),
}


def _weapon_think(player: Player, game) -> None:
    cmd = player.cmd
    firing = bool(cmd.buttons & BT_ATTACK)
    ammo_type = WEAPON_AMMO.get(player.readyweapon)
    can_fire = True
    if ammo_type is not None and player.ammo[ammo_type] <= 0:
        can_fire = player.readyweapon in (WP_FIST, WP_CHAINSAW)
        if not can_fire:
            for w in (WP_PISTOL, WP_SHOTGUN, WP_CHAINGUN, WP_MISSILE, WP_PLASMA, WP_BFG, WP_FIST):
                at = WEAPON_AMMO.get(w)
                if player.weaponowned[w] and (at is None or player.ammo[at] > 0):
                    player.pendingweapon = w
                    break
            ammo_type = WEAPON_AMMO.get(player.readyweapon)
            can_fire = ammo_type is None or player.ammo[ammo_type] > 0
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
    if player.pendingweapon != WP_NOCHANGE or player.psprite_state == "down":
        _lower_weapon(player, game)
        return
    if player.psprite_state == "up":
        _raise_weapon(player, game)
        return
    if firing and can_fire:
        ready_gate = (not player.attackdown) or player.readyweapon not in (WP_MISSILE, WP_BFG)
        if ready_gate:
            player.psprite_state = "atk"
            player.psprite_step = 0
            player.psprite_sy = WEAPONTOP
            player.attackdown = True
            _enter_atk_step(player, game, ammo_type, firing, can_fire)
            return
    if player.psprite_state != "ready":
        _start_ready(player, game)
        return
    _tick_ready(player, game)
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
    if player.pendingweapon != WP_NOCHANGE:
        player.readyweapon = player.pendingweapon
        player.pendingweapon = WP_NOCHANGE
    if player.readyweapon == WP_CHAINSAW:
        game.start_sound("sawup")
    player.psprite_state = "up"
    player.psprite_body = WEAPON_PATCH.get(player.readyweapon, "PISGA0")


def _raise_weapon(player: Player, game) -> None:
    """A_Raise: slide up from WEAPONBOTTOM to WEAPONTOP."""
    player.psprite_sy -= RAISESPEED
    if not player.psprite_body:
        player.psprite_body = WEAPON_PATCH.get(player.readyweapon, "PISGA0")
    if player.psprite_sy > WEAPONTOP:
        return
    player.psprite_sy = WEAPONTOP
    _start_ready(player, game)


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
    seq = WEAPON_ATK.get(player.readyweapon) or WEAPON_ATK[WP_PISTOL]
    while True:
        if player.psprite_step >= len(seq):
            # A_ReFire: restart the attack if still held, else drop to ready.
            if firing and can_fire and player.pendingweapon == WP_NOCHANGE:
                player.psprite_step = 0
                continue
            _start_ready(player, game)
            if not firing:
                player.attackdown = False
                player.refire = 0
            return
        body, tics, do_fire, flash, flash_tics, light = seq[player.psprite_step]
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


def _do_shot(player: Player, game, ammo_type) -> None:
    if ammo_type is not None:
        if player.ammo[ammo_type] <= 0:
            return
        player.ammo[ammo_type] -= 1
    dmg, rng, sfx = WEAPON_SHOT.get(player.readyweapon, (5, MISSILERANGE, "pistol"))
    hit = False
    if player.mo:
        pellets = 7 if player.readyweapon == WP_SHOTGUN else 20 if player.readyweapon == WP_SUPERSHOTGUN else 1
        if player.readyweapon == WP_CHAINSAW:
            shot = 2 * ((game.leveltime % 10) + 1)
            rng = MELEERANGE + 1
            pellets = 1
        else:
            shot = dmg * ((game.leveltime & 7) + 1)
        for _ in range(pellets):
            if line_attack(game.world, player.mo, shot, game, rng):
                hit = True
    if player.readyweapon == WP_CHAINSAW:
        game.start_sound("sawhit" if hit else "sawful")
    elif player.readyweapon == WP_FIST:
        if hit:
            game.start_sound("punch")
    elif sfx:
        game.start_sound(sfx)
    player.refire += 1
    player.attackdown = True
    from .enemy import noise_alert

    noise_alert(game.world, player.mo, game)


def weapon_patch(player: Player) -> str:
    if player.psprite_body:
        return player.psprite_body
    if player.psprite_state in ("atk", "fire"):
        return WEAPON_FIRE_BODY.get(player.readyweapon, WEAPON_PATCH.get(player.readyweapon, "PISGA0"))
    return WEAPON_PATCH.get(player.readyweapon, "PISGA0")
