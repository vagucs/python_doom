"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

V_DrawPatch and helpers (v_video.prg) on a bytearray framebuffer.
"""

from __future__ import annotations

import struct

from .defs import SCREENHEIGHT, SCREENWIDTH


def _i16(data: bytes, off: int) -> int:
    v = struct.unpack_from("<H", data, off)[0]
    return v - 65536 if v >= 32768 else v


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def patch_size(patch: bytes) -> tuple[int, int, int, int]:
    w, h, left, top = struct.unpack_from("<hhhh", patch, 0)
    return w, h, left, top


def draw_patch(fb: bytearray, x: int, y: int, patch: bytes, flipped: bool = False) -> None:
    w, h, left, top = patch_size(patch)
    x -= left
    y -= top
    desttop = y * SCREENWIDTH + x
    for col in range(w):
        src_col = w - 1 - col if flipped else col
        column = _u32(patch, 8 + src_col * 4)
        while column < len(patch):
            topdelta = patch[column]
            if topdelta == 0xFF:
                break
            length = patch[column + 1]
            source = column + 3
            dest = desttop + topdelta * SCREENWIDTH
            for _ in range(length):
                if 0 <= dest < SCREENWIDTH * SCREENHEIGHT:
                    fb[dest] = patch[source]
                source += 1
                dest += SCREENWIDTH
            column += length + 4
        desttop += 1


def draw_patch_direct(fb: bytearray, x: int, y: int, patch: bytes) -> None:
    draw_patch(fb, x, y, patch)


def copy_rect(
    dest: bytearray,
    src: bytes | bytearray,
    srcx: int,
    srcy: int,
    width: int,
    height: int,
    destx: int,
    desty: int,
) -> None:
    for row in range(height):
        s = (srcy + row) * SCREENWIDTH + srcx
        d = (desty + row) * SCREENWIDTH + destx
        dest[d : d + width] = src[s : s + width]


def fill(fb: bytearray, color: int = 0) -> None:
    fb[:] = bytes([color & 0xFF]) * len(fb)
