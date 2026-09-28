"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Intermission stats (wi_stuff.prg, single-player).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame

from .defs import SCREENHEIGHT, SCREENWIDTH, TICRATE
from .v_video import draw_patch, patch_size

WI_TITLEY = 2
SP_STATSX = 50
SP_STATSY = 50
SP_TIMEX = 16
SP_TIMEY = SCREENHEIGHT - 32
SHOWNEXTLOCDELAY = 4
NO_STATE = -1
STAT_COUNT = 0
SHOW_NEXT_LOC = 1
ANIM_ALWAYS = 0
ANIM_LEVEL = 2

PARS = (
    (0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (0, 30, 75, 120, 90, 165, 180, 180, 30, 165),
    (0, 90, 90, 90, 120, 90, 360, 240, 30, 170),
    (0, 90, 45, 90, 150, 90, 90, 165, 30, 135),
)
CPARS = (
    30, 90, 120, 120, 90, 150, 120, 120, 270, 90,
    210, 150, 150, 150, 210, 150, 420, 150, 210, 150,
    240, 150, 180, 150, 150, 300, 330, 420, 300, 180,
    120, 30,
)

LNODES = (
    ((185, 164), (148, 143), (69, 122), (209, 102), (116, 89), (166, 55), (71, 56), (135, 29), (71, 24)),
    ((254, 25), (97, 50), (188, 64), (128, 78), (214, 92), (133, 130), (208, 136), (148, 140), (235, 158)),
    ((156, 168), (48, 154), (174, 95), (265, 75), (130, 48), (279, 23), (198, 48), (140, 25), (281, 136)),
)

# (type, period, nanims, x, y, data1)
ANIMS = (
    (
        (ANIM_ALWAYS, TICRATE // 3, 3, 224, 104, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 184, 160, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 112, 136, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 72, 112, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 88, 96, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 64, 48, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 192, 40, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 136, 16, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 80, 16, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 64, 24, 0),
    ),
    (
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 1),
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 2),
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 3),
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 4),
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 5),
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 6),
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 7),
        (ANIM_ALWAYS, TICRATE // 3, 3, 192, 144, 8),
        (ANIM_LEVEL, TICRATE // 3, 1, 128, 136, 8),
    ),
    (
        (ANIM_ALWAYS, TICRATE // 3, 3, 104, 168, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 40, 136, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 160, 96, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 104, 80, 0),
        (ANIM_ALWAYS, TICRATE // 3, 3, 120, 32, 0),
        (ANIM_ALWAYS, TICRATE // 4, 3, 40, 0, 0),
    ),
)


def partime(episode: int, mapn: int, commercial: bool) -> int:
    if commercial:
        i = max(0, min(len(CPARS) - 1, mapn - 1))
        return TICRATE * CPARS[i]
    if 1 <= episode <= 3 and 1 <= mapn <= 9:
        return TICRATE * PARS[episode][mapn]
    if 1 <= mapn <= 9:
        return TICRATE * CPARS[min(len(CPARS) - 1, mapn)]
    return TICRATE * 30


def _pct(value: int, maximum: int) -> int:
    return (value * 100) // max(1, maximum)


@dataclass
class Anim:
    type: int
    period: int
    nanims: int
    x: int
    y: int
    data1: int
    patches: list = field(default_factory=list)
    ctr: int = -1
    nexttic: int = 0


@dataclass
class WbStart:
    epsd: int
    last: int
    next: int
    maxkills: int
    maxitems: int
    maxsecret: int
    partime: int
    skills: int
    sitems: int
    ssecret: int
    stime: int
    didsecret: bool
    commercial: bool


class Intermission:
    def __init__(self, game, wbs: WbStart) -> None:
        self.game = game
        self.wbs = wbs
        self.state = STAT_COUNT
        self.accelerate = 0
        self.sp_state = 1
        self.cnt_kills = -1
        self.cnt_items = -1
        self.cnt_secret = -1
        self.cnt_time = -1
        self.cnt_par = -1
        self.cnt_pause = TICRATE
        self.cnt = 0
        self.bcnt = 0
        self.snl_pointeron = False
        self.done = False
        self.anims: list[Anim] = []
        wad = game.wad
        self._p = {}
        names = {
            "finished": "WIF",
            "entering": "WIENTER",
            "kills": "WIOSTK",
            "items": "WIOSTI",
            "sp_secret": "WISCRT2",
            "percent": "WIPCNT",
            "colon": "WICOLON",
            "time": "WITIME",
            "par": "WIPAR",
            "sucks": "WISUCKS",
            "minus": "WIMINUS",
            "splat": "WISPLAT",
            "yah0": "WIURH0",
            "yah1": "WIURH1",
        }
        for k, lump in names.items():
            self._p[k] = self._lump(wad, lump)
        self.num = [self._lump(wad, f"WINUM{i}") for i in range(10)]
        if wbs.commercial:
            bg = "INTERPIC"
        elif wbs.epsd == 3:
            bg = "INTERPIC"
        else:
            bg = f"WIMAP{wbs.epsd}"
        self.background = self._lump(wad, bg) or self._lump(wad, "INTERPIC")
        nmaps = 32 if wbs.commercial else 9
        self.lnames = []
        for i in range(nmaps):
            if wbs.commercial:
                name = f"CWILV{i:02d}"
            else:
                name = f"WILV{wbs.epsd}{i}"
            self.lnames.append(self._lump(wad, name))
        if not wbs.commercial and wbs.epsd < 3:
            for j, spec in enumerate(ANIMS[wbs.epsd]):
                a = Anim(*spec)
                for i in range(a.nanims):
                    if wbs.epsd == 1 and j == 8:
                        a.patches.append(self.anims[4].patches[i] if len(self.anims) > 4 else None)
                    else:
                        a.patches.append(self._lump(wad, f"WIA{wbs.epsd}{j:02d}{i:02d}"))
                self.anims.append(a)
        self._init_animated()

    def _lump(self, wad, name: str):
        n = wad.check_num_for_name(name)
        if n < 0:
            return None
        return wad.cache_lump_num(n)

    def _init_animated(self) -> None:
        if self.wbs.commercial or self.wbs.epsd > 2:
            return
        for a in self.anims:
            a.ctr = -1
            if a.type == ANIM_ALWAYS:
                a.nexttic = self.bcnt + 1 + random.randrange(max(1, a.period))
            else:
                a.nexttic = self.bcnt + 1

    def _update_animated(self) -> None:
        if self.wbs.commercial or self.wbs.epsd > 2:
            return
        for i, a in enumerate(self.anims):
            if self.bcnt != a.nexttic:
                continue
            if a.type == ANIM_ALWAYS:
                a.ctr += 1
                if a.ctr >= a.nanims:
                    a.ctr = 0
                a.nexttic = self.bcnt + a.period
            elif a.type == ANIM_LEVEL:
                if not (self.state == STAT_COUNT and i == 7) and self.wbs.next == a.data1:
                    a.ctr += 1
                    if a.ctr == a.nanims:
                        a.ctr -= 1
                    a.nexttic = self.bcnt + a.period

    def ticker(self) -> None:
        self.bcnt += 1
        if self.bcnt == 1:
            if self.wbs.commercial:
                self.game.sound.change_music("dm2int", looping=True)
            else:
                self.game.sound.change_music("inter", looping=True)
        self._check_accelerate()
        if self.state == STAT_COUNT:
            self._update_stats()
        elif self.state == SHOW_NEXT_LOC:
            self._update_show_next()
        elif self.state == NO_STATE:
            self._update_no_state()

    def _check_accelerate(self) -> None:
        if self.game.menu and self.game.menu.active:
            return
        attack = pygame.K_LCTRL in self.game.keys or pygame.K_RCTRL in self.game.keys
        use = pygame.K_SPACE in self.game.keys or pygame.K_e in self.game.keys
        enter = pygame.K_RETURN in self.game.keys or pygame.K_KP_ENTER in self.game.keys
        p = self.game.player
        if p is None:
            if attack or use or enter:
                self.accelerate = 1
            return
        if attack:
            if not p.attackdown:
                self.accelerate = 1
            p.attackdown = True
        else:
            p.attackdown = False
        if use or enter:
            if not p.usedown:
                self.accelerate = 1
            p.usedown = True
        else:
            if not use:
                p.usedown = False

    def _update_stats(self) -> None:
        w = self.wbs
        self._update_animated()
        if self.accelerate and self.sp_state != 10:
            self.accelerate = 0
            self.cnt_kills = _pct(w.skills, w.maxkills)
            self.cnt_items = _pct(w.sitems, w.maxitems)
            self.cnt_secret = _pct(w.ssecret, w.maxsecret)
            self.cnt_time = w.stime // TICRATE
            self.cnt_par = w.partime // TICRATE
            self.game.start_sound("barexp")
            self.sp_state = 10
        if self.sp_state == 2:
            self.cnt_kills += 2
            if (self.bcnt & 3) == 0:
                self.game.start_sound("pistol")
            target = _pct(w.skills, w.maxkills)
            if self.cnt_kills >= target:
                self.cnt_kills = target
                self.game.start_sound("barexp")
                self.sp_state += 1
        elif self.sp_state == 4:
            self.cnt_items += 2
            if (self.bcnt & 3) == 0:
                self.game.start_sound("pistol")
            target = _pct(w.sitems, w.maxitems)
            if self.cnt_items >= target:
                self.cnt_items = target
                self.game.start_sound("barexp")
                self.sp_state += 1
        elif self.sp_state == 6:
            self.cnt_secret += 2
            if (self.bcnt & 3) == 0:
                self.game.start_sound("pistol")
            target = _pct(w.ssecret, w.maxsecret)
            if self.cnt_secret >= target:
                self.cnt_secret = target
                self.game.start_sound("barexp")
                self.sp_state += 1
        elif self.sp_state == 8:
            if (self.bcnt & 3) == 0:
                self.game.start_sound("pistol")
            self.cnt_time += 3
            ttime = w.stime // TICRATE
            if self.cnt_time >= ttime:
                self.cnt_time = ttime
            self.cnt_par += 3
            ptime = w.partime // TICRATE
            if self.cnt_par >= ptime:
                self.cnt_par = ptime
                if self.cnt_time >= ttime:
                    self.game.start_sound("barexp")
                    self.sp_state += 1
        elif self.sp_state == 10:
            if self.accelerate:
                self.game.start_sound("wpnup")
                if self.wbs.commercial:
                    self._init_no_state()
                else:
                    self._init_show_next()
        elif self.sp_state & 1:
            self.cnt_pause -= 1
            if self.cnt_pause == 0:
                self.sp_state += 1
                self.cnt_pause = TICRATE
                if self.sp_state == 2:
                    self.cnt_kills = 0
                elif self.sp_state == 4:
                    self.cnt_items = 0
                elif self.sp_state == 6:
                    self.cnt_secret = 0
                elif self.sp_state == 8:
                    self.cnt_time = 0
                    self.cnt_par = 0

    def _init_show_next(self) -> None:
        self.state = SHOW_NEXT_LOC
        self.accelerate = 0
        self.cnt = SHOWNEXTLOCDELAY * TICRATE
        self._init_animated()

    def _update_show_next(self) -> None:
        self._update_animated()
        self.cnt -= 1
        if self.cnt == 0 or self.accelerate:
            self._init_no_state()
        else:
            self.snl_pointeron = (self.cnt & 31) < 20

    def _init_no_state(self) -> None:
        self.state = NO_STATE
        self.accelerate = 0
        self.cnt = 10

    def _update_no_state(self) -> None:
        self._update_animated()
        self.cnt -= 1
        if self.cnt == 0:
            self.done = True

    def draw(self, fb: bytearray) -> None:
        if self.state == STAT_COUNT:
            self._draw_stats(fb)
        else:
            self._draw_show_next(fb)

    def _draw_bg(self, fb: bytearray) -> None:
        if self.background:
            draw_patch(fb, 0, 0, self.background)
        self._draw_animated(fb)

    def _draw_animated(self, fb: bytearray) -> None:
        if self.wbs.commercial or self.wbs.epsd > 2:
            return
        for a in self.anims:
            if a.ctr >= 0 and a.ctr < len(a.patches) and a.patches[a.ctr]:
                draw_patch(fb, a.x, a.y, a.patches[a.ctr])

    def _pw(self, patch) -> int:
        if not patch:
            return 8
        w, _h, _l, _t = patch_size(patch)
        return w

    def _ph(self, patch) -> int:
        if not patch:
            return 16
        _w, h, _l, _t = patch_size(patch)
        return h

    def _draw_num(self, fb, x: int, y: int, n: int, digits: int) -> int:
        fontw = self._pw(self.num[0]) if self.num[0] else 8
        if digits < 0:
            if n == 0:
                digits = 1
            else:
                digits = 0
                temp = abs(n)
                while temp:
                    temp //= 10
                    digits += 1
        neg = n < 0
        if neg:
            n = -n
        while digits > 0:
            digits -= 1
            x -= fontw
            d = n % 10
            if self.num[d]:
                draw_patch(fb, x, y, self.num[d])
            n //= 10
        if neg and self._p.get("minus"):
            x -= 8
            draw_patch(fb, x, y, self._p["minus"])
        return x

    def _draw_percent(self, fb, x: int, y: int, value: int) -> None:
        if value < 0:
            return
        p = self._p.get("percent")
        if p:
            draw_patch(fb, x, y, p)
        self._draw_num(fb, x, y, value, -1)

    def _draw_time(self, fb, x: int, y: int, t: int) -> None:
        if t < 0:
            return
        if t > 61 * 59:
            sucks = self._p.get("sucks")
            if sucks:
                draw_patch(fb, x - self._pw(sucks), y, sucks)
            return
        colon = self._p.get("colon")
        div = 1
        while True:
            n = (t // div) % 60
            x = self._draw_num(fb, x, y, n, 2) - (self._pw(colon) if colon else 0)
            div *= 60
            if div == 60 or t // div:
                if colon:
                    draw_patch(fb, x, y, colon)
            if t // div == 0:
                break

    def _draw_lf(self, fb: bytearray) -> None:
        y = WI_TITLEY
        if self.wbs.last < len(self.lnames) and self.lnames[self.wbs.last]:
            patch = self.lnames[self.wbs.last]
            draw_patch(fb, (SCREENWIDTH - self._pw(patch)) // 2, y, patch)
            y += (5 * self._ph(patch)) // 4
        fin = self._p.get("finished")
        if fin:
            draw_patch(fb, (SCREENWIDTH - self._pw(fin)) // 2, y, fin)

    def _draw_el(self, fb: bytearray) -> None:
        y = WI_TITLEY
        ent = self._p.get("entering")
        if ent:
            draw_patch(fb, (SCREENWIDTH - self._pw(ent)) // 2, y, ent)
            y += (5 * self._ph(ent)) // 4
        if self.wbs.next < len(self.lnames) and self.lnames[self.wbs.next]:
            patch = self.lnames[self.wbs.next]
            draw_patch(fb, (SCREENWIDTH - self._pw(patch)) // 2, y, patch)

    def _draw_on_lnode(self, fb, n: int, patches: list) -> None:
        if self.wbs.epsd >= len(LNODES) or n >= len(LNODES[self.wbs.epsd]):
            return
        node = LNODES[self.wbs.epsd][n]
        for patch in patches:
            if not patch:
                continue
            w, h, left, top = patch_size(patch)
            left_x = node[0] - left
            top_y = node[1] - top
            if left_x >= 0 and left_x + w < SCREENWIDTH and top_y >= 0 and top_y + h < SCREENHEIGHT:
                draw_patch(fb, node[0], node[1], patch)
                return

    def _draw_stats(self, fb: bytearray) -> None:
        self._draw_bg(fb)
        self._draw_lf(fb)
        lh = (3 * self._ph(self.num[0])) // 2 if self.num[0] else 24
        kills = self._p.get("kills")
        items = self._p.get("items")
        secret = self._p.get("sp_secret")
        if kills:
            draw_patch(fb, SP_STATSX, SP_STATSY, kills)
        self._draw_percent(fb, SCREENWIDTH - SP_STATSX, SP_STATSY, self.cnt_kills)
        if items:
            draw_patch(fb, SP_STATSX, SP_STATSY + lh, items)
        self._draw_percent(fb, SCREENWIDTH - SP_STATSX, SP_STATSY + lh, self.cnt_items)
        if secret:
            draw_patch(fb, SP_STATSX, SP_STATSY + 2 * lh, secret)
        self._draw_percent(fb, SCREENWIDTH - SP_STATSX, SP_STATSY + 2 * lh, self.cnt_secret)
        timep = self._p.get("time")
        if timep:
            draw_patch(fb, SP_TIMEX, SP_TIMEY, timep)
        self._draw_time(fb, SCREENWIDTH // 2 - SP_TIMEX, SP_TIMEY, self.cnt_time)
        if self.wbs.epsd < 3:
            par = self._p.get("par")
            if par:
                draw_patch(fb, SCREENWIDTH // 2 + SP_TIMEX, SP_TIMEY, par)
            self._draw_time(fb, SCREENWIDTH - SP_TIMEX, SP_TIMEY, self.cnt_par)

    def _draw_show_next(self, fb: bytearray) -> None:
        self._draw_bg(fb)
        if self.state == NO_STATE:
            self.snl_pointeron = True
        if not self.wbs.commercial:
            if self.wbs.epsd > 2:
                self._draw_el(fb)
                return
            last = self.wbs.next - 1 if self.wbs.last == 8 else self.wbs.last
            splat = [self._p.get("splat")]
            yah = [self._p.get("yah0"), self._p.get("yah1")]
            for i in range(max(0, last + 1)):
                self._draw_on_lnode(fb, i, splat)
            if self.wbs.didsecret:
                self._draw_on_lnode(fb, 8, splat)
            if self.snl_pointeron:
                self._draw_on_lnode(fb, self.wbs.next, yah)
        if not self.wbs.commercial or self.wbs.next != 30:
            self._draw_el(fb)
