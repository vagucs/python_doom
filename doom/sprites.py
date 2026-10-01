"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

VisSprite projection and wall clip (r_things.prg).
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field

from .compat import as_i32, as_u32, fixed_div, fixed_mul
from .defs import (
    ANG45,
    FINEANGLES,
    FINEMASK,
    FRACBITS,
    FRACUNIT,
    MF_SHADOW,
    SCREENWIDTH,
    SIL_BOTTOM,
    SIL_TOP,
)
from .v_video import patch_size

BASEYCENTER = 100
WEAPONTOP = 32 * FRACUNIT
WEAPONBOTTOM = 128 * FRACUNIT
LOWERSPEED = 6 * FRACUNIT
RAISESPEED = 6 * FRACUNIT

MINZ = 4 * FRACUNIT
# Harbour r_draw.prg: ±SCREENWIDTH offsets, colormap 6 (R_DrawFuzzColumn).
_FUZZ_DIR = (
    1, -1, 1, -1, 1, 1, -1, 1, 1, -1, 1, 1, 1, -1, 1, 1, 1, -1, -1, -1, -1, 1, -1, -1, 1,
    1, 1, 1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, -1, -1, -1, 1, 1, 1, 1, -1, 1, 1, -1, 1,
)
_fuzzpos = 0
MAX_SPRITE_FRAMES = 29


@dataclass
class SpriteFrame:
    """spriteframe_t: 8 rotations, optional mirror (flip)."""

    rotate: int = -1
    lump: list = field(default_factory=lambda: [-1] * 8)
    flip: list = field(default_factory=lambda: [0] * 8)


def init_sprite_defs(wad) -> dict[str, list[SpriteFrame]]:
    """R_InitSpriteDefs: parse S_START..S_END, including POSSA2A8 mirrors."""
    start = wad.check_num_for_name("S_START")
    end = wad.check_num_for_name("S_END")
    if start < 0:
        start = wad.check_num_for_name("SS_START")
    if end < 0:
        end = wad.check_num_for_name("SS_END")
    if start >= 0 and end > start:
        first, last = start + 1, end - 1
    else:
        first, last = 0, wad.num_lumps() - 1
    buckets: dict[str, list[int]] = {}
    for lump in range(first, last + 1):
        name = wad.lump_name(lump)
        if len(name) < 6:
            continue
        buckets.setdefault(name[:4], []).append(lump)
    result: dict[str, list[SpriteFrame]] = {}
    for sprname, lumps in buckets.items():
        frames = [SpriteFrame() for _ in range(MAX_SPRITE_FRAMES)]
        maxframe = -1
        for lump in lumps:
            name = wad.lump_name(lump)
            frame = ord(name[4]) - ord("A")
            rotation = ord(name[5]) - ord("0")
            if _install_sprite_lump(frames, lump, frame, rotation, False):
                maxframe = max(maxframe, frame)
            if len(name) >= 8 and "A" <= name[6] <= "]":
                frame2 = ord(name[6]) - ord("A")
                rotation2 = ord(name[7]) - ord("0")
                if _install_sprite_lump(frames, lump, frame2, rotation2, True):
                    maxframe = max(maxframe, frame2)
        if maxframe >= 0:
            for frame_i in range(maxframe + 1):
                slot = frames[frame_i]
                if slot.rotate == -1:
                    print(
                        f"R_InitSprites: No patches found for {sprname} frame {chr(ord('A') + frame_i)}",
                        file=sys.stderr,
                    )
                    slot.rotate = 0
            result[sprname] = frames[: maxframe + 1]
    return result


def _install_sprite_lump(
    frames: list[SpriteFrame], lump: int, frame: int, rotation: int, flipped: bool
) -> bool:
    """R_InstallSpriteLump (no I_Error: skip bad/duplicate slots)."""
    if frame < 0 or frame >= MAX_SPRITE_FRAMES or rotation < 0 or rotation > 8:
        return False
    sf = frames[frame]
    if rotation == 0:
        if sf.rotate == 1:
            return True
        sf.rotate = 0
        for r in range(8):
            sf.lump[r] = lump
            sf.flip[r] = int(flipped)
        return True
    if sf.rotate == 0:
        return True
    sf.rotate = 1
    idx = rotation - 1
    if sf.lump[idx] < 0:
        sf.lump[idx] = lump
        sf.flip[idx] = int(flipped)
    return True


