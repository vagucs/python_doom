"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

finesine / finetangent / tantoangle — exact vanilla tables.c values.
"""

from __future__ import annotations

from .compat import as_u32
from .defs import (
    ANGLETOFINESHIFT,
    FINEANGLES,
    FINEMASK,
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
    from .tables_data import FINESINE, FINETANGENT, TANTOANGLE

    finesine[:] = FINESINE
    # cosine is sine shifted by ANG90 >> ANGLETOFINESHIFT = 2048 (no wrap).
    finecosine[:] = finesine[FINEANGLES // 4 : FINEANGLES // 4 + FINEANGLES]
    finetangent[:] = FINETANGENT
    tantoangle[:] = TANTOANGLE


def fine_sin(angle: int) -> int:
    return finesine[(as_u32(angle) >> ANGLETOFINESHIFT) & FINEMASK]


def fine_cos(angle: int) -> int:
    # Harbour/vanilla: finecosine[i] == finesine[i + FINEANGLES/4] (extended table, no FINEMASK).
    idx = (as_u32(angle) >> ANGLETOFINESHIFT) & FINEMASK
    return finesine[idx + FINEANGLES // 4]


def slope_div(num: int, den: int) -> int:
    if den < 512:
        return SLOPERANGE
    ans = (num << 3) // (den >> 8)
    return SLOPERANGE if ans > SLOPERANGE else ans
