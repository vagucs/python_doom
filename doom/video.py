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

import os
import time
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
        self._fps_avg = 0.0
        self._fps_frames = 0
        self._fps_t0: Optional[float] = None
        self.window_title = "DOOM"
        self.crt = False
        self._crt_w = 0
        self._crt_h = 0
        self._crt_map: Optional[np.ndarray] = None
        self._crt_gain: Optional[np.ndarray] = None
        self._crt_mask = np.zeros((3, 3), dtype=np.int32)
        self._mouse_grab = False
        # Reused present buffers (avoid alloc/tobytes every frame).
        self._rgb = np.empty((SCREENHEIGHT, SCREENWIDTH, 3), dtype=np.uint8)
        self._rgb_surf: Optional[pygame.Surface] = None
        self._scaled_surf: Optional[pygame.Surface] = None
        self._scaled_size = (0, 0)
        self._crt_out: Optional[np.ndarray] = None
        self._crt_surf: Optional[pygame.Surface] = None
        self._profile = os.environ.get("DOOM_VIDEO_PROFILE", "").strip() not in ("", "0", "false")
        self._prof_lut = self._prof_scale = self._prof_blit = self._prof_flip = 0.0
        self._prof_n = 0

    def init(self, fullscreen: bool = False, title: str = "DOOM") -> None:
        pygame.display.init()
        pygame.font.init()
        self.fullscreen = fullscreen
        self.window_title = title
        self._apply_mode()
        pygame.display.set_caption(title)
        self._fps_font = pygame.font.SysFont("consolas", 16)
        # frombuffer shares self._rgb memory — keep the ndarray alive.
        self._rgb_surf = pygame.image.frombuffer(
            self._rgb, (SCREENWIDTH, SCREENHEIGHT), "RGB"
        )

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
        self._scaled_surf = None
        self._scaled_size = (0, 0)
        self._crt_surf = None
        self._crt_out = None

    def _ensure_scaled(self, dw: int, dh: int) -> pygame.Surface:
        if self._scaled_surf is None or self._scaled_size != (dw, dh):
            # Same pixel format as frombuffer RGB source (required by transform.scale dest).
            src = self._rgb_surf
            if src is not None:
                self._scaled_surf = pygame.Surface((dw, dh), 0, src)
            else:
                self._scaled_surf = pygame.Surface((dw, dh))
            self._scaled_size = (dw, dh)
        return self._scaled_surf

    def set_relative_mouse(self, enabled: bool) -> None:
        if enabled == self._mouse_grab:
            return
        self._mouse_grab = enabled
        pygame.event.set_grab(enabled)
        pygame.mouse.set_visible(not enabled)
        setter = getattr(pygame.mouse, "set_relative_mode", None)
        if callable(setter):
            try:
                setter(enabled)
            except pygame.error:
                pass

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
        assert self.screen is not None
        assert self._rgb_surf is not None
        dw, dh = self.screen.get_size()
        t0 = t1 = t2 = t3 = t4 = 0.0
        if self._profile:
            t0 = time.perf_counter()

        idx = np.frombuffer(self.fb, dtype=np.uint8).reshape(SCREENHEIGHT, SCREENWIDTH)
        np.take(self._lut, idx, axis=0, out=self._rgb)

        if self._profile:
            t1 = time.perf_counter()

        if self.crt and dw > 0 and dh > 0:
            out = self._crt_present(self._rgb, dw, dh)
            if self._crt_surf is None or self._crt_surf.get_size() != (dw, dh):
                self._crt_surf = pygame.image.frombuffer(out, (dw, dh), "RGB")
            self.screen.blit(self._crt_surf, (0, 0))
            if self._profile:
                t2 = t3 = time.perf_counter()
        else:
            if dw == SCREENWIDTH and dh == SCREENHEIGHT:
                self.screen.blit(self._rgb_surf, (0, 0))
                if self._profile:
                    t2 = t3 = time.perf_counter()
            else:
                scaled = self._ensure_scaled(dw, dh)
                pygame.transform.scale(self._rgb_surf, (dw, dh), scaled)
                if self._profile:
                    t2 = time.perf_counter()
                self.screen.blit(scaled, (0, 0))
                if self._profile:
                    t3 = time.perf_counter()

        if self.show_fps and self._fps_font:
            txt = self._fps_font.render(
                f"{self._fps_value} FPS  avg {self._fps_avg:.1f}",
                True,
                (255, 255, 80),
            )
            r = txt.get_rect()
            r.topright = (self.screen.get_width() - 6, 4)
            self.screen.blit(txt, r)

        pygame.display.flip()
        if self._profile:
            t4 = time.perf_counter()
            self._prof_lut += t1 - t0
            self._prof_scale += t2 - t1
            self._prof_blit += t3 - t2
            self._prof_flip += t4 - t3
            self._prof_n += 1
            if self._prof_n >= 300:
                n = self._prof_n
                print(
                    f"video present avg ms: lut={1000*self._prof_lut/n:.2f} "
                    f"scale={1000*self._prof_scale/n:.2f} "
                    f"blit={1000*self._prof_blit/n:.2f} "
                    f"flip={1000*self._prof_flip/n:.2f} "
                    f"(n={n})",
                    flush=True,
                )
                self._prof_lut = self._prof_scale = self._prof_blit = self._prof_flip = 0.0
                self._prof_n = 0

        self._fps_value = int(self._clock.get_fps())
        if self.show_fps:
            now = time.perf_counter()
            if self._fps_t0 is None:
                self._fps_t0 = now
                self._fps_frames = 0
            self._fps_frames += 1
            elapsed = now - self._fps_t0
            if elapsed > 0.0:
                self._fps_avg = self._fps_frames / elapsed
        else:
            self._fps_t0 = None
            self._fps_frames = 0
            self._fps_avg = 0.0
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
        out = np.ascontiguousarray(out)
        if self._crt_out is None or self._crt_out.shape != out.shape:
            self._crt_out = out
            self._crt_surf = None
        else:
            self._crt_out[:] = out
        return self._crt_out

    def ticks_ms(self) -> int:
        return pygame.time.get_ticks()
