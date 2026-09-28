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
    BT_ATTACK,
    BT_CHANGE,
    BT_USE,
    BT_WEAPONSHIFT,
    CF_GODMODE,
    FRACUNIT,
    GS_FINALE,
    GS_INTERMISSION,
    GS_LEVEL,
    GS_TITLE,
    MF_NOCLIP,
    MF_SHOOTABLE,
    MF_SOLID,
    PST_DEAD,
    PST_LIVE,
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
from .enemy import kill_monster, tick_enemies
from .finale import Finale
from .menu import Menu
from .mobj import spawn_map_things, touch_special
from .player import (
    ANGLETURN,
    FORWARDMOVE,
    SIDEMOVE,
    Ticcmd,
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
from .sprites import draw_psprite, draw_sprites, weapon_psprite_xy
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
        self.fullscreen = False
        self.crt = False
        self.title_patch: bytes | None = None
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
        self._cheat_seq = {"iddqd": 0, "idkfa": 0, "iddt": 0}
        self.automap = Automap()

    def start_sound(self, name: str) -> None:
        self.sound.play(name)

    def touch_special(self, special, toucher) -> None:
        touch_special(self, special, toucher)

    def use_special(self, line, thing, side: int) -> None:
        if self.specials:
            self.specials.use_special(line, thing, side)

    def cross_special(self, line, side: int, thing) -> None:
        if self.specials:
            self.specials.cross_special(line, side, thing)

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
            ang = angle_to(src.x, src.y, target.x, target.y)
            thrust = damage * (FRACUNIT // 8)
            target.momx += fixed_mul(thrust, fine_cos(ang))
            target.momy += fixed_mul(thrust, fine_sin(ang))
        if target.player:
            player = target.player
            if (player.cheats & CF_GODMODE) and damage < 1000:
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
            if player.health <= 0:
                player.health = 0
                player.playerstate = PST_DEAD
                target.alive = False
                target.flags &= ~(MF_SOLID | MF_SHOOTABLE)
                self.start_sound("pldeth")
            else:
                self.start_sound("plpain")
            return
        target.health -= damage
        if target.health <= 0:
            kill_monster(target, self, source)
        else:
            self.start_sound("popain")
            if source is not None:
                target.target = source
                if getattr(target, "ai_state", "") in ("", "look"):
                    target.ai_state = "chase"
                    target.reactiontime = 0

    def load_level(self, carry: bool = False) -> None:
        assert self.res is not None
        prev = self.player if carry else None
        self.world = World()
        self.world.setup_level(self.wad, self.res, self.episode, self.mapn)
        self.specials = Specials(self.world, self.res, self.sound)
        start = self.world.player_start()
        if start is None:
            raise RuntimeError("no player 1 start")
        self.player = spawn_player(self.world, start)
        if prev is not None:
            self._carry_player(prev)
        self.player.killcount = 0
        self.player.itemcount = 0
        self.player.secretcount = 0
        self.totalkills = 0
        self.totalitems = 0
        self.totalsecret = sum(1 for s in self.world.sectors if s.special == 9)
        if not self.nomonsters:
            self.totalkills, self.totalitems = spawn_map_things(self.world, self.skill)
        self.leveltime = 0
        self.gamestate = GS_LEVEL
        self.specials.exit_requested = False
        self.specials.secret_exit = False
        self.wi = None
        self.finale = None
        self.sound.play_level_music(self.episode, self.mapn)
        self.automap.reset_level()
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

    def world_done(self) -> None:
        if self.specials and self.specials.secret_exit and self.player:
            self.player.didsecret = True
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
        self.skill = skill
        self.episode = episode
        self.mapn = mapn
        self.load_level(carry=False)

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
        try:
            ok = read_and_restore(self, slot)
        except (OSError, KeyError, TypeError, ValueError, RuntimeError):
            return False
        if not ok:
            return False
        self._st_palette = -1
        self.keys.clear()
        self.automap.reset_level()
        if self.player:
            self.player.set_message("game loaded.")
        print(f"Loaded E{self.episode}M{self.mapn}")
        return True

    def return_to_title(self) -> None:
        self.gamestate = GS_TITLE
        self.player = None
        self.world = None
        self.wi = None
        self.finale = None
        self.automap.reset_level()
        self.sound.play_title_music()
        if self.menu:
            self.menu.clear()

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
        return cmd

    def run_tic(self) -> None:
        if self.wiping:
            done = self.wipe.tick(1, self.video.fb)
            if done:
                self.wiping = False
            return
        if self.menu:
            self.menu.ticker()
        self.sound.update()
        if self.gamestate == GS_TITLE:
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
                    self.return_to_title()
            return
        if self.gamestate != GS_LEVEL or self.player is None:
            return
        if self.menu and self.menu.active:
            self.player.cmd = Ticcmd()
        else:
            self.player.cmd = self.build_ticcmd()
        player_think(self.world, self.player, self, self.leveltime)
        tick_enemies(self.world, self)
        if self.specials:
            self.specials.tick()
            if self.specials.exit_requested:
                self.start_sound("swtchx")
                self.complete_level()
                return
        self.leveltime += 1
        self.automap.ticker(self)

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
        if self.gamestate == GS_TITLE and self.title_patch:
            fill(fb, 0)
            draw_patch(fb, 0, 0, self.title_patch)
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
            self.renderer.setup_frame(mo.x, mo.y, self.player.viewz, mo.angle, self.player.extralight)
            self.renderer.render(self.world, fb)
            draw_sprites(self.renderer, self.world, fb)
            self.renderer.draw_masked()
            self._draw_weapon(fb)
        if self.status and (self.automap.active or self.renderer.screenblocks < 11):
            self.status.draw(fb, self.player, show_messages=self.show_messages)

    def _apply_palette(self) -> None:
        """ST_doPaletteStuff: red shift on damage, gold on pickup."""
        pal = 0
        p = self.player
        if p is not None and self.gamestate == GS_LEVEL:
            if p.damagecount:
                pal = (p.damagecount + 7) >> 3
                if pal >= 8:
                    pal = 7
                pal += 1
            elif p.bonuscount:
                pal = (p.bonuscount + 7) >> 3
                if pal >= 4:
                    pal = 3
                pal += 9
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

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and (mods & pygame.KMOD_ALT):
                self.video.toggle_fullscreen()
                self.fullscreen = self.video.fullscreen
                return
            uni = getattr(ev, "unicode", "") or ""
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
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.gamestate == GS_TITLE:
                    self.load_level()
            elif ev.key == pygame.K_F11:
                self.video.show_fps = not self.video.show_fps
            else:
                self._feed_cheat(uni)
        elif ev.type == pygame.KEYUP:
            self.keys.discard(ev.key)
            self.automap.responder(ev, self)

    def _feed_cheat(self, uni: str) -> None:
        """st_stuff cht_CheckCheat: type IDDQD / IDKFA with no Enter (letters only)."""
        if self.gamestate != GS_LEVEL or self.player is None:
            return
        if self.skill == SK_NIGHTMARE:
            return
        ch = (uni or "").lower()
        if len(ch) != 1 or not ch.isalpha():
            return
        for seq, pos in list(self._cheat_seq.items()):
            expect = seq[pos] if pos < len(seq) else ""
            if ch == expect:
                pos += 1
                if pos >= len(seq):
                    self._cheat_seq[seq] = 0
                    if seq == "iddqd":
                        self._cheat_god()
                    elif seq == "idkfa":
                        self._cheat_idkfa()
                    elif seq == "iddt":
                        if self.automap.active:
                            self.automap.cycle_iddt()
                else:
                    self._cheat_seq[seq] = pos
            else:
                self._cheat_seq[seq] = 1 if ch == seq[0] else 0

    def _cheat_god(self) -> None:
        p = self.player
        p.cheats ^= CF_GODMODE
        if p.cheats & CF_GODMODE:
            p.health = 100
            if p.mo:
                p.mo.health = 100
            p.set_message("Degreelessness Mode On")
        else:
            p.set_message("Degreelessness Mode Off")

    def _cheat_idkfa(self) -> None:
        p = self.player
        p.armorpoints = 200
        p.armortype = 2
        for i in range(len(p.weaponowned)):
            p.weaponowned[i] = True
        for i in range(len(p.ammo)):
            p.ammo[i] = p.maxammo[i]
        p.cards = [True] * 6
        p.set_message("Very Happy Ammo Added")


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
        if a.lower().endswith(".wad") and not a.startswith("-"):
            iwad = a
        i += 1
    return iwad


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv
    game = Game()
    iwad_arg = parse_args(argv, game)
    path = find_iwad(iwad_arg)
    game.iwad_path = path
    print(f"IWAD: {path}")
    game.wad.add_file(path)
    init_tables()
    game.res = Resources(game.wad)
    game.res.init()
    game.renderer = Renderer(game.res)
    game.apply_view_size()
    pygame.mixer.pre_init(frequency=11025, size=-16, channels=1, buffer=512)
    pygame.init()
    game.video.init(fullscreen=game.fullscreen, title="DOOM (Python)")
    game.video.show_fps = game.show_fps
    game.video.crt = game.crt
    pal = game.wad.cache_lump_name("PLAYPAL")
    game.video.set_palette(pal)
    game._playpal = pal
    game.sound.init(game.wad)
    game.menu = Menu(game.wad, game.sound, game)
    if game.wad.check_num_for_name("TITLEPIC") >= 0:
        game.title_patch = game.wad.cache_lump_name("TITLEPIC")
    game.status = StatusBar(game.wad)
    if "-warp" in argv:
        game.load_level()
    else:
        game.gamestate = GS_TITLE
        game.start_sound("swtchn")
        game.sound.play_title_music()

    tick_ms = 1000 / TICRATE
    accum = 0.0
    last = pygame.time.get_ticks()
    while game.running:
        for ev in pygame.event.get():
            game.handle_event(ev)
        now = pygame.time.get_ticks()
        accum += now - last
        last = now
        while accum >= tick_ms:
            game.run_tic()
            accum -= tick_ms
        game.draw()
    game.sound.stop_music()
    pygame.quit()
    return 0
