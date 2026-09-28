"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

finesine / finetangent / tantoangle (tables.c generated at runtime).
"""

from __future__ import annotations

import math

from .compat import as_u32, fixed_div
from .defs import (
    ANGLETOFINESHIFT,
    ANG90,
    DBITS,
    FINEANGLES,
    FINEMASK,
    FRACUNIT,
    SLOPERANGE,
)

finesine: list[int] = []
finecosine: list[int] = []
finetangent: list[int] = []
tantoangle: list[int] = []


def init_tables() -> None:
    global finesine, finecosine, finetangent, tantoangle
    if finesine:
        return
    built_sin = [0] * (FINEANGLES // 4 * 5)
    for i in range(FINEANGLES // 4 * 5):
        a = (i + 0.5) * math.pi * 2 / FINEANGLES
        built_sin[i] = int(FRACUNIT * math.sin(a))
    finesine[:] = built_sin
    # cosine is sine shifted by ANG90 >> ANGLETOFINESHIFT = 2048
    finecosine[:] = finesine[FINEANGLES // 4 :]
    built_tan = [0] * (FINEANGLES // 2)
    for i in range(FINEANGLES // 2):
        a = (i - FINEANGLES // 4 + 0.5) * math.pi * 2 / FINEANGLES
        try:
            v = int(FRACUNIT * math.tan(a))
        except ValueError:
            v = 0x7FFFFFFF if a > 0 else -0x7FFFFFFF
        if v > 0x7FFFFFFF:
            v = 0x7FFFFFFF
        elif v < -0x7FFFFFFF:
            v = -0x7FFFFFFF
        built_tan[i] = v
    finetangent[:] = built_tan
    built_ang = [0] * (SLOPERANGE + 1)
    for i in range(SLOPERANGE + 1):
        built_ang[i] = as_u32(int(math.atan(i / SLOPERANGE) / (math.pi * 2) * 0xFFFFFFFF))
    tantoangle[:] = built_ang


def fine_sin(angle: int) -> int:
    return finesine[(as_u32(angle) >> ANGLETOFINESHIFT) & FINEMASK]


def fine_cos(angle: int) -> int:
    return finesine[((as_u32(angle) >> ANGLETOFINESHIFT) + FINEANGLES // 4) & FINEMASK]


def slope_div(num: int, den: int) -> int:
    if den < 512:
        return SLOPERANGE
    ans = (num << 3) // (den >> 8)
    return SLOPERANGE if ans > SLOPERANGE else ans
