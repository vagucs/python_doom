"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Game loop (d_main / g_game / d_loop) — 35 Hz tics, pygame input.
"""

from __future__ import annotations

import os
import sys

import pygame

from .collision import angle_to, point_in_subsector
from .compat import as_u32, fixed_mul
from .defs import (
    ANG90,
    ANG180,
    BT_ATTACK,
    BT_CHANGE,
    BT_USE,
    BT_WEAPONSHIFT,
    CF_GODMODE,
    CF_NOCLIP,
    FRACUNIT,
    GS_FINALE,
    GS_INTERMISSION,
    GS_LEVEL,
    GS_TITLE,
    MF_JUSTHIT,
    MF_NOCLIP,
    MF_SKULLFLY,
    MF_SHOOTABLE,
    MF_SOLID,
    PST_DEAD,
    PST_LIVE,
    PST_REBORN,
    PW_IRONFEET,
    PW_STRENGTH,
    RADIATIONPAL,
    SCREENHEIGHT,
    SCREENWIDTH,
    SK_BABY,
    SK_MEDIUM,
    SK_NIGHTMARE,
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
from .am_map import Automap
from .config import load as load_defaults, save as save_defaults
from .deh import deh
from .enemy import kill_monster, p_random, tick_enemies
from .finale import Finale, commercial_finale_map
from .menu import Menu
from .mobj import spawn_map_things, touch_special
from .player import (
    ANGLETURN,
    FORWARDMOVE,
    SIDEMOVE,
    Ticcmd,
    give_power,
    player_think,
    spawn_player,
    WEAPON_FIRE_BODY,
    WEAPON_FIRE_PATCH,
    WEAPON_PATCH,
)
from .r_data import Resources
from .render import Renderer
from .saveg import read_and_restore, write_save
from .sound import Sound
from .specials import Specials
from .sprites import WEAPONBOTTOM, draw_psprite, draw_sprites, weapon_psprite_xy
from .status import StatusBar
from .tables import fine_cos, fine_sin, init_tables
from .v_video import draw_patch, fill
from .video import Video
from .wad import Wad
from .wipe import Wipe
from .wi_stuff import Intermission, WbStart, partime
from .world import World

IWAD_NAMES = (
    "DOOM1.WAD",
    "doom1.wad",
    "DOOM.WAD",
    "doom.wad",
    "DOOM2.WAD",
    "doom2.wad",
    "PLUTONIA.WAD",
    "TNT.WAD",
    "freedoom1.wad",
    "freedoom2.wad",
)


def find_iwad(explicit: str | None = None) -> str:
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        raise FileNotFoundError(f"IWAD not found: {explicit}")
    env = os.environ.get("DOOMWADDIR") or os.environ.get("DOOMWADPATH")
    roots = [
        os.getcwd(),
        os.path.dirname(__file__),
        os.path.dirname(os.path.dirname(__file__)),
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ]
    if env:
        roots.insert(0, env)
    for root in roots:
        for name in IWAD_NAMES:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                return path
    raise FileNotFoundError(
        "No IWAD found. Put doom1.wad in this folder or pass -iwad file.wad"
    )


class Game:
    DEMOMARKER = 0x80

    def __init__(self) -> None:
        self.wad = Wad()
        self.video = Video()
        self.sound = Sound()
        self.res: Resources | None = None
        self.renderer: Renderer | None = None
        self.world: World | None = None
        self.specials: Specials | None = None
        self.status: StatusBar | None = None
        self.player = None
        self.gamestate = GS_TITLE
        self.episode = 1
        self.mapn = 1
        self.skill = SK_MEDIUM
        self.leveltime = 0
        self.keys: set[int] = set()
        self.turnheld = 0
        self.running = True
        self.show_fps = False
        self.nomonsters = False
        self.fastparm = False
        self.respawnparm = False
        self.respawnmonsters = False
        self._fast_on = None
        self.fullscreen = False
        self.crt = False
        self.title_patch: bytes | None = None
        self.credit_patch: bytes | None = None
        self.page_patch: bytes | None = None
        self.page_tic = 0
        self.demo_sequence = -1
        self.advancedemo = False
        self.demo_playback = False
        self.demo_recording = False
        self.demo_buffer: bytes | bytearray | None = None
        self.demo_p = 0
        self.demo_name = ""
        self.singledemo = False
        self.timingdemo = False
        self.timedemo_start = 0
        self.gametic = 0
        self.pwad_files: list[str] = []
        self.record_name: str | None = None
        self.playdemo_name: str | None = None
        self.timedemo_name: str | None = None
        self.nosound = False
        self.nomusic = False
        self.use_mouse = True
        self.mousex = 0
        self.mousey = 0
        self.mouse_fire = False
        self.iwad_path = ""
        self.menu: Menu | None = None
        self.show_messages = True
        self.detail_level = 0
        self.screen_size = 7
        self.mouse_sensitivity = 5
        self._st_palette = -1
        self._playpal: bytes | None = None
        self.totalkills = 0
        self.totalitems = 0
        self.totalsecret = 0
        self.wi: Intermission | None = None
        self.finale: Finale | None = None
        self.wipe = Wipe()
        self.wipegamestate: int | None = GS_TITLE
        self.wiping = False
        self.force_wipe = False
        self.next_mapn = 1
        self.automap = Automap()

    def start_sound(self, name: str) -> None:
        self.sound.play(name)

    def touch_special(self, special, toucher) -> None:
        touch_special(self, special, toucher)

    def use_special(self, line, thing, side: int) -> bool:
        if self.specials:
            return bool(self.specials.use_special(line, thing, side))
        return False

    def cross_special(self, line, side: int, thing) -> None:
        if self.specials:
            self.specials.cross_special(line, side, thing)

    def shoot_special(self, line, thing) -> None:
        if self.specials:
            self.specials.shoot_special(line, thing)

    def damage_mobj(self, target, source, damage: int, inflictor=None) -> None:
        if not target.alive or not (target.flags & MF_SHOOTABLE):
            return
        if target.player and self.skill == SK_BABY:
            damage >>= 1
        src = inflictor if inflictor is not None else source
        skip_saw = (
            source is not None
            and getattr(source, "player", None) is not None
            and source.player.readyweapon == WP_CHAINSAW
        )
        if src is not None and not (target.flags & MF_NOCLIP) and not skip_saw:
            from .info import MI_MASS, MOBJINFO

            ang = angle_to(src.x, src.y, target.x, target.y)
            mass = MOBJINFO[target.type][MI_MASS] or 100
            thrust = damage * (FRACUNIT // 8) * 100 // mass
            if (
                damage < 40
                and damage > target.health
                and target.z - src.z > 64 * FRACUNIT
                and (p_random() & 1)
            ):
                ang = as_u32(ang + ANG180)
                thrust *= 4
            target.momx += fixed_mul(thrust, fine_cos(ang))
            target.momy += fixed_mul(thrust, fine_sin(ang))
        if target.player:
            player = target.player
            if ((player.cheats & CF_GODMODE) or player.powers[0]) and damage < 1000:
                return
            saved = 0
            if player.armortype:
                saved = damage // (player.armortype == 1 and 3 or 2)
                if player.armorpoints <= saved:
                    saved = player.armorpoints
                    player.armortype = 0
                player.armorpoints -= saved
            damage -= saved
            player.health -= damage
            target.health = player.health
            player.damagecount += damage
            if player.damagecount > 100:
                player.damagecount = 100
            player.attacker = source
            if player.health <= 0:
                player.health = 0
                player.playerstate = PST_DEAD
                target.alive = False
                target.flags &= ~(MF_SOLID | MF_SHOOTABLE)
                self.start_sound("pldeth")
            else:
                self.start_sound("plpain")
                self._pain_or_wake(target, source)
            return
        target.health -= damage
        if target.health <= 0:
            kill_monster(target, self, source)
            return
        self._pain_or_wake(target, source)

    def _pain_or_wake(self, target, source) -> None:
        from .info import MI_PAINCHANCE, MI_PAINSTATE, MI_SEESTATE, MI_SPAWNSTATE, MOBJINFO
        from .thinker import set_mobj_state

        info = MOBJINFO[target.type]
        if p_random() < info[MI_PAINCHANCE] and not (target.flags & MF_SKULLFLY):
            target.flags |= MF_JUSTHIT
            if info[MI_PAINSTATE]:
                set_mobj_state(target, info[MI_PAINSTATE], self.world, self)
        target.reactiontime = 0
        if source is not None and source is not target and target.player is None:
            target.target = source
            if target.istate == info[MI_SPAWNSTATE] and info[MI_SEESTATE]:
                set_mobj_state(target, info[MI_SEESTATE], self.world, self)

    def load_level(self, carry: bool = False) -> None:
        assert self.res is not None
        prev = self.player if carry else None
        from .enemy import clear_random

        clear_random()
        self.world = World()
        self.world.setup_level(self.wad, self.res, self.episode, self.mapn)
        self.specials = Specials(self.world, self.res, self.sound)
        self.player = None
        self.totalkills, self.totalitems = spawn_map_things(self.world, self.skill, self)
        if self.player is None:
            raise RuntimeError("no player 1 start")
        if prev is not None:
            self._carry_player(prev)
        self.player.killcount = 0
        self.player.itemcount = 0
        self.player.secretcount = 0
        self.totalsecret = sum(1 for s in self.world.sectors if s.special == 9)
        from .thinker import apply_fast

        apply_fast(self)
        self.leveltime = 0
        self.gamestate = GS_LEVEL
        self.specials.exit_requested = False
        self.specials.secret_exit = False
        self.wi = None
        self.finale = None
        self.sound.play_level_music(self.episode, self.mapn)
        self.automap.reset_level()
        if self.status:
            self.status.reset(self.player)
        print(f"Entering E{self.episode}M{self.mapn}")

    def _carry_player(self, prev) -> None:
        p = self.player
        p.health = prev.health
        p.mo.health = prev.health
        p.armorpoints = prev.armorpoints
        p.armortype = prev.armortype
        p.ammo = list(prev.ammo)
        p.maxammo = list(prev.maxammo)
        p.weaponowned = list(prev.weaponowned)
        p.pendingweapon = WP_NOCHANGE
        p.readyweapon = prev.readyweapon
        p.psprite_state = "up"
        p.psprite_sy = 128 * FRACUNIT
        p.psprite_body = ""
        p.cheats = prev.cheats
        p.didsecret = prev.didsecret
        p.cards = [False] * 6
        p.damagecount = 0
        p.bonuscount = 0
        p.extralight = 0
        p.playerstate = PST_LIVE

    def _commercial(self) -> bool:
        return self.wad.check_num_for_name("MAP01") >= 0

    def complete_level(self) -> None:
        self.automap.stop()
        p = self.player
        if p is not None:
            p.cards = [False] * 6
            p.damagecount = 0
            p.bonuscount = 0
            p.extralight = 0
        secret = bool(self.specials and self.specials.secret_exit)
        commercial = self._commercial()
        if not commercial and self.mapn == 8:
            self.finale = Finale(self)
            self.gamestate = GS_FINALE
            return
        if not commercial and self.mapn == 9 and p is not None:
            p.didsecret = True
        if commercial:
            if secret and self.mapn == 15:
                nxt = 30
            elif secret and self.mapn == 31:
                nxt = 31
            elif self.mapn in (31, 32):
                nxt = 15
            else:
                nxt = self.mapn
        else:
            if secret:
                nxt = 8
            elif self.mapn == 9:
                nxt = {1: 3, 2: 5, 3: 6, 4: 2}.get(self.episode, 0)
            else:
                nxt = self.mapn
        self.next_mapn = nxt + 1
        kills = self.totalkills or 1
        items = self.totalitems or 1
        secrets = self.totalsecret or 1
        wbs = WbStart(
            epsd=self.episode - 1,
            last=self.mapn - 1,
            next=nxt,
            maxkills=kills,
            maxitems=items,
            maxsecret=secrets,
            partime=partime(self.episode, self.mapn, commercial),
            skills=p.killcount if p else 0,
            sitems=p.itemcount if p else 0,
            ssecret=p.secretcount if p else 0,
            stime=self.leveltime,
            didsecret=bool(p and p.didsecret),
            commercial=commercial,
        )
        self.wi = Intermission(self, wbs)
        self.gamestate = GS_INTERMISSION

    def world_done(self, from_finale: bool = False) -> None:
        secret = bool(self.specials and self.specials.secret_exit)
        if secret and self.player:
            self.player.didsecret = True
        if not from_finale and self._commercial() and commercial_finale_map(self.mapn, secret):
            self.finale = Finale(self)
            self.gamestate = GS_FINALE
            return
        self.mapn = self.next_mapn
        if self._commercial():
            lump = f"MAP{self.mapn:02d}"
        else:
            lump = f"E{self.episode}M{self.mapn}"
        if self.wad.check_num_for_name(lump) < 0:
            self.return_to_title()
            return
        self.load_level(carry=True)

    def next_map(self) -> None:
        self.complete_level()

    def start_new_game(self, skill: int, episode: int, mapn: int) -> None:
        from .thinker import apply_fast

        self.demo_playback = False
        self.advancedemo = False
        self.demo_buffer = None
        self.skill = skill
        self.episode = episode
        self.mapn = mapn
        self._fast_on = None
        apply_fast(self)
        self.load_level(carry=False)
        if self.demo_recording:
            self.begin_recording()

    def save_game(self, slot: int, description: str) -> bool:
        if self.gamestate != GS_LEVEL or self.player is None or self.world is None:
            return False
        try:
            ok = write_save(self, slot, description)
        except OSError:
            return False
        if ok:
            self.player.set_message("game saved.")
        return ok

    def load_game(self, slot: int) -> bool:
        self.demo_playback = False
        self.advancedemo = False
        self.demo_buffer = None
        try:
            ok = read_and_restore(self, slot)
        except (OSError, KeyError, TypeError, ValueError, RuntimeError):
            return False
        if not ok:
            return False
        self._st_palette = -1
        self.keys.clear()
        self.automap.reset_level()
        if self.status:
            self.status.reset(self.player)
        if self.player:
            self.player.set_message("game loaded.")
        print(f"Loaded E{self.episode}M{self.mapn}")
        return True

    def return_to_title(self) -> None:
        self.player = None
        self.world = None
        self.wi = None
        self.finale = None
        self.automap.reset_level()
        if self.menu:
            self.menu.clear()
        self.start_title()

    def start_title(self) -> None:
        self.demo_playback = False
        self.demo_buffer = None
        self.demo_p = 0
        self.demo_sequence = -1
        self.advancedemo = True
        self.do_advance_demo()

    def page_ticker(self) -> None:
        self.page_tic -= 1
        if self.page_tic < 0:
            self.advancedemo = True

    def do_advance_demo(self) -> None:
        self.advancedemo = False
        self.demo_playback = False
        self.demo_sequence = (self.demo_sequence + 1) % 6
        if self.demo_sequence == 0:
            self.page_tic = TICRATE * 11 if self._commercial() else 170
            self.gamestate = GS_TITLE
            self.page_patch = self.title_patch
            self.sound.play_title_music()
        elif self.demo_sequence == 1:
            if not self.play_demo("demo1"):
                self.advancedemo = True
                self.do_advance_demo()
        elif self.demo_sequence == 2:
            self.page_tic = 200
            self.gamestate = GS_TITLE
            self.page_patch = self.credit_patch or self.title_patch
        elif self.demo_sequence == 3:
            if not self.play_demo("demo2"):
                self.advancedemo = True
                self.do_advance_demo()
        elif self.demo_sequence == 4:
            self.page_tic = TICRATE * 11 if self._commercial() else 200
            self.gamestate = GS_TITLE
            self.page_patch = self.title_patch
            if self._commercial():
                self.sound.play_title_music()
        else:
            if not self.play_demo("demo3"):
                self.advancedemo = True
                self.do_advance_demo()

    def play_demo(self, name: str) -> bool:
        data = self._load_demo_bytes(name)
        if data is None or len(data) < 13:
            return False
        self.demo_buffer = data
        self.demo_p = 0
        demo_version = data[self.demo_p]
        self.demo_p += 1
        if demo_version <= 4:
            self.demo_p = 0
        demo_skill = data[self.demo_p]
        self.demo_p += 1
        demo_episode = data[self.demo_p]
        self.demo_p += 1
        demo_map = data[self.demo_p]
        self.demo_p += 1
        self.demo_p += 5
        self.demo_p += 4
        if demo_skill <= 4:
            self.skill = demo_skill
        if demo_episode >= 1:
            self.episode = demo_episode
        if demo_map >= 1:
            self.mapn = demo_map
        self.load_level(False)
        self.demo_playback = True
        if self.timingdemo:
            self.timedemo_start = pygame.time.get_ticks()
            self.gametic = 0
        return True

    def _load_demo_bytes(self, name: str) -> bytes | None:
        for path in (name, name + ".lmp"):
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    return fh.read()
        if self.wad.check_num_for_name(name) < 0:
            return None
        return self.wad.cache_lump_name(name)

    def begin_recording(self) -> None:
        buf = bytearray()
        buf.append(109)
        buf.append(self.skill & 0xFF)
        buf.append(self.episode & 0xFF)
        buf.append(self.mapn & 0xFF)
        buf.append(0)
        buf.append(1 if self.respawnparm else 0)
        buf.append(1 if self.fastparm else 0)
        buf.append(1 if self.nomonsters else 0)
        buf.append(0)
        buf.extend(b"\x01\x00\x00\x00")
        self.demo_buffer = buf
        self.demo_p = len(buf)
        self.demo_recording = True

    def write_demo_ticcmd(self, cmd: Ticcmd) -> None:
        if not isinstance(self.demo_buffer, bytearray):
            return
        self.demo_buffer.append(cmd.forwardmove & 0xFF)
        self.demo_buffer.append(cmd.sidemove & 0xFF)
        self.demo_buffer.append((cmd.angleturn >> 8) & 0xFF)
        self.demo_buffer.append(cmd.buttons & 0xFF)
        self.demo_p = len(self.demo_buffer)

    def finish_recording(self) -> None:
        if not self.demo_recording or not isinstance(self.demo_buffer, bytearray):
            return
        self.demo_buffer.append(Game.DEMOMARKER)
        name = self.demo_name or "demo.lmp"
        if not name.lower().endswith(".lmp"):
            name = name + ".lmp"
        try:
            with open(name, "wb") as fh:
                fh.write(self.demo_buffer)
            print(f"Demo {name} recorded")
        except OSError as exc:
            print(f"Demo write failed: {exc}")
        self.demo_recording = False

    def check_demo_status(self) -> None:
        if self.timingdemo:
            now = pygame.time.get_ticks()
            real = max(1, (now - self.timedemo_start) * TICRATE // 1000)
            fps = (self.gametic * TICRATE) / real
            print(f"timed {self.gametic} gametics in {real} realtics ({fps:.1f} fps)")
            self.timingdemo = False
            self.demo_playback = False
            self.running = False
            return
        if self.demo_playback:
            self.demo_playback = False
            if self.singledemo:
                self.running = False
            else:
                self.advancedemo = True
            return
        if self.demo_recording:
            self.finish_recording()
            self.running = False

    def _demo_sbyte(self) -> int:
        n = self.demo_buffer[self.demo_p]
        self.demo_p += 1
        return n - 256 if n >= 128 else n

    def read_demo_ticcmd(self) -> Ticcmd:
        cmd = Ticcmd()
        if (
            self.demo_buffer is None
            or self.demo_p + 4 > len(self.demo_buffer)
            or self.demo_buffer[self.demo_p] == Game.DEMOMARKER
        ):
            self.check_demo_status()
            return cmd
        cmd.forwardmove = self._demo_sbyte()
        cmd.sidemove = self._demo_sbyte()
        cmd.angleturn = self.demo_buffer[self.demo_p] << 8
        self.demo_p += 1
        if cmd.angleturn >= 32768:
            cmd.angleturn -= 65536
        cmd.buttons = self.demo_buffer[self.demo_p]
        self.demo_p += 1
        return cmd

    def begin_play(self) -> None:
        self.demo_playback = False
        self.advancedemo = False
        self.demo_buffer = None
        self.load_level(False)

    def build_ticcmd(self) -> Ticcmd:
        cmd = Ticcmd()
        k = pygame
        speed = 1 if (k.K_LSHIFT in self.keys or k.K_RSHIFT in self.keys) else 0
        strafe = k.K_LALT in self.keys or k.K_RALT in self.keys
        turning = k.K_RIGHT in self.keys or k.K_LEFT in self.keys
        self.turnheld = self.turnheld + 1 if turning else 0
        tspeed = 2 if self.turnheld < 6 else speed
        if strafe:
            if k.K_RIGHT in self.keys:
                cmd.sidemove += SIDEMOVE[speed]
            if k.K_LEFT in self.keys:
                cmd.sidemove -= SIDEMOVE[speed]
        else:
            if k.K_RIGHT in self.keys:
                cmd.angleturn -= ANGLETURN[tspeed]
            if k.K_LEFT in self.keys:
                cmd.angleturn += ANGLETURN[tspeed]
        if k.K_UP in self.keys:
            cmd.forwardmove += FORWARDMOVE[speed]
        if k.K_DOWN in self.keys:
            cmd.forwardmove -= FORWARDMOVE[speed]
        if k.K_COMMA in self.keys:
            cmd.sidemove -= SIDEMOVE[speed]
        if k.K_PERIOD in self.keys:
            cmd.sidemove += SIDEMOVE[speed]
        if k.K_RCTRL in self.keys or k.K_LCTRL in self.keys:
            cmd.buttons |= BT_ATTACK
        if k.K_SPACE in self.keys or k.K_e in self.keys:
            cmd.buttons |= BT_USE
        weap = {
            k.K_2: WP_PISTOL,
            k.K_3: WP_SHOTGUN,
            k.K_4: WP_CHAINGUN,
            k.K_5: WP_MISSILE,
            k.K_6: WP_PLASMA,
            k.K_7: WP_BFG,
        }
        if k.K_1 in self.keys:
            if self.player and self.player.readyweapon == WP_CHAINSAW:
                w1 = WP_FIST
            elif self.player and self.player.weaponowned[WP_CHAINSAW]:
                w1 = WP_CHAINSAW
            else:
                w1 = WP_FIST
            cmd.buttons |= BT_CHANGE | (w1 << BT_WEAPONSHIFT)
        else:
            for key, w in weap.items():
                if key in self.keys:
                    cmd.buttons |= BT_CHANGE | (w << BT_WEAPONSHIFT)
                    break
        if self.use_mouse:
            sens = (self.mouse_sensitivity + 5) / 10.0
            mx = int(self.mousex * sens)
            my = int(self.mousey * sens)
            cmd.forwardmove += my
            if cmd.forwardmove > 127:
                cmd.forwardmove = 127
            if cmd.forwardmove < -127:
                cmd.forwardmove = -127
            if strafe:
                cmd.sidemove += mx * 2
                if cmd.sidemove > 127:
                    cmd.sidemove = 127
                if cmd.sidemove < -127:
                    cmd.sidemove = -127
            else:
                cmd.angleturn -= mx * 8
            if self.mouse_fire:
                cmd.buttons |= BT_ATTACK
            self.mousex = 0
            self.mousey = 0
        return cmd

    def run_tic(self) -> None:
        self.gametic += 1
        self._sync_mouse_grab()
        if self.wiping:
            done = self.wipe.tick(1, self.video.fb)
            if done:
                self.wiping = False
            return
        if self.menu:
            self.menu.ticker()
        self.sound.update()
        if self.advancedemo:
            self.do_advance_demo()
        if self.gamestate == GS_TITLE:
            self.page_ticker()
            return
        if self.gamestate == GS_INTERMISSION:
            if self.wi:
                self.wi.ticker()
                if self.wi.done:
                    self.world_done()
            return
        if self.gamestate == GS_FINALE:
            if self.finale:
                self.finale.ticker()
                if self.finale.done:
                    if self.finale.action == "worlddone":
                        self.world_done(from_finale=True)
                    else:
                        self.return_to_title()
            return
        if self.gamestate != GS_LEVEL or self.player is None:
            return
        if self.demo_playback:
            self.player.cmd = self.read_demo_ticcmd()
        elif self.menu and self.menu.active:
            self.player.cmd = Ticcmd()
        else:
            self.player.cmd = self.build_ticcmd()
            if self.demo_recording:
                self.write_demo_ticcmd(self.player.cmd)
        player_think(self.world, self.player, self, self.leveltime)
        if self.player.playerstate == PST_REBORN:
            self.load_level(False)
            return
        tick_enemies(self.world, self)
        if self.specials:
            self.specials.tick()
            if self.specials.exit_requested:
                self.start_sound("swtchx")
                self.complete_level()
                return
        self.leveltime += 1
        self.automap.ticker(self)
        if self.status:
            self.status.ticker(self.player)

    def draw(self) -> None:
        fb = self.video.fb
        if self.wiping:
            if self.menu:
                self.menu.draw(fb)
            self._apply_palette()
            self.video.present()
            return
        need_wipe = self.force_wipe or self.gamestate != self.wipegamestate
        self.force_wipe = False
        if need_wipe:
            self.wipe.capture_start(fb)
        self._draw_frame(fb)
        if need_wipe:
            self.wipe.capture_end(fb)
            self.wipe.begin(fb)
            self.wipegamestate = self.gamestate
            self.wiping = True
        if self.menu:
            self.menu.draw(fb)
        self._apply_palette()
        self.video.present()

    def _draw_frame(self, fb: bytearray) -> None:
        if self.gamestate == GS_TITLE and self.page_patch:
            fill(fb, 0)
            draw_patch(fb, 0, 0, self.page_patch)
            return
        if self.gamestate == GS_INTERMISSION and self.wi:
            self.wi.draw(fb)
            return
        if self.gamestate == GS_FINALE and self.finale:
            self.finale.draw(fb)
            return
        if self.gamestate != GS_LEVEL or self.player is None:
            fill(fb, 0)
            return
        if self.automap.active:
            self.automap.drawer(fb, self)
        else:
            mo = self.player.mo
            fill(fb, 0)
            self.renderer.setup_frame(
                mo.x, mo.y, self.player.viewz, mo.angle, self.player.extralight, self.player.fixedcolormap
            )
            self.renderer.render(self.world, fb)
            draw_sprites(self.renderer, self.world, fb)
            self.renderer.draw_masked()
            if self.player.playerstate != PST_DEAD or self.player.psprite_sy < WEAPONBOTTOM:
                self._draw_weapon(fb)
        if self.status and (self.automap.active or self.renderer.screenblocks < 11):
            self.status.draw(fb, self.player, show_messages=self.show_messages)

    def _apply_palette(self) -> None:
        """ST_doPaletteStuff: red shift on damage, gold on pickup."""
        pal = 0
        p = self.player
        if p is not None and self.gamestate == GS_LEVEL:
            cnt = p.damagecount
            if p.powers[PW_STRENGTH]:
                bzc = 12 - (p.powers[PW_STRENGTH] // 64)
                if bzc > cnt:
                    cnt = bzc
            if cnt:
                pal = (cnt + 7) >> 3
                if pal >= 8:
                    pal = 7
                pal += 1
            elif p.bonuscount:
                pal = (p.bonuscount + 7) >> 3
                if pal >= 4:
                    pal = 3
                pal += 9
            elif p.powers[PW_IRONFEET] > 4 * 32 or (p.powers[PW_IRONFEET] & 8):
                pal = RADIATIONPAL
        if pal == self._st_palette:
            return
        self._st_palette = pal
        lump = self._playpal
        if lump is None:
            return
        off = pal * 768
        chunk = lump[off : off + 768]
        if len(chunk) == 768:
            self.video.set_palette_raw(chunk)

    def _draw_weapon(self, fb: bytearray) -> None:
        sx, sy = weapon_psprite_xy(self.player, self.leveltime)
        if self.player.psprite_body:
            body = self.player.psprite_body
        elif self.player.psprite_state in ("atk", "fire"):
            body = WEAPON_FIRE_BODY.get(self.player.readyweapon) or WEAPON_PATCH.get(
                self.player.readyweapon, "PISGA0"
            )
        else:
            body = WEAPON_PATCH.get(self.player.readyweapon, "PISGA0")
        n = self.wad.check_num_for_name(body)
        if n < 0:
            n = self.wad.check_num_for_name("PISGA0")
        if n >= 0:
            draw_psprite(self.renderer, fb, self.wad.cache_lump_num(n), sx, sy)
        flash = self.player.psprite_flash if self.player.flash_tics > 0 else ""
        if not flash and self.player.psprite_state == "fire":
            flash = WEAPON_FIRE_PATCH.get(self.player.readyweapon) or ""
        if flash:
            fn = self.wad.check_num_for_name(flash)
            if fn >= 0:
                draw_psprite(self.renderer, fb, self.wad.cache_lump_num(fn), sx, sy)

    def apply_view_size(self) -> None:
        if self.renderer is None:
            return
        self.renderer.set_view_size(self.screen_size + 3, self.detail_level)

    def _sync_mouse_grab(self) -> None:
        want = (
            self.use_mouse
            and self.gamestate == GS_LEVEL
            and not self.demo_playback
            and not (self.menu and self.menu.active)
        )
        self.video.set_relative_mouse(want)

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            if self.demo_recording:
                self.finish_recording()
            self.running = False
        elif ev.type == pygame.MOUSEMOTION:
            if self.use_mouse:
                self.mousex += ev.rel[0]
                self.mousey += -ev.rel[1]
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            if ev.button == 1:
                self.mouse_fire = True
                if self.finale and self.gamestate == GS_FINALE:
                    self.finale.responder()
        elif ev.type == pygame.MOUSEBUTTONUP:
            if ev.button == 1:
                self.mouse_fire = False
        elif ev.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and (mods & pygame.KMOD_ALT):
                self.video.toggle_fullscreen()
                self.fullscreen = self.video.fullscreen
                return
            uni = getattr(ev, "unicode", "") or ""
            if self.finale and self.gamestate == GS_FINALE:
                self.keys.add(ev.key)
                if self.finale.responder():
                    return
            if self.menu and self.menu.responder(ev.key, uni):
                return
            if self.automap.responder(ev, self):
                return
            plus_keys = {pygame.K_EQUALS, pygame.K_KP_PLUS}
            minus_keys = {pygame.K_MINUS, pygame.K_KP_MINUS}
            if hasattr(pygame, "K_PLUS"):
                plus_keys.add(pygame.K_PLUS)
            if ev.key in plus_keys or ev.key in minus_keys:
                delta = 1 if ev.key in plus_keys else -1
                if self.video.change_scale(delta):
                    self.start_sound("stnmov")
                return
            self.keys.add(ev.key)
            if ev.key == pygame.K_F11:
                self.video.show_fps = not self.video.show_fps
            elif self.demo_playback or self.gamestate == GS_TITLE:
                self.begin_play()
            else:
                self._feed_cheat(uni)
        elif ev.type == pygame.KEYUP:
            self.keys.discard(ev.key)
            self.automap.responder(ev, self)

    def _feed_cheat(self, uni: str) -> None:
        """st_stuff cht_CheckCheat: IDDQD, IDKFA, IDCLIP, IDCLEV, IDMUS, IDBEHOLD*."""
        if self.gamestate != GS_LEVEL or self.player is None:
            return
        ch = (uni or "").lower()
        if len(ch) != 1 or not (ch.isalpha() or ch.isdigit()):
            return
        nightmare = self.skill == SK_NIGHTMARE
        for cheat in deh.cheats:
            param = cheat.feed(ch)
            if param is None:
                continue
            if nightmare and cheat.action not in ("clev", "iddt"):
                continue
            self._do_cheat(cheat.action, param)

    def _do_cheat(self, action: str, param: str) -> None:
        if action == "god":
            self._cheat_god()
        elif action == "kfa":
            self._cheat_ammo(True)
        elif action == "fa":
            self._cheat_ammo(False)
        elif action in ("noclip", "noclip2"):
            self._cheat_noclip()
        elif action == "iddt":
            if self.automap.active:
                self.automap.cycle_iddt()
        elif action == "behold":
            self.player.set_message("invin visis rad allmap lite amp")
        elif action.startswith("behold") and len(action) == 7:
            self._cheat_behold("vsiral".find(action[6]))
        elif action == "choppers":
            p = self.player
            p.weaponowned[WP_CHAINSAW] = True
            p.pendingweapon = WP_CHAINSAW
            p.powers[0] = 1
            p.set_message("... doesn't suck - GM")
        elif action == "mypos":
            p = self.player
            mo = p.mo
            p.set_message(f"ang=0x{mo.angle & 0xFFFFFFFF:x};x,y=(0x{mo.x:x},0x{mo.y:x})")
        elif action == "clev":
            self._cheat_clev(param)
        elif action == "mus":
            self._cheat_mus(param)

    def _cheat_god(self) -> None:
        p = self.player
        p.cheats ^= CF_GODMODE
        if p.cheats & CF_GODMODE:
            p.health = deh.god_mode_health
            if p.mo:
                p.mo.health = deh.god_mode_health
            p.set_message("Degreelessness Mode On")
        else:
            p.set_message("Degreelessness Mode Off")

    def _cheat_ammo(self, keys: bool) -> None:
        p = self.player
        if keys:
            p.armorpoints = deh.idkfa_armor
            p.armortype = deh.idkfa_armor_class
        else:
            p.armorpoints = deh.idfa_armor
            p.armortype = deh.idfa_armor_class
        for i in range(len(p.weaponowned)):
            p.weaponowned[i] = True
        p.maxammo = list(deh.maxammo)
        for i in range(len(p.ammo)):
            p.ammo[i] = p.maxammo[i]
        if keys:
            p.cards = [True] * 6
        p.set_message("Very Happy Ammo Added" if keys else "Ammo Added")

    def _cheat_noclip(self) -> None:
        p = self.player
        p.cheats ^= CF_NOCLIP
        if p.cheats & CF_NOCLIP:
            p.mo.flags |= MF_NOCLIP
        else:
            p.mo.flags &= ~MF_NOCLIP
        p.set_message("No Clipping Mode ON" if p.cheats & CF_NOCLIP else "No Clipping Mode OFF")

    def _cheat_behold(self, pw: int) -> None:
        if pw < 0:
            return
        p = self.player
        if not p.powers[pw]:
            give_power(p, pw)
            if pw == PW_STRENGTH and p.readyweapon != WP_FIST:
                p.pendingweapon = WP_FIST
        elif pw == PW_STRENGTH:
            p.powers[pw] = 0
        else:
            p.powers[pw] = 1
        p.set_message("Power-up Toggled")

    def _cheat_clev(self, param: str) -> None:
        if len(param) < 2 or not param.isdigit():
            return
        a, b = int(param[0]), int(param[1])
        if self._commercial():
            episode, mapn = 1, a * 10 + b
            lump = f"MAP{mapn:02d}"
        else:
            episode, mapn = a, b
            lump = f"E{episode}M{mapn}"
        if episode < 1 or mapn < 1 or self.wad.check_num_for_name(lump) < 0:
            return
        self.player.set_message("Changing Level...")
        self.start_new_game(self.skill, episode, mapn)

    def _cheat_mus(self, param: str) -> None:
        if len(param) < 2 or not param.isdigit():
            return
        a, b = int(param[0]), int(param[1])
        if self._commercial():
            mapn = a * 10 + b
            from .sound import DOOM2_MUSIC

            if mapn < 1 or mapn > len(DOOM2_MUSIC):
                self.player.set_message("IMPOSSIBLE SELECTION")
                return
            name = DOOM2_MUSIC[mapn - 1]
        else:
            if a < 1 or b < 1 or b > 9:
                self.player.set_message("IMPOSSIBLE SELECTION")
                return
            name = f"e{a}m{b}"
        if not self.sound.has_music(name):
            self.player.set_message("IMPOSSIBLE SELECTION")
            return
        self.sound.change_music(name, looping=True)
        self.player.set_message("Music Change")


def parse_args(argv: list[str], game: Game) -> str | None:
    iwad = None
    args = argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-iwad" and i + 1 < len(args):
            iwad = args[i + 1]
            i += 2
            continue
        if a == "-fps":
            game.show_fps = True
            i += 1
            continue
        if a == "-nomonsters":
            game.nomonsters = True
            i += 1
            continue
        if a == "-fast":
            game.fastparm = True
            i += 1
            continue
        if a == "-respawn":
            game.respawnparm = True
            i += 1
            continue
        if a == "-warp" and i + 2 < len(args):
            game.episode = int(args[i + 1])
            game.mapn = int(args[i + 2])
            i += 3
            continue
        if a == "-skill" and i + 1 < len(args):
            game.skill = int(args[i + 1])
            i += 2
            continue
        if a == "-fullscreen":
            game.fullscreen = True
            i += 1
            continue
        if a == "-crt":
            game.crt = True
            i += 1
            continue
        if a == "-deh":
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                deh.files.append(args[i])
                i += 1
            continue
        if a == "-nodeh":
            deh.nodeh = True
            i += 1
            continue
        if a == "-dehlump":
            deh.dehlump = True
            i += 1
            continue
        if a == "-nocheats":
            deh.apply_cheats = False
            i += 1
            continue
        if a == "-file":
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                game.pwad_files.append(args[i])
                i += 1
            continue
        if a == "-record" and i + 1 < len(args):
            game.record_name = args[i + 1]
            i += 2
            continue
        if a == "-playdemo" and i + 1 < len(args):
            game.playdemo_name = args[i + 1]
            i += 2
            continue
        if a == "-timedemo" and i + 1 < len(args):
            game.timedemo_name = args[i + 1]
            i += 2
            continue
        if a == "-nosound":
            game.nosound = True
            i += 1
            continue
        if a == "-nomusic":
            game.nomusic = True
            i += 1
            continue
        if a.lower().endswith(".wad") and not a.startswith("-"):
            iwad = a
        i += 1
    return iwad


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    game = Game()
    load_defaults(game)
    iwad_arg = parse_args(argv, game)
    path = find_iwad(iwad_arg)
    game.iwad_path = path
    print(f"IWAD: {path}")
    game.wad.add_file(path)
    for extra in game.pwad_files:
        print(f"PWAD: {extra}")
        game.wad.add_file(extra)
    deh.load_after_iwad(game.wad, path)
    init_tables()
    game.res = Resources(game.wad)
    game.res.init()
    game.renderer = Renderer(game.res)
    game.apply_view_size()
    if not game.nosound:
        pygame.mixer.pre_init(frequency=11025, size=-16, channels=1, buffer=512)
    pygame.init()
    game.video.init(fullscreen=game.fullscreen, title="DOOM (Python)")
    game.video.show_fps = game.show_fps
    game.video.crt = game.crt
    pal = game.wad.cache_lump_name("PLAYPAL")
    game.video.set_palette(pal)
    game._playpal = pal
    if game.nosound:
        game.sound.enabled = False
        game.sound.music_enabled = False
    if game.nomusic:
        game.sound.music_enabled = False
    game.sound.init(game.wad)
    game.menu = Menu(game.wad, game.sound, game)
    if game.wad.check_num_for_name("TITLEPIC") >= 0:
        game.title_patch = game.wad.cache_lump_name("TITLEPIC")
    if game.wad.check_num_for_name("CREDIT") >= 0:
        game.credit_patch = game.wad.cache_lump_name("CREDIT")
    game.page_patch = game.title_patch
    game.status = StatusBar(game.wad)
    if game.record_name:
        game.demo_name = game.record_name
        game.demo_recording = True
        game.start_new_game(game.skill, game.episode, game.mapn)
    elif game.timedemo_name:
        game.timingdemo = True
        game.singledemo = True
        if not game.play_demo(game.timedemo_name):
            print(f"timedemo not found: {game.timedemo_name}")
            return 1
    elif game.playdemo_name:
        game.singledemo = True
        if not game.play_demo(game.playdemo_name):
            print(f"playdemo not found: {game.playdemo_name}")
            return 1
    elif "-warp" in argv:
        game.load_level()
    else:
        game.start_title()

    tick_ms = 1000 / TICRATE
    accum = 0.0
    last = pygame.time.get_ticks()
    while game.running:
        for ev in pygame.event.get():
            game.handle_event(ev)
        now = pygame.time.get_ticks()
        accum += now - last
        last = now
        if game.timingdemo:
            game.run_tic()
        else:
            while accum >= tick_ms:
                game.run_tic()
                accum -= tick_ms
        game.draw()
    if game.demo_recording:
        game.finish_recording()
    save_defaults(game)
    game.sound.stop_music()
    pygame.quit()
    return 0
