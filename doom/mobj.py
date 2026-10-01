"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Map objects: pickups, decorations, enemies (info / p_mobj / p_inter).
"""

from __future__ import annotations

from dataclasses import dataclass

from .collision import point_in_subsector
from .compat import as_u32
from .defs import (
    AM_CELL,
    AM_CLIP,
    AM_MISL,
    AM_SHELL,
    FRACUNIT,
    IT_BLUECARD,
    IT_BLUESKULL,
    IT_REDCARD,
    IT_REDSKULL,
    IT_YELLOWCARD,
    IT_YELLOWSKULL,
    MAXARMOR,
    MAXHEALTH,
    MF_AMBUSH,
    MF_COUNTITEM,
    MF_COUNTKILL,
    MF_FLOAT,
    MF_NOBLOCKMAP,
    MF_NOGRAVITY,
    MF_SPAWNCEILING,
    MF_NOSECTOR,
    MF_PICKUP,
    MF_SHADOW,
    MF_SHOOTABLE,
    MF_SOLID,
    MF_SPECIAL,
    PW_ALLMAP,
    PW_INFRARED,
    PW_INVISIBILITY,
    PW_INVULNERABILITY,
    PW_IRONFEET,
    SK_BABY,
    SK_EASY,
    SK_HARD,
    SK_NIGHTMARE,
    MTF_AMBUSH,
    WP_BFG,
    WP_CHAINGUN,
    WP_CHAINSAW,
    WP_FIST,
    WP_MISSILE,
    WP_PLASMA,
    WP_SHOTGUN,
    WP_SUPERSHOTGUN,
)
from .player import CLIPAMMO, Mobj, give_power

# type -> (sprite, radius_mapunits, height_mapunits, health, flags, kind, extra)
# kind: enemy, item, deco, weapon, ammo, key, health, armor

INFO = {
    3004: ("POSSA1", 20, 56, 20, MF_SOLID | MF_SHOOTABLE, "enemy", "posit1"),
    9: ("SPOSA1", 20, 56, 30, MF_SOLID | MF_SHOOTABLE, "enemy", "posit1"),
    3001: ("TROOA1", 20, 56, 60, MF_SOLID | MF_SHOOTABLE, "enemy", "bgsit1"),
    3002: ("SARGA1", 30, 56, 150, MF_SOLID | MF_SHOOTABLE, "enemy", "sgtsit"),
    58: ("SARGA1", 30, 56, 150, MF_SOLID | MF_SHOOTABLE | MF_SHADOW, "enemy", "sgtsit"),
    65: ("CPOSA1", 20, 56, 70, MF_SOLID | MF_SHOOTABLE, "enemy", "posit2"),
    3003: ("BOSSA1", 24, 64, 1000, MF_SOLID | MF_SHOOTABLE, "enemy", "brssit"),
    3005: ("HEADA1", 31, 56, 400, MF_SOLID | MF_SHOOTABLE | MF_FLOAT | MF_NOGRAVITY, "enemy", "cacsit"),
    3006: ("SKULA1", 16, 56, 100, MF_SOLID | MF_SHOOTABLE | MF_FLOAT | MF_NOGRAVITY, "enemy", "sklatk"),
    16: ("CYBRA1", 40, 110, 4000, MF_SOLID | MF_SHOOTABLE, "enemy", "cybsit"),
    7: ("SPIDA1", 128, 100, 3000, MF_SOLID | MF_SHOOTABLE, "enemy", "spisit"),
    68: ("BSPIA1", 64, 64, 500, MF_SOLID | MF_SHOOTABLE, "enemy", "bspsit"),
    69: ("BOS2A1", 24, 64, 500, MF_SOLID | MF_SHOOTABLE, "enemy", "kntsit"),
    64: ("VILEA1", 20, 56, 700, MF_SOLID | MF_SHOOTABLE, "enemy", "vilsit"),
    66: ("SKELA1", 20, 56, 500, MF_SOLID | MF_SHOOTABLE, "enemy", "skesit"),
    67: ("FATTA1", 48, 64, 600, MF_SOLID | MF_SHOOTABLE, "enemy", "mansit"),
    71: ("PAINA1", 31, 56, 400, MF_SOLID | MF_SHOOTABLE | MF_FLOAT | MF_NOGRAVITY, "enemy", "pesit"),
    84: ("SSWVA1", 20, 56, 50, MF_SOLID | MF_SHOOTABLE, "enemy", "posit1"),
    72: ("KEENA1", 16, 72, 100, MF_SOLID | MF_SHOOTABLE | MF_NOGRAVITY, "enemy", "keenpn"),
    87: ("", 20, 32, 1000, MF_NOBLOCKMAP | MF_NOSECTOR, "bosstarget", None),
    88: ("BBRNA1", 16, 16, 250, MF_SOLID | MF_SHOOTABLE, "enemy", "bossit"),
    89: ("", 20, 32, 1000, MF_NOBLOCKMAP | MF_NOSECTOR, "braineye", None),
    2035: ("BAR1A0", 10, 42, 20, MF_SOLID | MF_SHOOTABLE, "enemy", None),
    2011: ("STIMA0", 20, 16, 0, MF_SPECIAL, "health", 10),
    2012: ("MEDIA0", 20, 16, 0, MF_SPECIAL, "health", 25),
    2014: ("BON1A0", 20, 16, 0, MF_SPECIAL, "bonus_h", 1),
    2015: ("BON2A0", 20, 16, 0, MF_SPECIAL, "bonus_a", 1),
    2018: ("ARM1A0", 20, 16, 0, MF_SPECIAL, "armor", 1),
    2019: ("ARM2A0", 20, 16, 0, MF_SPECIAL, "armor", 2),
    83: ("MEGAA0", 20, 16, 0, MF_SPECIAL, "mega", 0),
    2013: ("SOULA0", 20, 16, 0, MF_SPECIAL, "soul", 0),
    2022: ("PINVA0", 20, 16, 0, MF_SPECIAL, "item", "Invulnerability"),
    2023: ("PSTRA0", 20, 16, 0, MF_SPECIAL, "berserk", 0),
    2024: ("PINSA0", 20, 16, 0, MF_SPECIAL, "item", "Partial invisibility"),
    2025: ("SUITA0", 20, 16, 0, MF_SPECIAL, "item", "Radiation shielding"),
    2026: ("PMAPA0", 20, 16, 0, MF_SPECIAL, "item", "Computer area map"),
    2045: ("PVISA0", 20, 16, 0, MF_SPECIAL, "item", "Light amplification visor"),
    5: ("BKEYA0", 20, 16, 0, MF_SPECIAL, "key", IT_BLUECARD),
    6: ("YKEYA0", 20, 16, 0, MF_SPECIAL, "key", IT_YELLOWCARD),
    13: ("RKEYA0", 20, 16, 0, MF_SPECIAL, "key", IT_REDCARD),
    40: ("BSKUA0", 20, 16, 0, MF_SPECIAL, "key", IT_BLUESKULL),
    39: ("YSKUA0", 20, 16, 0, MF_SPECIAL, "key", IT_YELLOWSKULL),
    38: ("RSKUA0", 20, 16, 0, MF_SPECIAL, "key", IT_REDSKULL),
    2001: ("SHOTA0", 20, 16, 0, MF_SPECIAL, "weapon", WP_SHOTGUN),
    82: ("SGN2A0", 20, 16, 0, MF_SPECIAL, "weapon", WP_SUPERSHOTGUN),
    2002: ("MGUNA0", 20, 16, 0, MF_SPECIAL, "weapon", WP_CHAINGUN),
    2003: ("LAUNA0", 20, 16, 0, MF_SPECIAL, "weapon", WP_MISSILE),
    2004: ("PLASA0", 20, 16, 0, MF_SPECIAL, "weapon", WP_PLASMA),
    2005: ("CSAWA0", 20, 16, 0, MF_SPECIAL, "weapon", WP_CHAINSAW),
    2006: ("BFUGA0", 20, 16, 0, MF_SPECIAL, "weapon", WP_BFG),
    2007: ("CLIPA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_CLIP, 1)),
    2048: ("AMMOA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_CLIP, 5)),
    2008: ("SHELA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_SHELL, 1)),
    2049: ("SBOXA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_SHELL, 5)),
    2047: ("CELLA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_CELL, 1)),
    17: ("CELPA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_CELL, 5)),
    2010: ("ROCKA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_MISL, 1)),
    2046: ("BROKA0", 20, 16, 0, MF_SPECIAL, "ammo", (AM_MISL, 5)),
    8: ("BPAKA0", 20, 16, 0, MF_SPECIAL, "backpack", 0),
    2028: ("COLUA0", 16, 16, 0, MF_SOLID, "deco", None),
    85: ("TLMPA0", 16, 16, 0, MF_SOLID, "deco", None),
    86: ("TLP2A0", 16, 16, 0, MF_SOLID, "deco", None),
    48: ("ELECA0", 16, 16, 0, MF_SOLID, "deco", None),
    30: ("COL1A0", 16, 16, 0, MF_SOLID, "deco", None),
    31: ("COL2A0", 16, 16, 0, MF_SOLID, "deco", None),
    32: ("COL3A0", 16, 16, 0, MF_SOLID, "deco", None),
    33: ("COL4A0", 16, 16, 0, MF_SOLID, "deco", None),
    35: ("CANDA0", 16, 16, 0, 0, "deco", None),
    37: ("CBRAA0", 16, 16, 0, MF_SOLID, "deco", None),
    41: ("CEYEA0", 16, 16, 0, MF_SOLID, "deco", None),
    42: ("FSKUA0", 16, 16, 0, MF_SOLID, "deco", None),
    43: ("TRE1A0", 16, 16, 0, MF_SOLID, "deco", None),
    47: ("SMITA0", 16, 16, 0, MF_SOLID, "deco", None),
    54: ("TRE2A0", 32, 16, 0, MF_SOLID, "deco", None),
    2028: ("COLUA0", 16, 16, 0, MF_SOLID, "deco", None),
    10: ("PLAYW0", 16, 16, 0, 0, "deco", None),
    12: ("PLAYW0", 16, 16, 0, 0, "deco", None),
    15: ("PLAYN0", 16, 16, 0, 0, "deco", None),
    24: ("POL5A0", 16, 16, 0, 0, "deco", None),
    25: ("POL1A0", 16, 16, 0, MF_SOLID, "deco", None),
    26: ("POL6A0", 16, 16, 0, MF_SOLID, "deco", None),
    27: ("POL4A0", 16, 16, 0, MF_SOLID, "deco", None),
    28: ("POL2A0", 16, 16, 0, MF_SOLID, "deco", None),
    34: ("CANDA0", 16, 16, 0, 0, "deco", None),
    36: ("CBRAA0", 16, 16, 0, MF_SOLID, "deco", None),
    46: ("TREDA0", 16, 16, 0, 0, "deco", None),
    55: ("GOR1A0", 16, 16, 0, 0, "deco", None),
    56: ("GOR2A0", 16, 16, 0, 0, "deco", None),
    57: ("GOR3A0", 16, 16, 0, 0, "deco", None),
    59: ("GOR5A0", 16, 16, 0, 0, "deco", None),
}

WEAPON_NAMES = {
    WP_SHOTGUN: "You got the shotgun!",
    WP_SUPERSHOTGUN: "You got the super shotgun!",
    WP_CHAINGUN: "You got the chaingun!",
    WP_MISSILE: "You got the rocket launcher!",
    WP_PLASMA: "You got the plasma gun!",
    WP_BFG: "You got the BFG9000!",
    WP_CHAINSAW: "A chainsaw!  Find some meat!",
}

KEY_NAMES = {
    IT_BLUECARD: "You picked up a blue keycard.",
    IT_YELLOWCARD: "You picked up a yellow keycard.",
    IT_REDCARD: "You picked up a red keycard.",
    IT_BLUESKULL: "You picked up a blue skull key.",
    IT_YELLOWSKULL: "You picked up a yellow skull key.",
    IT_REDSKULL: "You picked up a red skull key.",
}


def _sprite_and_frame(name: str) -> tuple[str, int]:
    """POSSA1 -> (POSS, 0); PLAYW0 -> (PLAY, 22)."""
    n = (name or "").upper()
    spr = n[:4]
    if len(n) >= 5 and "A" <= n[4] <= "]":
        return spr, ord(n[4]) - ord("A")
    return spr, 0


def skill_bit(skill: int) -> int:
    if skill <= SK_EASY:
        return 1
    if skill == SK_NIGHTMARE or skill >= SK_HARD:
        return 4
    return 2


def spawn_map_things(world, skill: int, game=None) -> tuple[int, int]:
    from .info import MI_FLAGS, MT_SKULL, mobj_type_for_doomednum
    from .thinker import ONCEILINGZ, ONFLOORZ, spawn_mobj

    bit = skill_bit(skill)
    totalkills = 0
    totalitems = 0
    nomonsters = bool(game and getattr(game, "nomonsters", False))
    for mt in world.things:
        if mt.type == 11:
            continue
        if mt.type in (1, 2, 3, 4):
            if mt.type == 1 and game is not None and game.player is None:
                from .player import spawn_player

                game.player = spawn_player(world, mt)
            continue
        if not (mt.options & bit):
            continue
        if mt.options & 16:
            continue
        typ = mobj_type_for_doomednum(mt.type)
        if typ < 0:
            continue
        from .info import MOBJINFO

        flags = MOBJINFO[typ][MI_FLAGS]
        if nomonsters and ((flags & MF_COUNTKILL) or typ == MT_SKULL):
            continue
        z = ONCEILINGZ if flags & MF_SPAWNCEILING else ONFLOORZ
        mo = spawn_mobj(world, mt.x * FRACUNIT, mt.y * FRACUNIT, z, typ, game)
        if mo.tics > 0:
            from .enemy import p_random

            mo.tics = 1 + (p_random() % mo.tics)
        mo.angle = as_u32((mt.angle // 45) * 0x20000000)
        mo.spawnpoint = mt
        if mt.options & MTF_AMBUSH:
            mo.flags |= MF_AMBUSH
        pickup = INFO.get(mt.type)
        if pickup:
            mo.info = (pickup[5], pickup[6])
        if mo.flags & MF_COUNTKILL:
            totalkills += 1
        if mo.flags & MF_COUNTITEM:
            totalitems += 1
    return totalkills, totalitems


def give_ammo(player, ammo: int, num: int) -> bool:
    if player.ammo[ammo] >= player.maxammo[ammo]:
        return False
    player.ammo[ammo] = min(player.maxammo[ammo], player.ammo[ammo] + CLIPAMMO[ammo] * num)
    return True


def touch_special(game, special: Mobj, toucher: Mobj) -> None:
    player = toucher.player
    if player is None or not special.alive:
        return
    pickup = INFO.get(getattr(special, "doomednum", special.type))
    if special.info and special.info[0] not in (None, ""):
        kind, extra = special.info
    elif pickup:
        kind, extra = pickup[5], pickup[6]
    else:
        kind, extra = ("deco", None)
    taken = True
    sfx = "itemup"
    if kind == "health":
        if player.health >= MAXHEALTH:
            taken = False
        else:
            player.health = min(MAXHEALTH, player.health + int(extra))
            player.mo.health = player.health
            player.set_message("Picked up a stimpack." if extra == 10 else "Picked up a medikit.")
    elif kind == "bonus_h":
        player.health = min(200, player.health + 1)
        player.mo.health = player.health
        player.set_message("You pick up a health bonus.")
    elif kind == "bonus_a":
        player.armorpoints = min(200, player.armorpoints + 1)
        if player.armortype == 0:
            player.armortype = 1
        player.set_message("You pick up an armor bonus.")
    elif kind == "armor":
        points = 100 if extra == 1 else 200
        if player.armorpoints >= points:
            taken = False
        else:
            player.armorpoints = points
            player.armortype = int(extra)
            player.set_message("Picked up the armor." if extra == 1 else "Picked up the MegaArmor!")
    elif kind == "soul":
        player.health = min(200, player.health + 100)
        player.mo.health = player.health
        player.set_message("Supercharge!")
    elif kind == "mega":
        player.health = 200
        player.mo.health = 200
        player.armorpoints = 200
        player.armortype = 2
        player.set_message("MegaSphere!")
    elif kind == "berserk":
        taken = give_power(player, PW_STRENGTH)
        if taken:
            if player.readyweapon != WP_FIST:
                player.pendingweapon = WP_FIST
            player.set_message("Berserk!")
            sfx = "getpow"
    elif kind == "key":
        player.cards[int(extra)] = True
        player.set_message(KEY_NAMES.get(int(extra), "You picked up a key."))
    elif kind == "weapon":
        w = int(extra)
        player.weaponowned[w] = True
        if player.readyweapon != w:
            player.pendingweapon = w
        if w in (WP_SHOTGUN, WP_SUPERSHOTGUN):
            give_ammo(player, AM_SHELL, 1)
        elif w == WP_CHAINGUN:
            give_ammo(player, AM_CLIP, 1)
        elif w == WP_MISSILE:
            give_ammo(player, AM_MISL, 1)
        elif w in (WP_PLASMA, WP_BFG):
            give_ammo(player, AM_CELL, 1)
        player.set_message(WEAPON_NAMES.get(w, "You got a weapon!"))
        game.start_sound("wpnup")
    elif kind == "ammo":
        ammo, num = extra
        taken = give_ammo(player, ammo, num)
        if taken:
            player.set_message("Picked up some ammo.")
    elif kind == "backpack":
        for i in range(4):
            player.maxammo[i] = player.maxammo[i] * 2 if player.maxammo[i] < 400 else player.maxammo[i]
            give_ammo(player, i, 1)
        player.set_message("You picked up a backpack full of ammo!")
    elif kind == "item":
        powers = {
            "Invulnerability": (PW_INVULNERABILITY, "Invulnerability!"),
            "Partial invisibility": (PW_INVISIBILITY, "Partial Invisibility"),
            "Radiation shielding": (PW_IRONFEET, "Radiation Shielding Suit"),
            "Computer area map": (PW_ALLMAP, "Computer Area Map"),
            "Light amplification visor": (PW_INFRARED, "Light Amplification Visor"),
        }
        pair = powers.get(str(extra))
        if pair is None:
            player.set_message(str(extra))
        else:
            pw, msg = pair
            taken = give_power(player, pw)
            if taken:
                player.set_message(msg)
                sfx = "getpow"
    else:
        taken = False
    if taken:
        if kind not in ("weapon",):
            game.start_sound(sfx)
        player.bonuscount += 6
        if special.flags & MF_COUNTITEM:
            player.itemcount += 1
        special.alive = False
        special.flags = 0
        if special in game.world.mobjs:
            game.world.mobjs.remove(special)
