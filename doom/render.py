"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Software renderer: r_main + r_bsp + r_segs + r_plane + r_draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .compat import abs_fixed, as_i32, as_u32, fixed_div, fixed_mul, shar, ushr
from .defs import (
    ANGLETOFINESHIFT,
    ANG90,
    ANG180,
    DBITS,
    FIELDOFVIEW,
    FINEANGLES,
    FINEMASK,
    FRACBITS,
    FRACUNIT,
    LIGHTLEVELS,
    LIGHTSCALESHIFT,
    LIGHTZSHIFT,
    MAXLIGHTSCALE,
    MAXLIGHTZ,
    ML_DONTPEGBOTTOM,
    ML_DONTPEGTOP,
    ML_MAPPED,
    NF_SUBSECTOR,
    NUMCOLORMAPS,
    SBARHEIGHT,
    SCREENHEIGHT,
    SCREENWIDTH,
    SIL_BOTH,
    SIL_BOTTOM,
    SIL_NONE,
    SIL_TOP,
)
from .tables import finesine, finetangent, init_tables, slope_div, tantoangle

HEIGHTBITS = 12
HEIGHTUNIT = 1 << HEIGHTBITS
ANGLETOSKYSHIFT = 22
SHRT_MAX = 0x7FFF
INT_MAX = 0x7FFFFFFF
INT_MIN = -0x7FFFFFFF


@dataclass
class ClipRange:
    first: int = 0
    last: int = 0


@dataclass
class Visplane:
    height: int = 0
    picnum: int = 0
    lightlevel: int = 0
    minx: int = 0
    maxx: int = 0
    top: list = field(default_factory=list)
    bottom: list = field(default_factory=list)


@dataclass
class DrawSeg:
    x1: int = 0
    x2: int = 0
    scale1: int = 0
    scale2: int = 0
    silhouette: int = 0
    sprtopclip: list = field(default_factory=list)
    sprbottomclip: list = field(default_factory=list)
    bsilheight: int = 0
    tsilheight: int = 0
    curline: object = None
    scalestep: int = 0
    maskedtexturecol: list | None = None


