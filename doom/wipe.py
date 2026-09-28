"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

Screen melt (f_wipe.prg wipe_Melt). Old frame drips down, new one fills from the top.
"""

from __future__ import annotations

import random

import numpy as np

from .defs import SCREENHEIGHT, SCREENWIDTH

COLW = SCREENWIDTH // 2


class Wipe:
    def __init__(self) -> None:
        self.start = np.zeros((SCREENHEIGHT, SCREENWIDTH), dtype=np.uint8)
        self.end = np.zeros((SCREENHEIGHT, SCREENWIDTH), dtype=np.uint8)
        self.y = [0] * COLW
        self.active = False

    def capture_start(self, fb: bytearray) -> None:
        self.start = np.frombuffer(bytes(fb), dtype=np.uint8).reshape(
            SCREENHEIGHT, SCREENWIDTH
        ).copy()

    def capture_end(self, fb: bytearray) -> None:
        self.end = np.frombuffer(bytes(fb), dtype=np.uint8).reshape(
            SCREENHEIGHT, SCREENWIDTH
        ).copy()

    def begin(self, fb: bytearray) -> None:
        """Restore the old frame and set per-column delays (wipe_initMelt)."""
        fb[:] = self.start.tobytes()
        self.y = [0] * COLW
        self.y[0] = -(random.randrange(16))
        for i in range(1, COLW):
            r = random.randrange(3) - 1
            ny = self.y[i - 1] + r
            if ny > 0:
                ny = 0
            elif ny == -16:
                ny = -15
            self.y[i] = ny
        self.active = True

    def tick(self, tics: int, fb: bytearray) -> bool:
        dest = np.frombuffer(fb, dtype=np.uint8).reshape(SCREENHEIGHT, SCREENWIDTH)
        h = SCREENHEIGHT
        done = True
        for _ in range(max(1, tics)):
            for i in range(COLW):
                yi = self.y[i]
                x0 = i * 2
                if yi < 0:
                    dest[:, x0 : x0 + 2] = self.start[:, x0 : x0 + 2]
                    self.y[i] = yi + 1
                    done = False
                    continue
                if yi >= h:
                    continue
                dy = yi + 1 if yi < 16 else 8
                if yi + dy > h:
                    dy = h - yi
                dest[yi : yi + dy, x0 : x0 + 2] = self.end[yi : yi + dy, x0 : x0 + 2]
                yi += dy
                self.y[i] = yi
                rem = h - yi
                if rem > 0:
                    dest[yi:h, x0 : x0 + 2] = self.start[0:rem, x0 : x0 + 2]
                done = False
        if done:
            dest[:, :] = self.end
            self.active = False
        return done
