"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Load / save (g_game G_DoSaveGame / G_DoLoadGame, condensed p_saveg).

Vanilla writes a 24-byte description then a binary thinker dump. This port
keeps the same 6-slot files (`doomsav0.dsg` … `doomsav5.dsg`) and header, then
JSON for the playable state (player, mobjs, sectors, movers).
"""

from __future__ import annotations

import json
import os

from .defs import GS_LEVEL, LOADSAVEEMPTY, SAVEGAMENAME, SAVESTRINGSIZE
from .player import Mobj, Player
from .specials import Button, FloorMove, Plat, Specials, VerticalDoor
from .world import World

SAVE_MAGIC = b"DOOMPY01"


def save_dir(game) -> str:
    if getattr(game, "iwad_path", ""):
        d = os.path.dirname(os.path.abspath(game.iwad_path))
        if d:
            return d
    return os.getcwd()


def save_path(game, slot: int) -> str:
    return os.path.join(save_dir(game), f"{SAVEGAMENAME}{int(slot)}.dsg")


def _pad_desc(text: str) -> bytes:
    raw = (text or "")[:SAVESTRINGSIZE].encode("latin1", "replace")
    return raw + b"\x00" * (SAVESTRINGSIZE - len(raw))


def _decode_desc(raw: bytes) -> str:
    if b"\x00" in raw:
        raw = raw.split(b"\x00", 1)[0]
    return raw.decode("latin1", "replace").rstrip()


def read_slot_description(game, slot: int) -> tuple[str, bool]:
    path = save_path(game, slot)
    try:
        with open(path, "rb") as f:
            header = f.read(SAVESTRINGSIZE + len(SAVE_MAGIC))
    except OSError:
        return LOADSAVEEMPTY, False
    if len(header) < SAVESTRINGSIZE + len(SAVE_MAGIC):
        return LOADSAVEEMPTY, False
    if header[SAVESTRINGSIZE : SAVESTRINGSIZE + len(SAVE_MAGIC)] != SAVE_MAGIC:
        return LOADSAVEEMPTY, False
    desc = _decode_desc(header[:SAVESTRINGSIZE])
    return (desc or LOADSAVEEMPTY), True


def _json_info(info):
    if info is None:
        return None
    kind, extra = info
    if isinstance(extra, tuple):
        extra = list(extra)
    return [kind, extra]


def _parse_info(raw):
    if raw is None:
        return None
    kind, extra = raw[0], raw[1]
    if isinstance(extra, list):
        extra = tuple(extra)
    return (kind, extra)


def _mobj_index(mobjs, mo) -> int | None:
    if mo is None:
        return None
    for i, other in enumerate(mobjs):
        if other is mo:
            return i
    return None


def _dump_mobj(mo: Mobj, mobjs: list) -> dict:
    return {
        "x": mo.x,
        "y": mo.y,
        "z": mo.z,
        "angle": mo.angle,
        "momx": mo.momx,
        "momy": mo.momy,
        "momz": mo.momz,
        "radius": mo.radius,
        "height": mo.height,
        "floorz": mo.floorz,
        "ceilingz": mo.ceilingz,
        "flags": mo.flags,
        "health": mo.health,
        "type": mo.type,
        "sprite": mo.sprite,
        "info": _json_info(mo.info),
        "alive": mo.alive,
        "reactiontime": mo.reactiontime,
        "target": _mobj_index(mobjs, mo.target),
        "movedir": mo.movedir,
        "movecount": mo.movecount,
        "ai_state": mo.ai_state,
        "frame": mo.frame,
        "tics": mo.tics,
        "chase_tics": mo.chase_tics,
        "just_attacked": mo.just_attacked,
        "damage": mo.damage,
        "attack_kind": getattr(mo, "_attack_kind", ""),
        "did_fire": getattr(mo, "_did_fire", False),
        "is_player": mo.player is not None,
    }


def _dump_player(player: Player) -> dict:
    return {
        "playerstate": player.playerstate,
        "viewz": player.viewz,
        "viewheight": player.viewheight,
        "deltaviewheight": player.deltaviewheight,
        "bob": player.bob,
        "health": player.health,
        "armorpoints": player.armorpoints,
        "armortype": player.armortype,
        "ammo": list(player.ammo),
        "maxammo": list(player.maxammo),
        "weaponowned": list(player.weaponowned),
        "pendingweapon": player.pendingweapon,
        "readyweapon": player.readyweapon,
        "cards": list(player.cards),
        "cheats": player.cheats,
        "message": player.message,
        "message_tics": player.message_tics,
        "attackdown": player.attackdown,
        "usedown": player.usedown,
        "damagecount": player.damagecount,
        "bonuscount": player.bonuscount,
        "extralight": player.extralight,
        "refire": player.refire,
        "killcount": player.killcount,
        "itemcount": player.itemcount,
        "secretcount": player.secretcount,
        "didsecret": player.didsecret,
        "psprite_y": player.psprite_y,
        "psprite_sy": player.psprite_sy,
        "psprite_state": player.psprite_state,
        "psprite_tics": player.psprite_tics,
        "psprite_step": player.psprite_step,
        "psprite_body": player.psprite_body,
        "psprite_flash": player.psprite_flash,
        "flash_tics": player.flash_tics,
    }


def _sector_index(world, sector) -> int:
    for i, s in enumerate(world.sectors):
        if s is sector:
            return i
    return -1


def _dump_thinker(th, world) -> dict | None:
    sec_i = _sector_index(world, getattr(th, "sector", None))
    if sec_i < 0:
        return None
    if isinstance(th, VerticalDoor):
        return {
            "kind": "door",
            "sector": sec_i,
            "type": th.type,
            "direction": th.direction,
            "topheight": th.topheight,
            "speed": th.speed,
            "topwait": th.topwait,
            "topcountdown": th.topcountdown,
        }
    if isinstance(th, Plat):
        return {
            "kind": "plat",
            "sector": sec_i,
            "type": th.type,
            "status": th.status,
            "speed": th.speed,
            "low": th.low,
            "high": th.high,
            "wait": th.wait,
            "count": th.count,
        }
    if isinstance(th, FloorMove):
        return {
            "kind": "floor",
            "sector": sec_i,
            "direction": th.direction,
            "dest": th.dest,
            "speed": th.speed,
        }
    return None


def dump_state(game) -> dict:
    world = game.world
    specials = game.specials
    player = game.player
    mobjs = list(world.mobjs)
    thinkers = []
    if specials:
        for th in specials.thinkers:
            if getattr(th, "dead", False):
                continue
            rec = _dump_thinker(th, world)
            if rec:
                thinkers.append(rec)
    buttons = []
    if specials:
        for btn in specials.buttons:
            line = btn.line
            buttons.append(
                {
                    "line": getattr(line, "i_line", -1),
                    "where": btn.where,
                    "texture": btn.texture,
                    "timer": btn.timer,
                }
            )
    return {
        "episode": game.episode,
        "mapn": game.mapn,
        "skill": game.skill,
        "leveltime": game.leveltime,
        "player": _dump_player(player),
        "sectors": [
            {
                "floorheight": s.floorheight,
                "ceilingheight": s.ceilingheight,
                "floorpic": s.floorpic,
                "ceilingpic": s.ceilingpic,
                "lightlevel": s.lightlevel,
                "special": s.special,
            }
            for s in world.sectors
        ],
        "sides": [
            {
                "textureoffset": sd.textureoffset,
                "rowoffset": sd.rowoffset,
                "toptexture": sd.toptexture,
                "bottomtexture": sd.bottomtexture,
                "midtexture": sd.midtexture,
            }
            for sd in world.sides
        ],
        "lines": [{"flags": ln.flags, "special": ln.special} for ln in world.lines],
        "mobjs": [_dump_mobj(mo, mobjs) for mo in mobjs],
        "thinkers": thinkers,
        "buttons": buttons,
        "totalkills": getattr(game, "totalkills", 0),
        "totalitems": getattr(game, "totalitems", 0),
        "totalsecret": getattr(game, "totalsecret", 0),
    }


def write_save(game, slot: int, description: str) -> bool:
    if game.world is None or game.player is None:
        return False
    path = save_path(game, slot)
    payload = json.dumps(dump_state(game), separators=(",", ":")).encode("utf-8")
    blob = _pad_desc(description) + SAVE_MAGIC + payload
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, path)
    return True


def read_save(game, slot: int) -> dict | None:
    path = save_path(game, slot)
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    need = SAVESTRINGSIZE + len(SAVE_MAGIC)
    if len(data) < need or data[SAVESTRINGSIZE:need] != SAVE_MAGIC:
        return None
    try:
        return json.loads(data[need:].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None


def _restore_player(rec: dict, mo: Mobj) -> Player:
    player = Player(mo=mo)
    player.playerstate = rec.get("playerstate", player.playerstate)
    player.viewz = rec.get("viewz", player.viewz)
    player.viewheight = rec.get("viewheight", player.viewheight)
    player.deltaviewheight = rec.get("deltaviewheight", player.deltaviewheight)
    player.bob = rec.get("bob", player.bob)
    player.health = rec.get("health", player.health)
    player.armorpoints = rec.get("armorpoints", player.armorpoints)
    player.armortype = rec.get("armortype", player.armortype)
    if rec.get("ammo") is not None:
        player.ammo = list(rec["ammo"])
    if rec.get("maxammo") is not None:
        player.maxammo = list(rec["maxammo"])
    if rec.get("weaponowned") is not None:
        player.weaponowned = list(rec["weaponowned"])
    player.pendingweapon = rec.get("pendingweapon", player.pendingweapon)
    player.readyweapon = rec.get("readyweapon", player.readyweapon)
    if rec.get("cards") is not None:
        player.cards = list(rec["cards"])
    player.cheats = rec.get("cheats", player.cheats)
    player.message = rec.get("message", "")
    player.message_tics = rec.get("message_tics", 0)
    player.attackdown = rec.get("attackdown", False)
    player.usedown = rec.get("usedown", False)
    player.damagecount = rec.get("damagecount", 0)
    player.bonuscount = rec.get("bonuscount", 0)
    player.extralight = rec.get("extralight", 0)
    player.refire = rec.get("refire", 0)
    player.killcount = rec.get("killcount", 0)
    player.itemcount = rec.get("itemcount", 0)
    player.secretcount = rec.get("secretcount", 0)
    player.didsecret = rec.get("didsecret", False)
    player.psprite_y = rec.get("psprite_y", player.psprite_y)
    player.psprite_sy = rec.get("psprite_sy", player.psprite_sy)
    player.psprite_state = rec.get("psprite_state", player.psprite_state)
    player.psprite_tics = rec.get("psprite_tics", player.psprite_tics)
    player.psprite_step = rec.get("psprite_step", 0)
    player.psprite_body = rec.get("psprite_body", "")
    player.psprite_flash = rec.get("psprite_flash", "")
    player.flash_tics = rec.get("flash_tics", 0)
    mo.player = player
    mo.health = player.health
    return player


def _restore_mobj(rec: dict) -> Mobj:
    mo = Mobj(
        x=rec.get("x", 0),
        y=rec.get("y", 0),
        z=rec.get("z", 0),
        angle=rec.get("angle", 0),
        momx=rec.get("momx", 0),
        momy=rec.get("momy", 0),
        momz=rec.get("momz", 0),
        radius=rec.get("radius", Mobj().radius),
        height=rec.get("height", Mobj().height),
        floorz=rec.get("floorz", 0),
        ceilingz=rec.get("ceilingz", 0),
        flags=rec.get("flags", 0),
        health=rec.get("health", 0),
        type=rec.get("type", 0),
        sprite=rec.get("sprite", ""),
        info=_parse_info(rec.get("info")),
        alive=rec.get("alive", True),
        reactiontime=rec.get("reactiontime", 0),
        movedir=rec.get("movedir", 8),
        movecount=rec.get("movecount", 0),
        ai_state=rec.get("ai_state", ""),
        frame=rec.get("frame", 0),
        tics=rec.get("tics", 0),
        chase_tics=rec.get("chase_tics", 0),
        just_attacked=rec.get("just_attacked", False),
        damage=rec.get("damage", 0),
    )
    mo._attack_kind = rec.get("attack_kind", "")
    mo._did_fire = rec.get("did_fire", False)
    return mo


def restore_state(game, data: dict) -> None:
    game.episode = int(data["episode"])
    game.mapn = int(data["mapn"])
    game.skill = int(data["skill"])
    game.leveltime = int(data.get("leveltime", 0))
    game.totalkills = int(data.get("totalkills", 0))
    game.totalitems = int(data.get("totalitems", 0))
    game.totalsecret = int(data.get("totalsecret", 0))
    game.world = World()
    game.world.setup_level(game.wad, game.res, game.episode, game.mapn)
    game.specials = Specials(game.world, game.res, game.sound)
    game.specials.exit_requested = False
    world = game.world
    for i, rec in enumerate(data.get("sectors") or []):
        if i >= len(world.sectors):
            break
        s = world.sectors[i]
        s.floorheight = rec.get("floorheight", s.floorheight)
        s.ceilingheight = rec.get("ceilingheight", s.ceilingheight)
        s.floorpic = rec.get("floorpic", s.floorpic)
        s.ceilingpic = rec.get("ceilingpic", s.ceilingpic)
        s.lightlevel = rec.get("lightlevel", s.lightlevel)
        s.special = rec.get("special", s.special)
        s.specialdata = None
    for i, rec in enumerate(data.get("sides") or []):
        if i >= len(world.sides):
            break
        sd = world.sides[i]
        sd.textureoffset = rec.get("textureoffset", sd.textureoffset)
        sd.rowoffset = rec.get("rowoffset", sd.rowoffset)
        sd.toptexture = rec.get("toptexture", sd.toptexture)
        sd.bottomtexture = rec.get("bottomtexture", sd.bottomtexture)
        sd.midtexture = rec.get("midtexture", sd.midtexture)
    for i, rec in enumerate(data.get("lines") or []):
        if i >= len(world.lines):
            break
        ln = world.lines[i]
        ln.flags = rec.get("flags", ln.flags)
        ln.special = rec.get("special", ln.special)
    thinkers = []
    for rec in data.get("thinkers") or []:
        sec_i = rec.get("sector", -1)
        if not (0 <= sec_i < len(world.sectors)):
            continue
        sector = world.sectors[sec_i]
        kind = rec.get("kind")
        if kind == "door":
            th = VerticalDoor(
                sector=sector,
                type=rec.get("type", 0),
                direction=rec.get("direction", 0),
                topheight=rec.get("topheight", 0),
                speed=rec.get("speed", 0),
                topwait=rec.get("topwait", 0),
                topcountdown=rec.get("topcountdown", 0),
            )
        elif kind == "plat":
            th = Plat(
                sector=sector,
                type=rec.get("type", 0),
                status=rec.get("status", 0),
                speed=rec.get("speed", 0),
                low=rec.get("low", 0),
                high=rec.get("high", 0),
                wait=rec.get("wait", 0),
                count=rec.get("count", 0),
            )
        elif kind == "floor":
            th = FloorMove(
                sector=sector,
                direction=rec.get("direction", 0),
                dest=rec.get("dest", 0),
                speed=rec.get("speed", 0),
            )
        else:
            continue
        sector.specialdata = th
        thinkers.append(th)
    game.specials.thinkers = thinkers
    buttons = []
    for rec in data.get("buttons") or []:
        li = rec.get("line", -1)
        if not (0 <= li < len(world.lines)):
            continue
        buttons.append(
            Button(
                line=world.lines[li],
                where=rec.get("where", "top"),
                texture=rec.get("texture", 0),
                timer=rec.get("timer", 0),
            )
        )
    game.specials.buttons = buttons
    recs = data.get("mobjs") or []
    mobjs = [_restore_mobj(rec) for rec in recs]
    for mo, rec in zip(mobjs, recs):
        ti = rec.get("target")
        if isinstance(ti, int) and 0 <= ti < len(mobjs):
            mo.target = mobjs[ti]
    player = None
    for mo, rec in zip(mobjs, recs):
        if rec.get("is_player"):
            player = _restore_player(data.get("player") or {}, mo)
            break
    world.mobjs = mobjs
    game.player = player
    if player is None:
        raise RuntimeError("save has no player")
    game.gamestate = GS_LEVEL
    game.sound.play_level_music(game.episode, game.mapn)


def read_and_restore(game, slot: int) -> bool:
    data = read_save(game, slot)
    if data is None:
        return False
    restore_state(game, data)
    return True
