"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Automap (am_map.prg). Tab toggles; walls use ML_MAPPED like vanilla.
"""

from __future__ import annotations

import pygame

from .compat import as_u32, fixed_div, fixed_mul, shar, ushr
from .defs import (
    ANGLETOFINESHIFT,
    FRACUNIT,
    GS_LEVEL,
    ML_DONTDRAW,
    ML_MAPPED,
    ML_SECRET,
    PLAYER_RADIUS,
    SBARHEIGHT,
    SCREENHEIGHT,
    SCREENWIDTH,
)
from .tables import finecosine, finesine
from .v_video import draw_patch

REDS = 256 - 5 * 16
REDRANGE = 16
GREENS = 7 * 16
GRAYS = 6 * 16
BROWNS = 4 * 16
YELLOWS = 256 - 32 + 7
BLACK = 0
WHITE = 256 - 47
BACKGROUND = BLACK
WALLCOLORS = REDS
WALLRANGE = REDRANGE
TSWALLCOLORS = GRAYS
FDWALLCOLORS = BROWNS
CDWALLCOLORS = YELLOWS
THINGCOLORS = GREENS
SECRETWALLCOLORS = WALLCOLORS
GRIDCOLORS = 104
XHAIRCOLORS = GRAYS
LINE_NEVERSEE = ML_DONTDRAW

INITSCALEMTOF = 13107
F_PANINC = 4
M_ZOOMIN = 66846
M_ZOOMOUT = 64250
AM_NUMMARKPOINTS = 10
MAPBLOCKUNITS = 128
INT_MAX = 0x7FFFFFFF

OC_LEFT = 1
OC_RIGHT = 2
OC_BOTTOM = 4
OC_TOP = 8


def _mline(ax: int, ay: int, bx: int, by: int) -> tuple[tuple[int, int], tuple[int, int]]:
    return ((ax, ay), (bx, by))


def _player_arrow() -> list[tuple[tuple[int, int], tuple[int, int]]]:
    n_r = int((8 * PLAYER_RADIUS) / 7)
    q = n_r // 4
    e = n_r // 8
    return [
        _mline(-n_r + e, 0, n_r, 0),
        _mline(n_r, 0, n_r - n_r // 2, q),
        _mline(n_r, 0, n_r - n_r // 2, -q),
        _mline(-n_r + e, 0, -n_r - e, q),
        _mline(-n_r + e, 0, -n_r - e, -q),
        _mline(-n_r + 3 * e, 0, -n_r + e, q),
        _mline(-n_r + 3 * e, 0, -n_r + e, -q),
    ]


def _thin_triangle() -> list[tuple[tuple[int, int], tuple[int, int]]]:
    return [
        _mline(int(-0.5 * FRACUNIT), int(-0.7 * FRACUNIT), FRACUNIT, 0),
        _mline(FRACUNIT, 0, int(-0.5 * FRACUNIT), int(0.7 * FRACUNIT)),
        _mline(int(-0.5 * FRACUNIT), int(0.7 * FRACUNIT), int(-0.5 * FRACUNIT), int(-0.7 * FRACUNIT)),
    ]


class Automap:
    def __init__(self) -> None:
        self.active = False
        self.cheating = 0
        self.grid = 0
        self.followplayer = 1
        self.stopped = True
        self.lastlevel = -1
        self.lastepisode = -1
        self.bigstate = 0
        self.lightlev = 0
        self.amclock = 0
        self.f_x = 0
        self.f_y = 0
        self.f_w = SCREENWIDTH
        self.f_h = SCREENHEIGHT - SBARHEIGHT
        self.m_x = 0
        self.m_y = 0
        self.m_x2 = 0
        self.m_y2 = 0
        self.m_w = 0
        self.m_h = 0
        self.min_x = 0
        self.min_y = 0
        self.max_x = 0
        self.max_y = 0
        self.min_scale_mtof = FRACUNIT
        self.max_scale_mtof = FRACUNIT
        self.scale_mtof = INITSCALEMTOF
        self.scale_ftom = FRACUNIT
        self.old_m_x = 0
        self.old_m_y = 0
        self.old_m_w = 0
        self.old_m_h = 0
        self.f_oldloc_x = INT_MAX
        self.f_oldloc_y = 0
        self.m_paninc_x = 0
        self.m_paninc_y = 0
        self.mtof_zoommul = FRACUNIT
        self.ftom_zoommul = FRACUNIT
        self.player_arrow = _player_arrow()
        self.thintriangle_guy = _thin_triangle()
        self.marknums: list[bytes | None] = [None] * 10
        self.markpoints = [(-1, -1)] * AM_NUMMARKPOINTS
        self.markpointnum = 0
        self._fb: bytearray | None = None
        self._clip = [0, 0, 0, 0]

    def ftom(self, x: int) -> int:
        return fixed_mul(x * FRACUNIT, self.scale_ftom)

    def mtof(self, x: int) -> int:
        return shar(fixed_mul(x, self.scale_mtof), 16)

    def cxmtof(self, x: int) -> int:
        return self.f_x + self.mtof(x - self.m_x)

    def cymtof(self, y: int) -> int:
        return self.f_y + (self.f_h - self.mtof(y - self.m_y))

    def start(self, game) -> None:
        if not self.stopped:
            self.stop()
        self.stopped = False
        if self.lastlevel != game.mapn or self.lastepisode != game.episode:
            self._level_init(game)
            self.lastlevel = game.mapn
            self.lastepisode = game.episode
        self._init_variables(game)
        self._load_pics(game.wad)
        self.active = True

    def stop(self) -> None:
        self.active = False
        self.stopped = True
        self.m_paninc_x = 0
        self.m_paninc_y = 0
        self.mtof_zoommul = FRACUNIT
        self.ftom_zoommul = FRACUNIT
        self.bigstate = 0

    def reset_level(self) -> None:
        if self.active:
            self.stop()
        self.lastlevel = -1
        self.lastepisode = -1
        self.cheating = 0

    def ticker(self, game) -> None:
        if not self.active:
            return
        self.amclock += 1
        if self.followplayer:
            self._do_follow_player(game)
        if self.ftom_zoommul != FRACUNIT:
            self._change_window_scale()
        if self.m_paninc_x or self.m_paninc_y:
            self._change_window_loc()

    def drawer(self, fb: bytearray, game) -> None:
        if not self.active:
            return
        self._fb = fb
        self._clear_fb(BACKGROUND)
        if self.grid:
            self._draw_grid(game)
        self._draw_walls(game)
        self._draw_players(game)
        if self.cheating == 2:
            self._draw_things(game)
        self._draw_crosshair()
        self._draw_marks()
        self._fb = None

    def responder(self, ev: pygame.event.Event, game) -> bool:
        if game.gamestate != GS_LEVEL or game.player is None or game.world is None:
            return False
        if ev.type == pygame.KEYDOWN:
            if not self.active:
                if ev.key == pygame.K_TAB:
                    self.start(game)
                    return True
                return False
            key = ev.key
            if key == pygame.K_RIGHT:
                if not self.followplayer:
                    self.m_paninc_x = self.ftom(F_PANINC)
                    return True
                return False
            if key == pygame.K_LEFT:
                if not self.followplayer:
                    self.m_paninc_x = -self.ftom(F_PANINC)
                    return True
                return False
            if key == pygame.K_UP:
                if not self.followplayer:
                    self.m_paninc_y = self.ftom(F_PANINC)
                    return True
                return False
            if key == pygame.K_DOWN:
                if not self.followplayer:
                    self.m_paninc_y = -self.ftom(F_PANINC)
                    return True
                return False
            if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.mtof_zoommul = M_ZOOMOUT
                self.ftom_zoommul = M_ZOOMIN
                return True
            plus_keys = {pygame.K_EQUALS, pygame.K_KP_PLUS}
            if hasattr(pygame, "K_PLUS"):
                plus_keys.add(pygame.K_PLUS)
            if key in plus_keys:
                self.mtof_zoommul = M_ZOOMIN
                self.ftom_zoommul = M_ZOOMOUT
                return True
            if key == pygame.K_TAB:
                self.stop()
                return True
            if key == pygame.K_0:
                self.bigstate = 0 if self.bigstate else 1
                if self.bigstate:
                    self._save_scale_and_loc()
                    self._min_out_window_scale()
                else:
                    self._restore_scale_and_loc(game)
                return True
            if key == pygame.K_f:
                self.followplayer = 0 if self.followplayer else 1
                self.f_oldloc_x = INT_MAX
                game.player.set_message(
                    "Follow Mode ON" if self.followplayer else "Follow Mode OFF"
                )
                return True
            if key == pygame.K_g:
                self.grid = 0 if self.grid else 1
                game.player.set_message("Grid ON" if self.grid else "Grid OFF")
                return True
            if key == pygame.K_m:
                game.player.set_message(f"Marked Spot {self.markpointnum}")
                self._add_mark()
                return True
            if key == pygame.K_c:
                self._clear_marks()
                game.player.set_message("All Marks Cleared")
                return True
            return False
        if ev.type == pygame.KEYUP and self.active:
            key = ev.key
            if key in (pygame.K_RIGHT, pygame.K_LEFT) and not self.followplayer:
                self.m_paninc_x = 0
            elif key in (pygame.K_UP, pygame.K_DOWN) and not self.followplayer:
                self.m_paninc_y = 0
            elif key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.mtof_zoommul = FRACUNIT
                self.ftom_zoommul = FRACUNIT
            elif hasattr(pygame, "K_PLUS") and key == pygame.K_PLUS:
                self.mtof_zoommul = FRACUNIT
                self.ftom_zoommul = FRACUNIT
        return False

    def cycle_iddt(self) -> None:
        self.cheating = (self.cheating + 1) % 3

    def _level_init(self, game) -> None:
        self.f_x = 0
        self.f_y = 0
        self.f_w = SCREENWIDTH
        self.f_h = SCREENHEIGHT - SBARHEIGHT
        self._clear_marks()
        self._find_min_max(game.world)
        self.scale_mtof = fixed_div(self.min_scale_mtof, int(0.7 * FRACUNIT))
        if self.scale_mtof > self.max_scale_mtof:
            self.scale_mtof = self.min_scale_mtof
        self.scale_ftom = fixed_div(FRACUNIT, self.scale_mtof)

    def _init_variables(self, game) -> None:
        self.active = True
        self.f_oldloc_x = INT_MAX
        self.amclock = 0
        self.lightlev = 0
        self.m_paninc_x = 0
        self.m_paninc_y = 0
        self.ftom_zoommul = FRACUNIT
        self.mtof_zoommul = FRACUNIT
        self.m_w = self.ftom(self.f_w)
        self.m_h = self.ftom(self.f_h)
        mo = game.player.mo
        self.m_x = mo.x - self.m_w // 2
        self.m_y = mo.y - self.m_h // 2
        self._change_window_loc()
        self.old_m_x = self.m_x
        self.old_m_y = self.m_y
        self.old_m_w = self.m_w
        self.old_m_h = self.m_h

    def _load_pics(self, wad) -> None:
        for i in range(10):
            n = wad.check_num_for_name(f"AMMNUM{i}")
            self.marknums[i] = wad.cache_lump_num(n) if n >= 0 else None

    def _clear_marks(self) -> None:
        self.markpoints = [(-1, -1)] * AM_NUMMARKPOINTS
        self.markpointnum = 0

    def _add_mark(self) -> None:
        self.markpoints[self.markpointnum] = (
            self.m_x + self.m_w // 2,
            self.m_y + self.m_h // 2,
        )
        self.markpointnum = (self.markpointnum + 1) % AM_NUMMARKPOINTS

    def _find_min_max(self, world) -> None:
        self.min_x = INT_MAX
        self.min_y = INT_MAX
        self.max_x = -INT_MAX
        self.max_y = -INT_MAX
        for v in world.vertexes:
            if v.x < self.min_x:
                self.min_x = v.x
            elif v.x > self.max_x:
                self.max_x = v.x
            if v.y < self.min_y:
                self.min_y = v.y
            elif v.y > self.max_y:
                self.max_y = v.y
        max_w = self.max_x - self.min_x
        max_h = self.max_y - self.min_y
        if max_w <= 0:
            max_w = FRACUNIT
        if max_h <= 0:
            max_h = FRACUNIT
        a = fixed_div(self.f_w * FRACUNIT, max_w)
        b = fixed_div(self.f_h * FRACUNIT, max_h)
        self.min_scale_mtof = a if a < b else b
        self.max_scale_mtof = fixed_div(self.f_h * FRACUNIT, 2 * PLAYER_RADIUS)

    def _activate_new_scale(self) -> None:
        self.m_x += self.m_w // 2
        self.m_y += self.m_h // 2
        self.m_w = self.ftom(self.f_w)
        self.m_h = self.ftom(self.f_h)
        self.m_x -= self.m_w // 2
        self.m_y -= self.m_h // 2
        self.m_x2 = self.m_x + self.m_w
        self.m_y2 = self.m_y + self.m_h

    def _save_scale_and_loc(self) -> None:
        self.old_m_x = self.m_x
        self.old_m_y = self.m_y
        self.old_m_w = self.m_w
        self.old_m_h = self.m_h

    def _restore_scale_and_loc(self, game) -> None:
        self.m_w = self.old_m_w
        self.m_h = self.old_m_h
        if not self.followplayer:
            self.m_x = self.old_m_x
            self.m_y = self.old_m_y
        else:
            mo = game.player.mo
            self.m_x = mo.x - self.m_w // 2
            self.m_y = mo.y - self.m_h // 2
        self.m_x2 = self.m_x + self.m_w
        self.m_y2 = self.m_y + self.m_h
        self.scale_mtof = fixed_div(self.f_w * FRACUNIT, self.m_w)
        self.scale_ftom = fixed_div(FRACUNIT, self.scale_mtof)

    def _min_out_window_scale(self) -> None:
        self.scale_mtof = self.min_scale_mtof
        self.scale_ftom = fixed_div(FRACUNIT, self.scale_mtof)
        self._activate_new_scale()

    def _max_out_window_scale(self) -> None:
        self.scale_mtof = self.max_scale_mtof
        self.scale_ftom = fixed_div(FRACUNIT, self.scale_mtof)
        self._activate_new_scale()

    def _change_window_scale(self) -> None:
        self.scale_mtof = fixed_mul(self.scale_mtof, self.mtof_zoommul)
        self.scale_ftom = fixed_div(FRACUNIT, self.scale_mtof)
        if self.scale_mtof < self.min_scale_mtof:
            self._min_out_window_scale()
        elif self.scale_mtof > self.max_scale_mtof:
            self._max_out_window_scale()
        else:
            self._activate_new_scale()

    def _change_window_loc(self) -> None:
        if self.m_paninc_x or self.m_paninc_y:
            self.followplayer = 0
            self.f_oldloc_x = INT_MAX
        self.m_x += self.m_paninc_x
        self.m_y += self.m_paninc_y
        if self.m_x + self.m_w // 2 > self.max_x:
            self.m_x = self.max_x - self.m_w // 2
        elif self.m_x + self.m_w // 2 < self.min_x:
            self.m_x = self.min_x - self.m_w // 2
        if self.m_y + self.m_h // 2 > self.max_y:
            self.m_y = self.max_y - self.m_h // 2
        elif self.m_y + self.m_h // 2 < self.min_y:
            self.m_y = self.min_y - self.m_h // 2
        self.m_x2 = self.m_x + self.m_w
        self.m_y2 = self.m_y + self.m_h

    def _do_follow_player(self, game) -> None:
        mo = game.player.mo
        if self.f_oldloc_x != mo.x or self.f_oldloc_y != mo.y:
            self.m_x = self.ftom(self.mtof(mo.x)) - self.m_w // 2
            self.m_y = self.ftom(self.mtof(mo.y)) - self.m_h // 2
            self.m_x2 = self.m_x + self.m_w
            self.m_y2 = self.m_y + self.m_h
            self.f_oldloc_x = mo.x
            self.f_oldloc_y = mo.y

    def _clear_fb(self, color: int) -> None:
        fb = self._fb
        if fb is None:
            return
        row = bytes([color & 0xFF]) * self.f_w
        n = self.f_w * self.f_h
        fb[:n] = row * self.f_h

    def _put_dot(self, xx: int, yy: int, cc: int) -> None:
        fb = self._fb
        if fb is None:
            return
        if 0 <= xx < self.f_w and 0 <= yy < self.f_h:
            fb[yy * self.f_w + xx] = cc & 0xFF

    def _draw_fline(self, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
        if not (0 <= x0 < self.f_w and 0 <= y0 < self.f_h and 0 <= x1 < self.f_w and 0 <= y1 < self.f_h):
            return
        dx = x1 - x0
        ax = 2 * (dx if dx >= 0 else -dx)
        sx = -1 if dx < 0 else 1
        dy = y1 - y0
        ay = 2 * (dy if dy >= 0 else -dy)
        sy = -1 if dy < 0 else 1
        x, y = x0, y0
        if ax > ay:
            d = ay - ax // 2
            while True:
                self._put_dot(x, y, color)
                if x == x1:
                    return
                if d >= 0:
                    y += sy
                    d -= ax
                x += sx
                d += ay
        else:
            d = ax - ay // 2
            while True:
                self._put_dot(x, y, color)
                if y == y1:
                    return
                if d >= 0:
                    x += sx
                    d -= ay
                y += sy
                d += ax

    def _clip_mline(self, ax: int, ay: int, bx: int, by: int) -> bool:
        out1 = 0
        out2 = 0
        if ay > self.m_y2:
            out1 = OC_TOP
        elif ay < self.m_y:
            out1 = OC_BOTTOM
        if by > self.m_y2:
            out2 = OC_TOP
        elif by < self.m_y:
            out2 = OC_BOTTOM
        if out1 & out2:
            return False
        if ax < self.m_x:
            out1 |= OC_LEFT
        elif ax > self.m_x2:
            out1 |= OC_RIGHT
        if bx < self.m_x:
            out2 |= OC_LEFT
        elif bx > self.m_x2:
            out2 |= OC_RIGHT
        if out1 & out2:
            return False
        fx0 = self.cxmtof(ax)
        fy0 = self.cymtof(ay)
        fx1 = self.cxmtof(bx)
        fy1 = self.cymtof(by)

        def outcode(mx: int, my: int) -> int:
            oc = 0
            if my < 0:
                oc |= OC_TOP
            elif my >= self.f_h:
                oc |= OC_BOTTOM
            if mx < 0:
                oc |= OC_LEFT
            elif mx >= self.f_w:
                oc |= OC_RIGHT
            return oc

        out1 = outcode(fx0, fy0)
        out2 = outcode(fx1, fy1)
        if out1 & out2:
            return False
        f_w = self.f_w
        f_h = self.f_h
        for _ in range(8):
            if (out1 | out2) == 0:
                break
            outside = out1 if out1 else out2
            if outside & OC_TOP:
                dy = fy0 - fy1
                dx = fx1 - fx0
                tmpx = fx0 + int((dx * fy0) / dy) if dy else fx0
                tmpy = 0
            elif outside & OC_BOTTOM:
                dy = fy0 - fy1
                dx = fx1 - fx0
                tmpx = fx0 + int((dx * (fy0 - f_h)) / dy) if dy else fx0
                tmpy = f_h - 1
            elif outside & OC_RIGHT:
                dy = fy1 - fy0
                dx = fx1 - fx0
                tmpy = fy0 + int((dy * (f_w - 1 - fx0)) / dx) if dx else fy0
                tmpx = f_w - 1
            else:
                dy = fy1 - fy0
                dx = fx1 - fx0
                tmpy = fy0 + int((dy * (-fx0)) / dx) if dx else fy0
                tmpx = 0
            if outside == out1:
                fx0, fy0 = tmpx, tmpy
                out1 = outcode(fx0, fy0)
            else:
                fx1, fy1 = tmpx, tmpy
                out2 = outcode(fx1, fy1)
            if out1 & out2:
                return False
        else:
            return False
        self._clip[0] = fx0
        self._clip[1] = fy0
        self._clip[2] = fx1
        self._clip[3] = fy1
        return True

    def _draw_mline(self, ax: int, ay: int, bx: int, by: int, color: int) -> None:
        if self._clip_mline(ax, ay, bx, by):
            c = self._clip
            self._draw_fline(c[0], c[1], c[2], c[3], color)

    def _draw_grid(self, game) -> None:
        block = MAPBLOCKUNITS * FRACUNIT
        orgx = game.world.bmaporgx
        orgy = game.world.bmaporgy
        start = self.m_x
        rem = (start - orgx) % block
        if rem:
            start += block - rem
        end = self.m_x + self.m_w
        y0, y1 = self.m_y, self.m_y + self.m_h
        x = start
        while x < end:
            self._draw_mline(x, y0, x, y1, GRIDCOLORS)
            x += block
        start = self.m_y
        rem = (start - orgy) % block
        if rem:
            start += block - rem
        end = self.m_y + self.m_h
        x0, x1 = self.m_x, self.m_x + self.m_w
        y = start
        while y < end:
            self._draw_mline(x0, y, x1, y, GRIDCOLORS)
            y += block

    def _draw_walls(self, game) -> None:
        color = WALLCOLORS + self.lightlev
        for line in game.world.lines:
            ax, ay = line.v1.x, line.v1.y
            bx, by = line.v2.x, line.v2.y
            if self.cheating or (line.flags & ML_MAPPED):
                if (line.flags & LINE_NEVERSEE) and not self.cheating:
                    continue
                if line.backsector is None:
                    self._draw_mline(ax, ay, bx, by, color)
                    continue
                if line.frontsector is None:
                    continue
                if line.special == 39:
                    self._draw_mline(ax, ay, bx, by, WALLCOLORS + WALLRANGE // 2)
                elif line.flags & ML_SECRET:
                    self._draw_mline(ax, ay, bx, by, color)
                elif line.backsector.floorheight != line.frontsector.floorheight:
                    self._draw_mline(ax, ay, bx, by, FDWALLCOLORS + self.lightlev)
                elif line.backsector.ceilingheight != line.frontsector.ceilingheight:
                    self._draw_mline(ax, ay, bx, by, CDWALLCOLORS + self.lightlev)
                elif self.cheating:
                    self._draw_mline(ax, ay, bx, by, TSWALLCOLORS + self.lightlev)

    def _rotate(self, x: int, y: int, a: int) -> tuple[int, int]:
        n_fine = ushr(as_u32(a), ANGLETOFINESHIFT)
        cs = finecosine[n_fine]
        sn = finesine[n_fine]
        return fixed_mul(x, cs) - fixed_mul(y, sn), fixed_mul(x, sn) + fixed_mul(y, cs)

    def _draw_line_character(
        self,
        lines: list[tuple[tuple[int, int], tuple[int, int]]],
        scale: int,
        angle: int,
        color: int,
        x: int,
        y: int,
    ) -> None:
        for (ax, ay), (bx, by) in lines:
            nax, nay, nbx, nby = ax, ay, bx, by
            if scale:
                nax = fixed_mul(scale, nax)
                nay = fixed_mul(scale, nay)
                nbx = fixed_mul(scale, nbx)
                nby = fixed_mul(scale, nby)
            if angle:
                nax, nay = self._rotate(nax, nay, angle)
                nbx, nby = self._rotate(nbx, nby, angle)
            self._draw_mline(nax + x, nay + y, nbx + x, nby + y, color)

    def _draw_players(self, game) -> None:
        mo = game.player.mo
        self._draw_line_character(self.player_arrow, 0, mo.angle, WHITE, mo.x, mo.y)

    def _draw_things(self, game) -> None:
        scale = 16 * FRACUNIT
        color = THINGCOLORS + self.lightlev
        for mo in game.world.mobjs:
            self._draw_line_character(
                self.thintriangle_guy, scale, mo.angle, color, mo.x, mo.y
            )

    def _draw_crosshair(self) -> None:
        self._put_dot(self.f_w // 2, self.f_h // 2, XHAIRCOLORS)

    def _draw_marks(self) -> None:
        fb = self._fb
        if fb is None:
            return
        for i, (mx, my) in enumerate(self.markpoints):
            if mx == -1 or self.marknums[i] is None:
                continue
            fx = self.cxmtof(mx)
            fy = self.cymtof(my)
            if self.f_x <= fx <= self.f_w - 5 and self.f_y <= fy <= self.f_h - 6:
                draw_patch(fb, fx, fy, self.marknums[i])