class Renderer:
    def __init__(self, resources) -> None:
        init_tables()
        self.res = resources
        self.viewwidth = SCREENWIDTH
        self.viewheight = SCREENHEIGHT - SBARHEIGHT
        self.centerx = self.viewwidth // 2
        self.centery = self.viewheight // 2
        self.centerxfrac = self.centerx << FRACBITS
        self.centeryfrac = self.centery << FRACBITS
        self.projection = self.centerxfrac
        self.detailshift = 0
        self.viewangletox = [0] * (FINEANGLES // 2)
        self.xtoviewangle = [0] * (SCREENWIDTH + 1)
        self.clipangle = 0
        self.yslope = [0] * SCREENHEIGHT
        self.distscale = [0] * SCREENWIDTH
        self.scalelight = [[0] * MAXLIGHTSCALE for _ in range(LIGHTLEVELS)]
        self.zlight = [[0] * MAXLIGHTZ for _ in range(LIGHTLEVELS)]
        self.walllights = [0] * MAXLIGHTSCALE
        self.ylookup = [i * SCREENWIDTH for i in range(SCREENHEIGHT)]
        self.columnofs = list(range(SCREENWIDTH))
        self.viewwindowx = 0
        self.viewwindowy = 0
        self.scaledviewwidth = SCREENWIDTH
        self.screenblocks = 10
        self.pspritescale = FRACUNIT
        self.pspriteiscale = FRACUNIT
        self.ceilingclip = [0] * SCREENWIDTH
        self.floorclip = [0] * SCREENWIDTH
        self.solidsegs = [ClipRange() for _ in range(64)]
        self.newend = 0
        self.visplanes: list[Visplane] = []
        self.floorplane: Visplane | None = None
        self.ceilingplane: Visplane | None = None
        self.viewx = self.viewy = self.viewz = self.viewangle = 0
        self.viewcos = self.viewsin = 0
        self.extralight = 0
        self.curline = None
        self.frontsector = None
        self.backsector = None
        self.rw_x = self.rw_stopx = 0
        self.rw_start = 0
        self.rw_centerangle = self.rw_offset = self.rw_distance = 0
        self.rw_scale = self.rw_scalestep = 0
        self.rw_midtexturemid = self.rw_toptexturemid = self.rw_bottomtexturemid = 0
        self.rw_normalangle = self.rw_angle1 = 0
        self.segtextured = self.markfloor = self.markceiling = False
        self.maskedtexture = False
        self.maskedtexturecol: list | None = None
        self.midtexture = self.toptexture = self.bottomtexture = 0
        self.pixhigh = self.pixlow = self.pixhighstep = self.pixlowstep = 0
        self.topfrac = self.topstep = self.bottomfrac = self.bottomstep = 0
        self.worldtop = self.worldbottom = self.worldhigh = self.worldlow = 0
        self.dc_x = self.dc_yl = self.dc_yh = self.dc_iscale = self.dc_texturemid = 0
        self.dc_source = bytes(128)
        self.dc_colormap = bytes(range(256))
        self.fb = bytearray(SCREENWIDTH * SCREENHEIGHT)
        self.drawsegs: list[DrawSeg] = []
        self.basexscale = 0
        self.baseyscale = 0
        self._init_mapping()
        self._init_lights()
        self._init_slopes()

    def set_view_size(self, blocks: int, detail: int) -> None:
        """R_SetViewSize / R_ExecuteSetViewSize."""
        blocks = max(3, min(11, int(blocks)))
        detail = 1 if detail else 0
        self.screenblocks = blocks
        self.detailshift = detail
        if blocks == 11:
            scaled = SCREENWIDTH
            viewheight = SCREENHEIGHT
        else:
            scaled = blocks * 32
            viewheight = (blocks * 168 // 10) & ~7
        self.scaledviewwidth = scaled
        self.viewwidth = scaled >> detail
        self.viewheight = viewheight
        self.centerx = self.viewwidth // 2
        self.centery = self.viewheight // 2
        self.centerxfrac = self.centerx << FRACBITS
        self.centeryfrac = self.centery << FRACBITS
        self.projection = self.centerxfrac
        self.viewwindowx = (SCREENWIDTH - scaled) >> 1
        if scaled == SCREENWIDTH:
            self.viewwindowy = 0
        else:
            self.viewwindowy = (SCREENHEIGHT - SBARHEIGHT - viewheight) >> 1
        self.ylookup = [(i + self.viewwindowy) * SCREENWIDTH for i in range(SCREENHEIGHT)]
        self.columnofs = [self.viewwindowx + i for i in range(SCREENWIDTH)]
        self.ceilingclip = [0] * max(1, self.viewwidth)
        self.floorclip = [0] * max(1, self.viewwidth)
        self.pspritescale = FRACUNIT * self.viewwidth // SCREENWIDTH
        self.pspriteiscale = FRACUNIT * SCREENWIDTH // max(1, self.viewwidth)
        self._init_mapping()
        self._init_slopes()
        self._init_lights()

    def _init_mapping(self) -> None:
        focallength = fixed_div(
            self.centerxfrac, finetangent[FINEANGLES // 4 + FIELDOFVIEW // 2]
        )
        half = FINEANGLES // 2
        for i in range(half):
            ft = finetangent[i]
            if ft > FRACUNIT * 2:
                t = -1
            elif ft < -FRACUNIT * 2:
                t = self.viewwidth + 1
            else:
                t = as_i32(self.centerxfrac - fixed_mul(ft, focallength) + FRACUNIT - 1) >> FRACBITS
                t = max(-1, min(self.viewwidth + 1, t))
            self.viewangletox[i] = t
        for x in range(self.viewwidth + 1):
            i = 0
            while i < half and self.viewangletox[i] > x:
                i += 1
            self.xtoviewangle[x] = as_u32((i << ANGLETOFINESHIFT) - ANG90)
        for i in range(half):
            if self.viewangletox[i] == -1:
                self.viewangletox[i] = 0
            elif self.viewangletox[i] == self.viewwidth + 1:
                self.viewangletox[i] = self.viewwidth
        self.clipangle = self.xtoviewangle[0]

    def _init_lights(self) -> None:
        for i in range(LIGHTLEVELS):
            startmap = ((LIGHTLEVELS - 1 - i) * 2) * NUMCOLORMAPS // LIGHTLEVELS
            for j in range(MAXLIGHTZ):
                scale = fixed_div((SCREENWIDTH // 2 * FRACUNIT), (j + 1) << LIGHTZSHIFT) >> LIGHTSCALESHIFT
                level = startmap - scale // 2
                level = max(0, min(NUMCOLORMAPS - 1, level))
                self.zlight[i][j] = level
            for j in range(MAXLIGHTSCALE):
                vw = max(1, self.viewwidth << self.detailshift)
                level = startmap - int(j * SCREENWIDTH / vw / 2)
                self.scalelight[i][j] = max(0, min(NUMCOLORMAPS - 1, level))

    def _init_slopes(self) -> None:
        for i in range(self.viewheight):
            dy = abs(((i - self.centery) << FRACBITS) + FRACUNIT // 2)
            dy = max(dy, 1)
            self.yslope[i] = fixed_div(((self.viewwidth << self.detailshift) // 2) * FRACUNIT, dy)
        from .tables import fine_cos
        for i in range(self.viewwidth):
            cosadj = abs_fixed(fine_cos(self.xtoviewangle[i]))
            self.distscale[i] = fixed_div(FRACUNIT, max(cosadj, 1))

    def point_to_angle(self, x: int, y: int) -> int:
        x = as_i32(x - self.viewx)
        y = as_i32(y - self.viewy)
        if x == 0 and y == 0:
            return 0
        if x >= 0:
            if y >= 0:
                if x > y:
                    return tantoangle[slope_div(y, x)]
                return as_u32(ANG90 - 1 - tantoangle[slope_div(x, y)])
            y = -y
            if x > y:
                return as_u32(-tantoangle[slope_div(y, x)])
            return as_u32(0xC0000000 + tantoangle[slope_div(x, y)])
        x = -x
        if y >= 0:
            if x > y:
                return as_u32(ANG180 - 1 - tantoangle[slope_div(y, x)])
            return as_u32(ANG90 + tantoangle[slope_div(x, y)])
        y = -y
        if x > y:
            return as_u32(ANG180 + tantoangle[slope_div(y, x)])
        return as_u32(0xC0000000 - 1 - tantoangle[slope_div(x, y)])

    def point_on_side(self, x: int, y: int, node) -> int:
        dx = as_i32(x - node.x)
        dy = as_i32(y - node.y)
        left = as_i32(node.dy >> 16) * dx
        right = dy * as_i32(node.dx >> 16)
        return 1 if right >= left else 0

    def scale_from_global_angle(self, visangle: int) -> int:
        anglea = as_u32(ANG90 + as_u32(visangle - self.viewangle))
        angleb = as_u32(ANG90 + as_u32(visangle - self.rw_normalangle))
        sinea = finesine[(anglea >> ANGLETOFINESHIFT) & FINEMASK]
        sineb = finesine[(angleb >> ANGLETOFINESHIFT) & FINEMASK]
        num = fixed_mul(self.projection, sineb) << self.detailshift
        den = fixed_mul(self.rw_distance, sinea)
        if den > (num >> 16) and den:
            scale = fixed_div(num, den)
            if scale > 64 * FRACUNIT:
                scale = 64 * FRACUNIT
            elif scale < 256:
                scale = 256
        else:
            scale = 64 * FRACUNIT
        return scale

    def setup_frame(self, x: int, y: int, z: int, angle: int, extra_light: int = 0) -> None:
        from .tables import fine_cos, fine_sin
        self.viewx, self.viewy, self.viewz = x, y, z
        self.viewangle = as_u32(angle)
        self.viewsin = fine_sin(self.viewangle)
        self.viewcos = fine_cos(self.viewangle)
        self.extralight = extra_light
        # R_ClearPlanes: scale of the view plane at 90° to the view
        ang = ushr(as_u32(self.viewangle - ANG90), ANGLETOFINESHIFT) & FINEMASK
        self.basexscale = fixed_div(finesine[(ang + FINEANGLES // 4) & FINEMASK], self.centerxfrac or 1)
        self.baseyscale = -fixed_div(finesine[ang], self.centerxfrac or 1)

    def render(self, world, fb: bytearray) -> None:
        self.fb = fb
        self.visplanes = []
        self.drawsegs = []
        self._clear_clip()
        if world.nodes:
            self._render_bsp_node(world, world.numnodes - 1)
        else:
            self._subsector(world, 0)
        self._draw_planes()

    def _clear_clip(self) -> None:
        self.solidsegs[0].first = -0x7FFFFFFF
        self.solidsegs[0].last = -1
        self.solidsegs[1].first = self.viewwidth
        self.solidsegs[1].last = 0x7FFFFFFF
        self.newend = 2
        for i in range(self.viewwidth):
            self.floorclip[i] = self.viewheight
            self.ceilingclip[i] = -1

    def _find_plane(self, height: int, picnum: int, lightlevel: int) -> Visplane:
        if picnum == self.res.skyflatnum:
            height = 0
            lightlevel = 0
        for p in self.visplanes:
            if p.height == height and p.picnum == picnum and p.lightlevel == lightlevel:
                return p
        p = Visplane(
            height=height, picnum=picnum, lightlevel=lightlevel,
            minx=self.viewwidth, maxx=-1,
            top=[0xFF] * SCREENWIDTH, bottom=[0] * SCREENWIDTH,
        )
        self.visplanes.append(p)
        return p

    def _check_plane(self, pl: Visplane | None, start: int, stop: int) -> Visplane:
        if pl is None:
            return self._find_plane(0, 0, 0)
        if start < pl.minx:
            intrl, unionl = pl.minx, start
        else:
            unionl, intrl = pl.minx, start
        if stop > pl.maxx:
            intrh, unionh = pl.maxx, stop
        else:
            unionh, intrh = pl.maxx, stop
        x = intrl
        while x <= intrh:
            if 0 <= x < SCREENWIDTH and pl.top[x] != 0xFF:
                break
            x += 1
        if x > intrh:
            pl.minx = unionl
            pl.maxx = unionh
            return pl
        return self._dup_plane(pl, start, stop)

    def _dup_plane(self, src: Visplane, start: int, stop: int) -> Visplane:
        p = Visplane(
            height=src.height, picnum=src.picnum, lightlevel=src.lightlevel,
            minx=start, maxx=stop,
            top=[0xFF] * SCREENWIDTH, bottom=[0] * SCREENWIDTH,
        )
        self.visplanes.append(p)
        return p

    def _render_bsp_node(self, world, bspnum: int) -> None:
        if bspnum & NF_SUBSECTOR or bspnum < 0:
            self._subsector(world, 0 if bspnum == -1 else (bspnum & ~NF_SUBSECTOR))
            return
        node = world.nodes[bspnum]
        side = self.point_on_side(self.viewx, self.viewy, node)
        self._render_bsp_node(world, node.children[side])
        self._render_bsp_node(world, node.children[side ^ 1])

    def _subsector(self, world, num: int) -> None:
        sub = world.subsectors[num]
        self.frontsector = sub.sector
        light = (self.frontsector.lightlevel >> 4) + self.extralight
        light = max(0, min(LIGHTLEVELS - 1, light))
        self.walllights = self.scalelight[light]
        self.floorplane = self._find_plane(
            self.frontsector.floorheight, self.frontsector.floorpic, self.frontsector.lightlevel
        )
        self.ceilingplane = self._find_plane(
            self.frontsector.ceilingheight, self.frontsector.ceilingpic, self.frontsector.lightlevel
        )
        line = sub.firstline
        for _ in range(sub.numlines):
            self._add_line(world.segs[line])
            line += 1

    def _add_line(self, line) -> None:
        self.curline = line
        angle1 = self.point_to_angle(line.v1.x, line.v1.y)
        angle2 = self.point_to_angle(line.v2.x, line.v2.y)
        span = as_u32(angle1 - angle2)
        if span >= ANG180:
            return
        self.rw_angle1 = angle1
        angle1 = as_u32(angle1 - self.viewangle)
        angle2 = as_u32(angle2 - self.viewangle)
        tspan = as_u32(angle1 + self.clipangle)
        if tspan > as_u32(2 * self.clipangle):
            tspan = as_u32(tspan - 2 * self.clipangle)
            if tspan >= span:
                return
            angle1 = self.clipangle
        tspan = as_u32(self.clipangle - angle2)
        if tspan > as_u32(2 * self.clipangle):
            tspan = as_u32(tspan - 2 * self.clipangle)
            if tspan >= span:
                return
            angle2 = as_u32(-self.clipangle)
        mask = FINEANGLES // 2 - 1
        x1 = self.viewangletox[ushr(as_u32(angle1 + ANG90), ANGLETOFINESHIFT) & mask]
        x2 = self.viewangletox[ushr(as_u32(angle2 + ANG90), ANGLETOFINESHIFT) & mask]
        if x1 == x2:
            return
        self.backsector = line.backsector
        if self.backsector is None:
            self._clip_solid(x1, x2 - 1)
            return
        if (
            self.backsector.ceilingheight <= self.frontsector.floorheight
            or self.backsector.floorheight >= self.frontsector.ceilingheight
        ):
            self._clip_solid(x1, x2 - 1)
            return
        self._clip_pass(x1, x2 - 1)

    def _clip_solid(self, first: int, last: int) -> None:
        if first > last:
            return
        start = 0
        while start < self.newend and self.solidsegs[start].last < first - 1:
            start += 1
        if start >= self.newend:
            self._store_wall_range(first, last)
            return
        if first < self.solidsegs[start].first:
            if last < self.solidsegs[start].first - 1:
                self._store_wall_range(first, last)
                self.solidsegs.insert(start, ClipRange(first, last))
                self.newend += 1
                if self.newend > len(self.solidsegs):
                    self.solidsegs.append(ClipRange())
                return
            self._store_wall_range(first, self.solidsegs[start].first - 1)
            self.solidsegs[start].first = first
        if last <= self.solidsegs[start].last:
            return
        nexti = start
        while nexti + 1 < self.newend and last >= self.solidsegs[nexti + 1].first - 1:
            self._store_wall_range(self.solidsegs[nexti].last + 1, self.solidsegs[nexti + 1].first - 1)
            nexti += 1
            if last <= self.solidsegs[nexti].last:
                self.solidsegs[start].last = self.solidsegs[nexti].last
                self._crunch_solid(start, nexti)
                return
        self._store_wall_range(self.solidsegs[nexti].last + 1, last)
        self.solidsegs[start].last = last
        self._crunch_solid(start, nexti)

    def _crunch_solid(self, start: int, nexti: int) -> None:
        if nexti == start:
            return
        tail = self.solidsegs[nexti + 1 : self.newend]
        del self.solidsegs[start + 1 : self.newend]
        self.solidsegs[start + 1 : start + 1] = tail
        self.newend = start + 1 + len(tail)
        while len(self.solidsegs) < 64:
            self.solidsegs.append(ClipRange())

    def _clip_pass(self, first: int, last: int) -> None:
        if first > last:
            return
        start = 0
        while start < self.newend and self.solidsegs[start].last < first - 1:
            start += 1
        if start >= self.newend:
            self._store_wall_range(first, last)
            return
        if first < self.solidsegs[start].first:
            if last < self.solidsegs[start].first - 1:
                self._store_wall_range(first, last)
                return
            self._store_wall_range(first, self.solidsegs[start].first - 1)
        if last <= self.solidsegs[start].last:
            return
        nexti = start
        while nexti + 1 < self.newend and last >= self.solidsegs[nexti + 1].first - 1:
            self._store_wall_range(self.solidsegs[nexti].last + 1, self.solidsegs[nexti + 1].first - 1)
            nexti += 1
            if last <= self.solidsegs[nexti].last:
                return
        self._store_wall_range(self.solidsegs[nexti].last + 1, last)

    def _store_wall_range(self, start: int, stop: int) -> None:
        if start > stop:
            return
        line = self.curline
        linedef = line.linedef
        sidedef = line.sidedef
        linedef.flags |= ML_MAPPED
        self.rw_normalangle = as_u32(line.angle + ANG90)
        offsetangle = as_u32(self.rw_normalangle - self.rw_angle1)
        if offsetangle > ANG180:
            offsetangle = as_u32(-offsetangle)
        if offsetangle > ANG90:
            offsetangle = ANG90
        distangle = as_u32(ANG90 - offsetangle)
        hyp = self._point_to_dist(line.v1.x, line.v1.y)
        self.rw_distance = fixed_mul(hyp, finesine[(distangle >> ANGLETOFINESHIFT) & FINEMASK])
        self.rw_x = start
        self.rw_start = start
        self.rw_stopx = stop + 1
        self.rw_scale = self.scale_from_global_angle(as_u32(self.viewangle + self.xtoviewangle[start]))
        if stop > start:
            scale2 = self.scale_from_global_angle(as_u32(self.viewangle + self.xtoviewangle[stop]))
            self.rw_scalestep = (scale2 - self.rw_scale) // (stop - start)
        else:
            self.rw_scalestep = 0
        self.worldtop = self.frontsector.ceilingheight - self.viewz
        self.worldbottom = self.frontsector.floorheight - self.viewz
        self.midtexture = self.toptexture = self.bottomtexture = 0
        self.maskedtexture = False
        self.maskedtexturecol = None
        self.segtextured = False
        if self.backsector is None:
            self.midtexture = sidedef.midtexture
            self.markfloor = self.markceiling = True
            if linedef.flags & ML_DONTPEGBOTTOM:
                vtop = self.frontsector.floorheight + self.res.texture_height(self.midtexture)
                self.rw_midtexturemid = vtop - self.viewz
            else:
                self.rw_midtexturemid = self.worldtop
            self.rw_midtexturemid += sidedef.rowoffset
        else:
            self.worldhigh = self.backsector.ceilingheight - self.viewz
            self.worldlow = self.backsector.floorheight - self.viewz
            if (
                self.frontsector.ceilingpic == self.res.skyflatnum
                and self.backsector.ceilingpic == self.res.skyflatnum
            ):
                self.worldtop = self.worldhigh
            self.markfloor = (
                self.worldlow != self.worldbottom
                or self.backsector.floorpic != self.frontsector.floorpic
                or self.backsector.lightlevel != self.frontsector.lightlevel
            )
            self.markceiling = (
                self.worldhigh != self.worldtop
                or self.backsector.ceilingpic != self.frontsector.ceilingpic
                or self.backsector.lightlevel != self.frontsector.lightlevel
            )
            if (
                self.backsector.ceilingheight <= self.frontsector.floorheight
                or self.backsector.floorheight >= self.frontsector.ceilingheight
            ):
                self.markceiling = self.markfloor = True
            if self.worldhigh < self.worldtop:
                self.toptexture = sidedef.toptexture
                if linedef.flags & ML_DONTPEGTOP:
                    self.rw_toptexturemid = self.worldtop
                else:
                    vtop = self.backsector.ceilingheight + self.res.texture_height(self.toptexture or 0)
                    self.rw_toptexturemid = vtop - self.viewz
            if self.worldlow > self.worldbottom:
                self.bottomtexture = sidedef.bottomtexture
                if linedef.flags & ML_DONTPEGBOTTOM:
                    self.rw_bottomtexturemid = self.worldtop
                else:
                    self.rw_bottomtexturemid = self.worldlow
            self.rw_toptexturemid += sidedef.rowoffset
            self.rw_bottomtexturemid += sidedef.rowoffset
            if sidedef.midtexture:
                self.maskedtexture = True
                self.maskedtexturecol = [SHRT_MAX] * (stop - start + 1)
        self.segtextured = bool(
            self.midtexture or self.toptexture or self.bottomtexture or self.maskedtexture
        )
        if self.segtextured:
            offsetangle = as_u32(self.rw_normalangle - self.rw_angle1)
            if offsetangle > ANG180:
                offsetangle = as_u32(-offsetangle)
            self.rw_offset = fixed_mul(hyp, finesine[(offsetangle >> ANGLETOFINESHIFT) & FINEMASK])
            if as_u32(self.rw_normalangle - self.rw_angle1) < ANG180:
                self.rw_offset = -self.rw_offset
            self.rw_offset += sidedef.textureoffset + line.offset
            self.rw_centerangle = as_u32(ANG90 + self.viewangle - self.rw_normalangle)
        if self.frontsector.floorheight >= self.viewz:
            self.markfloor = False
        if self.frontsector.ceilingheight <= self.viewz and self.frontsector.ceilingpic != self.res.skyflatnum:
            self.markceiling = False
        if self.markceiling:
            self.ceilingplane = self._check_plane(self.ceilingplane, start, stop)
        if self.markfloor:
            self.floorplane = self._check_plane(self.floorplane, start, stop)
        self.worldtop >>= 4
        self.worldbottom >>= 4
        self.topstep = -fixed_mul(self.rw_scalestep, self.worldtop)
        self.topfrac = (self.centeryfrac >> 4) - fixed_mul(self.worldtop, self.rw_scale)
        self.bottomstep = -fixed_mul(self.rw_scalestep, self.worldbottom)
        self.bottomfrac = (self.centeryfrac >> 4) - fixed_mul(self.worldbottom, self.rw_scale)
        if self.backsector is not None:
            self.worldhigh >>= 4
            self.worldlow >>= 4
            if self.worldhigh < self.worldtop:
                self.pixhigh = (self.centeryfrac >> 4) - fixed_mul(self.worldhigh, self.rw_scale)
                self.pixhighstep = -fixed_mul(self.rw_scalestep, self.worldhigh)
            if self.worldlow > self.worldbottom:
                self.pixlow = (self.centeryfrac >> 4) - fixed_mul(self.worldlow, self.rw_scale)
                self.pixlowstep = -fixed_mul(self.rw_scalestep, self.worldlow)
        scale1 = self.rw_scale
        self._render_seg_loop()
        self._push_drawseg(start, stop, scale1)

    def _push_drawseg(self, start: int, stop: int, scale1: int) -> None:
        """r_segs: fill a drawseg for R_DrawSprite clipping."""
        ds = DrawSeg(
            x1=start,
            x2=stop,
            scale1=scale1,
            scale2=scale1 + self.rw_scalestep * max(0, stop - start),
            curline=self.curline,
        )
        ds.scalestep = self.rw_scalestep
        ds.maskedtexturecol = self.maskedtexturecol
        if self.backsector is None:
            ds.silhouette = SIL_BOTH
            ds.bsilheight = INT_MAX
            ds.tsilheight = INT_MIN
            width = stop - start + 1
            ds.sprtopclip = [self.viewheight] * width
            ds.sprbottomclip = [-1] * width
        else:
            ds.silhouette = SIL_NONE
            if self.frontsector.floorheight > self.backsector.floorheight:
                ds.silhouette = SIL_BOTTOM
                ds.bsilheight = self.frontsector.floorheight
            elif self.backsector.floorheight > self.viewz:
                ds.silhouette = SIL_BOTTOM
                ds.bsilheight = INT_MAX
            if self.frontsector.ceilingheight < self.backsector.ceilingheight:
                ds.silhouette |= SIL_TOP
                ds.tsilheight = self.frontsector.ceilingheight
            elif self.backsector.ceilingheight < self.viewz:
                ds.silhouette |= SIL_TOP
                ds.tsilheight = INT_MIN
            if self.backsector.ceilingheight <= self.frontsector.floorheight:
                ds.silhouette |= SIL_BOTTOM
                ds.bsilheight = INT_MAX
            if self.backsector.floorheight >= self.frontsector.ceilingheight:
                ds.silhouette |= SIL_TOP
                ds.tsilheight = INT_MIN
            ds.sprtopclip = self.ceilingclip[start : stop + 1][:]
            ds.sprbottomclip = self.floorclip[start : stop + 1][:]
            if self.maskedtexture:
                if not (ds.silhouette & SIL_TOP):
                    ds.silhouette |= SIL_TOP
                    ds.tsilheight = INT_MIN
                if not (ds.silhouette & SIL_BOTTOM):
                    ds.silhouette |= SIL_BOTTOM
                    ds.bsilheight = INT_MAX
        self.drawsegs.append(ds)

    def _point_to_dist(self, x: int, y: int) -> int:
        dx = abs_fixed(x - self.viewx)
        dy = abs_fixed(y - self.viewy)
        if dy > dx:
            dx, dy = dy, dx
        if dx == 0:
            return 0
        frac = fixed_div(dy, dx)
        ang = (tantoangle[min(frac >> DBITS, 2048)] + ANG90) >> ANGLETOFINESHIFT
        return fixed_div(dx, finesine[ang & FINEMASK])

    def _render_seg_loop(self) -> None:
        texturecolumn = 0
        while self.rw_x < self.rw_stopx:
            yl = shar(self.topfrac + HEIGHTUNIT - 1, HEIGHTBITS)
            if yl < self.ceilingclip[self.rw_x] + 1:
                yl = self.ceilingclip[self.rw_x] + 1
            if self.markceiling and self.ceilingplane is not None:
                top = self.ceilingclip[self.rw_x] + 1
                bottom = yl - 1
                if bottom >= self.floorclip[self.rw_x]:
                    bottom = self.floorclip[self.rw_x] - 1
                if top <= bottom:
                    self.ceilingplane.top[self.rw_x] = top
                    self.ceilingplane.bottom[self.rw_x] = bottom
            yh = shar(self.bottomfrac, HEIGHTBITS)
            if yh >= self.floorclip[self.rw_x]:
                yh = self.floorclip[self.rw_x] - 1
            if self.markfloor and self.floorplane is not None:
                top = yh + 1
                bottom = self.floorclip[self.rw_x] - 1
                if top <= self.ceilingclip[self.rw_x]:
                    top = self.ceilingclip[self.rw_x] + 1
                if top <= bottom:
                    self.floorplane.top[self.rw_x] = top
                    self.floorplane.bottom[self.rw_x] = bottom
            if self.segtextured:
                angle = ushr(as_u32(self.rw_centerangle + self.xtoviewangle[self.rw_x]), ANGLETOFINESHIFT)
                tanv = finetangent[angle & (FINEANGLES // 2 - 1)]
                texturecolumn = shar(self.rw_offset - fixed_mul(tanv, self.rw_distance), FRACBITS)
                index = ushr(self.rw_scale, LIGHTSCALESHIFT)
                if index >= MAXLIGHTSCALE:
                    index = MAXLIGHTSCALE - 1
                self.dc_colormap = self.res.colormap(self.walllights[index])
                self.dc_x = self.rw_x
                self.dc_iscale = (0xFFFFFFFF // self.rw_scale) if self.rw_scale else 0
            if self.midtexture:
                self.dc_yl, self.dc_yh = yl, yh
                self.dc_texturemid = self.rw_midtexturemid
                self.dc_source = self.res.get_column(self.midtexture, texturecolumn)
                self._draw_column()
                self.ceilingclip[self.rw_x] = self.viewheight
                self.floorclip[self.rw_x] = -1
            else:
                if self.toptexture:
                    mid = shar(self.pixhigh, HEIGHTBITS)
                    self.pixhigh += self.pixhighstep
                    if mid >= self.floorclip[self.rw_x]:
                        mid = self.floorclip[self.rw_x] - 1
                    if mid >= yl:
                        self.dc_yl, self.dc_yh = yl, mid
                        self.dc_texturemid = self.rw_toptexturemid
                        self.dc_source = self.res.get_column(self.toptexture, texturecolumn)
                        self._draw_column()
                        self.ceilingclip[self.rw_x] = mid
                    else:
                        self.ceilingclip[self.rw_x] = yl - 1
                elif self.markceiling:
                    self.ceilingclip[self.rw_x] = yl - 1
                if self.bottomtexture:
                    mid = shar(self.pixlow + HEIGHTUNIT - 1, HEIGHTBITS)
                    self.pixlow += self.pixlowstep
                    if mid <= self.ceilingclip[self.rw_x]:
                        mid = self.ceilingclip[self.rw_x] + 1
                    if mid <= yh:
                        self.dc_yl, self.dc_yh = mid, yh
                        self.dc_texturemid = self.rw_bottomtexturemid
                        self.dc_source = self.res.get_column(self.bottomtexture, texturecolumn)
                        self._draw_column()
                        self.floorclip[self.rw_x] = mid
                    else:
                        self.floorclip[self.rw_x] = yh + 1
                elif self.markfloor:
                    self.floorclip[self.rw_x] = yh + 1
                if self.maskedtexture and self.maskedtexturecol is not None:
                    self.maskedtexturecol[self.rw_x - self.rw_start] = texturecolumn
            self.rw_scale += self.rw_scalestep
            self.topfrac += self.topstep
            self.bottomfrac += self.bottomstep
            self.rw_x += 1

    def _draw_column(self) -> None:
        count = self.dc_yh - self.dc_yl
        if count < 0 or self.dc_x < 0 or self.dc_x >= self.viewwidth:
            return
        yl = max(0, min(SCREENHEIGHT - 1, self.dc_yl))
        if self.detailshift:
            x = self.dc_x << 1
            if x < 0 or x + 1 >= SCREENWIDTH:
                return
            dest = self.ylookup[yl] + self.columnofs[x]
            dest2 = dest + 1
        else:
            dest = self.ylookup[yl] + self.columnofs[self.dc_x]
            dest2 = None
        fracstep = self.dc_iscale
        frac = self.dc_texturemid + (self.dc_yl - self.centery) * fracstep
        src = self.dc_source
        cm = self.dc_colormap
        fb = self.fb
        slen = len(src)
        limit = SCREENWIDTH * SCREENHEIGHT
        while count >= 0 and dest < limit:
            idx = (frac >> FRACBITS) & 127
            if slen:
                pix = src[idx % slen]
                val = cm[pix] if pix < len(cm) else pix
                fb[dest] = val
                if dest2 is not None and dest2 < limit:
                    fb[dest2] = val
            dest += SCREENWIDTH
            if dest2 is not None:
                dest2 += SCREENWIDTH
            frac = as_i32(frac + fracstep)
            count -= 1

    def draw_masked(self) -> None:
        """R_DrawMasked leftover two-sided mids (after sprites)."""
        for ds in reversed(self.drawsegs):
            if ds.maskedtexturecol:
                self.render_masked_seg_range(ds, ds.x1, ds.x2)

    def render_masked_seg_range(self, ds: DrawSeg, x1: int, x2: int) -> None:
        """R_RenderMaskedSegRange: door / grate midtexture in the opening."""
        if not ds.maskedtexturecol or ds.curline is None:
            return
        line = ds.curline
        front = line.frontsector
        back = line.backsector
        sidedef = line.sidedef
        texnum = sidedef.midtexture if sidedef is not None else 0
        if not texnum or back is None or front is None:
            return
        lightnum = (front.lightlevel >> 4) + self.extralight
        if line.v1.y == line.v2.y:
            lightnum -= 1
        elif line.v1.x == line.v2.x:
            lightnum += 1
        lightnum = max(0, min(LIGHTLEVELS - 1, lightnum))
        walllights = self.scalelight[lightnum]
        if line.linedef.flags & ML_DONTPEGBOTTOM:
            dc_texturemid = front.floorheight if front.floorheight > back.floorheight else back.floorheight
            dc_texturemid = dc_texturemid + self.res.texture_height(texnum) - self.viewz
        else:
            dc_texturemid = (
                front.ceilingheight if front.ceilingheight < back.ceilingheight else back.ceilingheight
            )
            dc_texturemid = dc_texturemid - self.viewz
        dc_texturemid += sidedef.rowoffset
        spryscale = ds.scale1 + (x1 - ds.x1) * ds.scalestep
        for dc_x in range(x1, x2 + 1):
            i = dc_x - ds.x1
            if i < 0 or i >= len(ds.maskedtexturecol):
                spryscale += ds.scalestep
                continue
            tcol = ds.maskedtexturecol[i]
            if tcol != SHRT_MAX:
                index = ushr(spryscale, LIGHTSCALESHIFT) if spryscale > 0 else 0
                if index >= MAXLIGHTSCALE:
                    index = MAXLIGHTSCALE - 1
                self.dc_colormap = self.res.colormap(walllights[index])
                self.dc_x = dc_x
                self.dc_iscale = (0xFFFFFFFF // spryscale) if spryscale else 0
                self.dc_texturemid = dc_texturemid
                sprtopscreen = self.centeryfrac - fixed_mul(dc_texturemid, spryscale)
                mceil = ds.sprtopclip[i] if i < len(ds.sprtopclip) else -1
                mfloor = ds.sprbottomclip[i] if i < len(ds.sprbottomclip) else self.viewheight
                posts = self.res.column_posts(texnum, tcol)
                self._draw_masked_column(posts, sprtopscreen, spryscale, mceil, mfloor)
                ds.maskedtexturecol[i] = SHRT_MAX
            spryscale += ds.scalestep

    def _draw_masked_column(
        self, posts: list[tuple[int, bytes]], sprtopscreen: int, spryscale: int, mceil: int, mfloor: int
    ) -> None:
        """R_DrawMaskedColumn: opaque posts clipped to the seg opening."""
        basemid = self.dc_texturemid
        for topdelta, pixels in posts:
            if not pixels:
                continue
            topscreen = sprtopscreen + spryscale * topdelta
            bottomscreen = topscreen + spryscale * len(pixels)
            yl = (topscreen + FRACUNIT - 1) >> FRACBITS
            yh = (bottomscreen - 1) >> FRACBITS
            if yh >= mfloor:
                yh = mfloor - 1
            if yl <= mceil:
                yl = mceil + 1
            if yl < 0:
                yl = 0
            if yh >= self.viewheight:
                yh = self.viewheight - 1
            if yl <= yh:
                src = pixels if len(pixels) >= 128 else pixels + bytes(128 - len(pixels))
                self.dc_yl, self.dc_yh = yl, yh
                self.dc_source = src[:128]
                self.dc_texturemid = basemid - (topdelta << FRACBITS)
                self._draw_column()
        self.dc_texturemid = basemid

    def _draw_planes(self) -> None:
        """R_DrawPlanes + R_MapPlane (r_plane.prg)."""
        for pl in self.visplanes:
            if pl.minx > pl.maxx:
                continue
            if pl.picnum == self.res.skyflatnum:
                self.dc_iscale = 9 * FRACUNIT // 10
                self.dc_colormap = self.res.colormap(0)
                self.dc_texturemid = 100 * FRACUNIT
                for x in range(pl.minx, pl.maxx + 1):
                    yl, yh = pl.top[x], pl.bottom[x]
                    if yl <= yh and yl < 0xFF:
                        ang = ushr(as_u32(self.viewangle + self.xtoviewangle[x]), ANGLETOSKYSHIFT)
                        self.dc_x, self.dc_yl, self.dc_yh = x, yl, yh
                        self.dc_source = self.res.get_column(self.res.skytexture, ang)
                        self._draw_column()
                continue
            light = max(0, min(LIGHTLEVELS - 1, (pl.lightlevel >> 4) + self.extralight))
            planezlight = self.zlight[light]
            flat = self.res.flat_pixels(pl.picnum)
            planeheight = abs_fixed(pl.height - self.viewz)
            if planeheight == 0:
                continue
            cached_y = -1
            distance = ds_xstep = ds_ystep = 0
            for x in range(max(0, pl.minx), min(self.viewwidth, pl.maxx + 1)):
                t1, b1 = pl.top[x], pl.bottom[x]
                if t1 > b1 or t1 == 0xFF:
                    continue
                for y in range(t1, min(b1, self.viewheight - 1) + 1):
                    if y != cached_y:
                        cached_y = y
                        distance = fixed_mul(planeheight, self.yslope[y])
                        ds_xstep = fixed_mul(distance, self.basexscale)
                        ds_ystep = fixed_mul(distance, self.baseyscale)
                    length = fixed_mul(distance, self.distscale[x])
                    ang = ushr(as_u32(self.viewangle + self.xtoviewangle[x]), ANGLETOFINESHIFT) & FINEMASK
                    ds_xfrac = self.viewx + fixed_mul(finesine[(ang + FINEANGLES // 4) & FINEMASK], length)
                    ds_yfrac = -self.viewy - fixed_mul(finesine[ang], length)
                    index = min(MAXLIGHTZ - 1, ushr(distance, LIGHTZSHIFT))
                    cm = self.res.colormap(planezlight[index])
                    # R_DrawSpan: xtemp = xfrac>>16, ytemp = (yfrac>>10)&0x0FC0
                    spot = ((ds_xfrac >> 16) & 63) | ((ds_yfrac >> 10) & 0x0FC0)
                    pix = cm[flat[spot] if spot < len(flat) else 0]
                    if self.detailshift:
                        xx = x << 1
                        off = self.ylookup[y] + self.columnofs[xx]
                        self.fb[off] = pix
                        self.fb[off + 1] = pix
                    else:
                        self.fb[self.ylookup[y] + self.columnofs[x]] = pix