def lookup_sprite(res, name: str, ang_to_thing: int, moangle: int, frame: int) -> tuple[int, int] | None:
    """(lump, flip) from the installed sprite frames — not check_num_for_name('POSSA2')."""
    base = (name or "")[:4].upper()
    frames = getattr(res, "sprites", None) or {}
    sprframes = frames.get(base)
    if not sprframes:
        return None
    fi = frame & 0x7FFF
    if fi >= len(sprframes):
        return None
    sf = sprframes[fi]
    if sf.rotate:
        rot = ushr_29(as_u32(ang_to_thing - moangle + (ANG45 // 2) * 9)) & 7
        lump, flip = sf.lump[rot], sf.flip[rot]
    else:
        lump, flip = sf.lump[0], sf.flip[0]
    if lump < 0:
        return None
    return lump, flip


def draw_sprites(renderer, world, fb: bytearray) -> None:
    vis = []
    for mo in world.mobjs:
        if not mo.sprite or mo.player is not None:
            continue
        item = _project(renderer, mo)
        if item is not None:
            vis.append(item)
    vis.sort(key=lambda t: t["scale"])
    for spr in vis:
        _draw_sprite(renderer, fb, spr)


def _project(renderer, mo) -> dict | None:
    tr_x = as_i32(mo.x - renderer.viewx)
    tr_y = as_i32(mo.y - renderer.viewy)
    gxt = fixed_mul(tr_x, renderer.viewcos)
    gyt = -fixed_mul(tr_y, renderer.viewsin)
    tz = gxt - gyt
    if tz < MINZ:
        return None
    xscale = fixed_div(renderer.projection, tz)
    # Harbour r_things: gyt := FixedMul(tr_y, viewcos)  (not negated)
    gxt = -fixed_mul(tr_x, renderer.viewsin)
    gyt = fixed_mul(tr_y, renderer.viewcos)
    tx = -(gyt + gxt)
    if abs(tx) > tz * 4:
        return None
    wad = renderer.res.wad
    found = lookup_sprite(
        renderer.res, mo.sprite, renderer.point_to_angle(mo.x, mo.y), mo.angle, getattr(mo, "frame", 0)
    )
    if found is None:
        return None
    lump, flip = found
    patch = wad.cache_lump_num(lump)
    w, _h, left, top = patch_size(patch)
    tx -= left * FRACUNIT
    x1 = (renderer.centerxfrac + fixed_mul(tx, xscale)) >> FRACBITS
    if x1 > renderer.viewwidth:
        return None
    tx += w * FRACUNIT
    x2 = ((renderer.centerxfrac + fixed_mul(tx, xscale)) >> FRACBITS) - 1
    if x2 < 0:
        return None
    iscale = fixed_div(FRACUNIT, xscale) if xscale else FRACUNIT
    xiscale = -iscale if flip else iscale
    startfrac = ((w << FRACBITS) - 1) if flip else 0
    vis_x1 = max(x1, 0)
    vis_x2 = min(x2, renderer.viewwidth - 1)
    if vis_x1 > x1:
        startfrac += xiscale * (vis_x1 - x1)
    return {
        "mo": mo,
        "patch": patch,
        "w": w,
        "scale": xscale << renderer.detailshift,
        "gx": mo.x,
        "gy": mo.y,
        "gz": mo.z,
        "gzt": mo.z + top * FRACUNIT,
        "texturemid": mo.z + top * FRACUNIT - renderer.viewz,
        "x1": vis_x1,
        "x2": vis_x2,
        "xiscale": xiscale,
        "startfrac": startfrac,
    }


def ushr_29(n: int) -> int:
    return (n & 0xFFFFFFFF) >> 29


def _point_on_seg_side(x: int, y: int, line) -> int:
    lx, ly = line.v1.x, line.v1.y
    ldx = line.v2.x - lx
    ldy = line.v2.y - ly
    if ldx == 0:
        if x <= lx:
            return 1 if ldy > 0 else 0
        return 1 if ldy < 0 else 0
    if ldy == 0:
        if y <= ly:
            return 1 if ldx < 0 else 0
        return 1 if ldx > 0 else 0
    dx = x - lx
    dy = y - ly
    left = fixed_mul(ldy >> FRACBITS, dx)
    right = fixed_mul(dy, ldx >> FRACBITS)
    return 0 if right < left else 1


def _clip_against_walls(renderer, spr) -> tuple[list[int], list[int]]:
    x1, x2 = spr["x1"], spr["x2"]
    clipbot = [-2] * SCREENWIDTH
    cliptop = [-2] * SCREENWIDTH
    for ds in reversed(renderer.drawsegs):
        if ds.x1 > x2 or ds.x2 < x1:
            continue
        if ds.silhouette == 0 and not ds.maskedtexturecol:
            continue
        r1 = max(ds.x1, x1)
        r2 = min(ds.x2, x2)
        scale = max(ds.scale1, ds.scale2)
        lowscale = min(ds.scale1, ds.scale2)
        in_front = scale < spr["scale"] or (
            lowscale < spr["scale"]
            and ds.curline is not None
            and _point_on_seg_side(spr["gx"], spr["gy"], ds.curline) == 0
        )
        if in_front:
            if ds.maskedtexturecol:
                renderer.render_masked_seg_range(ds, r1, r2)
            continue
        silhouette = ds.silhouette
        if spr["gz"] >= ds.bsilheight:
            silhouette &= ~SIL_BOTTOM
        if spr["gzt"] <= ds.tsilheight:
            silhouette &= ~SIL_TOP
        for x in range(r1, r2 + 1):
            i = x - ds.x1
            if i < 0 or i >= len(ds.sprtopclip):
                continue
            if silhouette & SIL_BOTTOM and clipbot[x] == -2:
                clipbot[x] = ds.sprbottomclip[i]
            if silhouette & SIL_TOP and cliptop[x] == -2:
                cliptop[x] = ds.sprtopclip[i]
    viewh = renderer.viewheight
    for x in range(x1, x2 + 1):
        if clipbot[x] == -2:
            clipbot[x] = viewh
        if cliptop[x] == -2:
            cliptop[x] = -1
    return cliptop, clipbot


def draw_psprite(renderer, fb: bytearray, patch: bytes, sx: int, sy: int) -> None:
    """R_DrawPSprite: weapon overlay, same leftover/top as vanilla (not V_DrawPatch 0,32)."""
    w, _h, left, top = patch_size(patch)
    pspritescale = getattr(renderer, "pspritescale", FRACUNIT)
    pspriteiscale = getattr(renderer, "pspriteiscale", FRACUNIT)
    tx = sx - 160 * FRACUNIT
    tx -= left * FRACUNIT
    x1 = (renderer.centerxfrac + fixed_mul(tx, pspritescale)) >> FRACBITS
    if x1 > renderer.viewwidth:
        return
    tx += w * FRACUNIT
    x2 = ((renderer.centerxfrac + fixed_mul(tx, pspritescale)) >> FRACBITS) - 1
    if x2 < 0:
        return
    vis_x1 = max(x1, 0)
    vis_x2 = min(x2, renderer.viewwidth - 1)
    startfrac = 0
    if vis_x1 > x1:
        startfrac += pspriteiscale * (vis_x1 - x1)
    texturemid = BASEYCENTER * FRACUNIT + FRACUNIT // 2 - (sy - top * FRACUNIT)
    # Harbour R_DrawPSprite: vis.scale = pspritescale << detailshift so LOW
    # keeps full weapon height (X stays in viewwidth, DrawColumnLow doubles it).
    vis_scale = pspritescale << getattr(renderer, "detailshift", 0)
    _draw_sprite(
        renderer,
        fb,
        {
            "patch": patch,
            "w": w,
            "scale": vis_scale,
            "texturemid": texturemid,
            "x1": vis_x1,
            "x2": vis_x2,
            "xiscale": pspriteiscale,
            "startfrac": startfrac,
        },
        clip_walls=False,
    )


def weapon_psprite_xy(player, leveltime: int) -> tuple[int, int]:
    """A_WeaponReady bob, or A_Raise/A_Lower sy while switching weapons."""
    from .tables import finesine

    state = getattr(player, "psprite_state", "ready")
    if state in ("up", "down"):
        return FRACUNIT, player.psprite_sy
    if state == "atk":
        return FRACUNIT, getattr(player, "psprite_sy", WEAPONTOP) or WEAPONTOP
    bob = player.bob or 0
    angle = (128 * leveltime) & FINEMASK
    sx = FRACUNIT + fixed_mul(bob, finesine[(angle + FINEANGLES // 4) % len(finesine)])
    angle &= FINEANGLES // 2 - 1
    sy = WEAPONTOP + fixed_mul(bob, finesine[angle])
    player.psprite_sy = sy
    return sx, sy


def _draw_sprite(renderer, fb, spr, clip_walls: bool = True) -> None:
    patch = spr["patch"]
    patch_w = spr["w"]
    iscale = spr["xiscale"]
    spryscale = spr["scale"]
    # R_DrawVisSprite: dc_iscale = abs(xiscale) >> detailshift
    y_iscale = abs(iscale) >> getattr(renderer, "detailshift", 0)
    if y_iscale < 1:
        y_iscale = 1
    sprtopscreen = renderer.centeryfrac - fixed_mul(spr["texturemid"], spryscale)
    if clip_walls:
        cliptop, clipbot = _clip_against_walls(renderer, spr)
    else:
        cliptop = [-1] * SCREENWIDTH
        clipbot = [renderer.viewheight] * SCREENWIDTH
    colofs = [struct.unpack_from("<I", patch, 8 + c * 4)[0] for c in range(max(1, patch_w))]
    mo = spr.get("mo")
    fuzz = mo is not None and (getattr(mo, "flags", 0) & MF_SHADOW)
    if fuzz:
        cm = renderer.res.colormap(6)
    else:
        cm = renderer.fixedcolormap or renderer.res.colormap(0)
    ylookup = renderer.ylookup
    frac = spr["startfrac"]
    for x in range(spr["x1"], spr["x2"] + 1):
        col = frac >> FRACBITS
        if 0 <= col < patch_w:
            column = colofs[col]
            while column < len(patch):
                topdelta = patch[column]
                if topdelta == 0xFF:
                    break
                length = patch[column + 1]
                source = column + 3
                topscreen = sprtopscreen + spryscale * topdelta
                bottomscreen = topscreen + spryscale * length
                yl = (topscreen + FRACUNIT - 1) >> FRACBITS
                yh = (bottomscreen - 1) >> FRACBITS
                if yl <= cliptop[x]:
                    yl = cliptop[x] + 1
                if yh >= clipbot[x]:
                    yh = clipbot[x] - 1
                if yl < 0:
                    yl = 0
                if yh >= renderer.viewheight:
                    yh = renderer.viewheight - 1
                if fuzz:
                    if yl <= 0:
                        yl = 1
                    if yh >= renderer.viewheight - 1:
                        yh = renderer.viewheight - 2
                if yl <= yh:
                    texfrac = fixed_mul((yl << FRACBITS) - topscreen, y_iscale)
                    if texfrac < 0:
                        texfrac = 0
                    for y in range(yl, yh + 1):
                        if fuzz:
                            _draw_fuzz_pixel(renderer, fb, x, y, cm)
                        else:
                            idx = texfrac >> FRACBITS
                            if 0 <= idx < length:
                                pix = patch[source + idx]
                                val = cm[pix] if pix < len(cm) else pix
                                if renderer.detailshift:
                                    xx = x << 1
                                    off = ylookup[y] + renderer.columnofs[xx]
                                    fb[off] = val
                                    fb[off + 1] = val
                                else:
                                    fb[ylookup[y] + renderer.columnofs[x]] = val
                        texfrac += y_iscale
                column += length + 4
        frac += iscale


def _draw_fuzz_pixel(renderer, fb, x: int, y: int, cm) -> None:
    """R_DrawFuzzColumn: sample a neighbour and map through COLORMAP 6."""
    global _fuzzpos
    dest = renderer.ylookup[y] + renderer.columnofs[(x << 1) if renderer.detailshift else x]
    src = dest + _FUZZ_DIR[_fuzzpos] * SCREENWIDTH
    _fuzzpos = (_fuzzpos + 1) % len(_FUZZ_DIR)
    if src < 0 or src >= len(fb):
        src = dest
    pix = fb[src] & 255
    val = cm[pix] if pix < len(cm) else pix
    fb[dest] = val
    if renderer.detailshift and dest + 1 < len(fb):
        fb[dest + 1] = val
