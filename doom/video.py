"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

pygame video: 320x200 paletted framebuffer scaled to window (doomgeneric_allegro).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pygame

from .defs import SCREENHEIGHT, SCREENWIDTH

SCALE_MIN = 1
SCALE_MAX = 6


class Video:
    def __init__(self) -> None:
        self.fb = bytearray(SCREENWIDTH * SCREENHEIGHT)
        self.palette = [(0, 0, 0)] * 256
        self._lut = np.zeros((256, 3), dtype=np.uint8)
        self.screen: Optional[pygame.Surface] = None
        self._clock = pygame.time.Clock()
        self.fullscreen = False
        self.scale = 2
        self.show_fps = False
        self._fps_font: Optional[pygame.font.Font] = None
        self._fps_value = 0
        self.window_title = "DOOM"
        self.crt = False
        self._crt_w = 0
        self._crt_h = 0
        self._crt_map: Optional[np.ndarray] = None
        self._crt_gain: Optional[np.ndarray] = None
        self._crt_mask = np.zeros((3, 3), dtype=np.int32)

    def init(self, fullscreen: bool = False, title: str = "DOOM") -> None:
        pygame.display.init()
        pygame.font.init()
        self.fullscreen = fullscreen
        self.window_title = title
        self._apply_mode()
        pygame.display.set_caption(title)
        self._fps_font = pygame.font.SysFont("consolas", 16)

    def _apply_mode(self) -> None:
        try:
            if self.fullscreen:
                flags = pygame.FULLSCREEN | pygame.SCALED
                self.screen = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT), flags)
            else:
                w = SCREENWIDTH * self.scale
                h = SCREENHEIGHT * self.scale
                self.screen = pygame.display.set_mode((w, h))
        except pygame.error:
            flags = pygame.FULLSCREEN if self.fullscreen else 0
            if self.fullscreen:
                self.screen = pygame.display.set_mode((0, 0), flags)
            else:
                w = SCREENWIDTH * self.scale
                h = SCREENHEIGHT * self.scale
                self.screen = pygame.display.set_mode((w, h), flags)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self._apply_mode()
        pygame.display.set_caption(self.window_title)

    def change_scale(self, delta: int) -> bool:
        if self.fullscreen:
            return False
        new = max(SCALE_MIN, min(SCALE_MAX, self.scale + delta))
        if new == self.scale:
            return False
        self.scale = new
        self._apply_mode()
        pygame.display.set_caption(self.window_title)
        return True

    def set_palette(self, playpal: bytes, gamma: int = 0) -> None:
        pal = playpal[:768]
        colors = []
        for i in range(256):
            r, g, b = pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]
            colors.append((r, g, b))
            self._lut[i] = (r, g, b)
        self.palette = colors

    def set_palette_raw(self, rgb768: bytes) -> None:
        for i in range(256):
            r, g, b = rgb768[i * 3], rgb768[i * 3 + 1], rgb768[i * 3 + 2]
            self.palette[i] = (r, g, b)
            self._lut[i] = (r, g, b)

    def present(self) -> None:
        idx = np.frombuffer(self.fb, dtype=np.uint8).reshape(SCREENHEIGHT, SCREENWIDTH)
        rgb = self._lut[idx]
        assert self.screen is not None
        dw, dh = self.screen.get_size()
        if self.crt and dw > 0 and dh > 0:
            out = self._crt_present(rgb, dw, dh)
            surf = pygame.image.frombuffer(out.tobytes(), (dw, dh), "RGB")
            self.screen.blit(surf, (0, 0))
        else:
            surf = pygame.image.frombuffer(rgb.tobytes(), (SCREENWIDTH, SCREENHEIGHT), "RGB")
            scaled = pygame.transform.scale(surf, (dw, dh))
            self.screen.blit(scaled, (0, 0))
        if self.show_fps and self._fps_font:
            txt = self._fps_font.render(f"{self._fps_value} FPS", True, (255, 255, 80))
            r = txt.get_rect()
            r.topright = (self.screen.get_width() - 6, 4)
            self.screen.blit(txt, r)
        pygame.display.flip()
        self._fps_value = int(self._clock.get_fps())
        self._clock.tick()

    def _crt_build(self, dw: int, dh: int) -> None:
        """Harbour CrtBuild: barrel map + vignette/scanline gain + RGB phosphor mask."""
        if self._crt_map is not None and self._crt_w == dw and self._crt_h == dh:
            return
        y = np.arange(dh, dtype=np.float64)
        x = np.arange(dw, dtype=np.float64)
        ny = 2.0 * y / dh - 1.0
        nx = 2.0 * (x + 0.5) / dw - 1.0
        u = nx[None, :] * (1.0 + (ny[:, None] ** 2) / 32.0)
        v = ny[:, None] * (1.0 + (nx[None, :] ** 2) / 24.0)
        outside = (u <= -1.0) | (u >= 1.0) | (v <= -1.0) | (v >= 1.0)
        sx = (u + 1.0) * 0.5 * SCREENWIDTH
        sy = (v + 1.0) * 0.5 * SCREENHEIGHT
        ix = np.clip(sx.astype(np.int32), 0, SCREENWIDTH - 1)
        iy = np.clip(sy.astype(np.int32), 0, SCREENHEIGHT - 1)
        sl = min(max(dh / SCREENHEIGHT - 1.0, 0.0), 1.0) * 0.45
        d = (sy - iy) - 0.5
        uu = (u + 1.0) * 0.5
        vv = (v + 1.0) * 0.5
        vignette = np.clip(16.0 * uu * vv * (1.0 - uu) * (1.0 - vv), 0.0, None)
        g = (1.0 - sl * 4.0 * d * d) * np.power(np.maximum(vignette, 1e-20), 0.12) * 255.0
        g = np.clip(g, 0.0, 255.0)
        mapping = (iy * SCREENWIDTH + ix).astype(np.uint16)
        mapping[outside] = np.uint16(0xFFFF)
        self._crt_map = mapping
        self._crt_gain = np.where(outside, 0, g + 0.5).astype(np.uint8)
        self._crt_w = dw
        self._crt_h = dh
        if dw >= 2 * SCREENWIDTH:
            off, boost = 0.70, 1.40
        else:
            off, boost = 1.0, 1.15
        mask = np.zeros((3, 3), dtype=np.int32)
        for m in range(3):
            for c in range(3):
                mask[m, c] = int(256.0 * boost * (1.0 if m == c else off))
        self._crt_mask = mask

    def _crt_present(self, rgb: np.ndarray, dw: int, dh: int) -> np.ndarray:
        """Harbour CrtRender: 1-2-1 horizontal bleed, then map/gain/mask."""
        self._crt_build(dw, dh)
        src = rgb.astype(np.uint16)
        left = np.empty_like(src)
        left[:, 0] = src[:, 0]
        left[:, 1:] = src[:, :-1]
        right = np.empty_like(src)
        right[:, -1] = src[:, -1]
        right[:, :-1] = src[:, 1:]
        blur = ((left + src * 2 + right) >> 2).astype(np.uint8).reshape(-1, 3)
        idx = self._crt_map.astype(np.int32)
        hole = idx == 0xFFFF
        pix = blur[np.where(hole, 0, idx)]
        gain = self._crt_gain.astype(np.uint32)[..., None]
        mk = self._crt_mask[np.arange(dw) % 3]
        out = (pix.astype(np.uint32) * gain * mk[None, :, :]) >> 16
        out = np.clip(out, 0, 255).astype(np.uint8)
        out[hole] = 0
        return np.ascontiguousarray(out)

    def ticks_ms(self) -> int:
        return pygame.time.get_ticks()
