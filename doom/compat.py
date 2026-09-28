"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

32-bit wrap, shifts and 16.16 fixed-point (Harbour xhb_compat / m_fixed).
"""

from .defs import FRACBITS, FRACUNIT

MASK32 = 0xFFFFFFFF
MASK31 = 0x7FFFFFFF


def as_u32(n: int) -> int:
    return n & MASK32


def as_i32(n: int) -> int:
    n = n & MASK32
    if n >= 0x80000000:
        return n - 0x100000000
    return n


def ushr(n: int, bits: int) -> int:
    n = n & MASK32
    if bits <= 0:
        return n
    if bits >= 32:
        return 0
    return n >> bits


def shar(n: int, bits: int) -> int:
    n = as_i32(n)
    if bits <= 0:
        return n
    if bits >= 31:
        return -1 if n < 0 else 0
    return n >> bits


def fixed_mul(a: int, b: int) -> int:
    return as_i32((as_i32(a) * as_i32(b)) >> FRACBITS)


def fixed_div(a: int, b: int) -> int:
    a = as_i32(a)
    b = as_i32(b)
    if b == 0:
        return 0x7FFFFFFF if a >= 0 else as_i32(-0x80000000)
    abs_a = -a if a < 0 else a
    abs_b = -b if b < 0 else b
    if (abs_a >> 14) >= abs_b:
        return as_i32(-0x80000000) if (a ^ b) < 0 else 0x7FFFFFFF
    return as_i32((a << 16) // b)


def abs_fixed(n: int) -> int:
    n = as_i32(n)
    return -n if n < 0 else n
