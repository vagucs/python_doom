"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

default.cfg subset (m_misc): mouse, volumes, messages, screenblocks.
"""

from __future__ import annotations

import os


def config_path() -> str:
    return os.path.join(os.getcwd(), "default.cfg")


def load(game) -> None:
    path = config_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        key, val = parts[0], parts[1]
        try:
            n = int(val)
        except ValueError:
            continue
        if key == "mouse_sensitivity":
            game.mouse_sensitivity = max(0, min(9, n))
        elif key == "sfx_volume":
            game.sound.sfx_volume = max(0, min(15, n))
        elif key == "music_volume":
            game.sound.music_volume = max(0, min(15, n))
        elif key == "show_messages":
            game.show_messages = n != 0
        elif key == "use_mouse":
            game.use_mouse = n != 0
        elif key == "screenblocks":
            game.screen_size = max(0, min(8, n - 3))


def save(game) -> None:
    path = config_path()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"mouse_sensitivity\t\t{int(game.mouse_sensitivity)}\n")
            fh.write(f"sfx_volume\t\t{int(game.sound.sfx_volume)}\n")
            fh.write(f"music_volume\t\t{int(game.sound.music_volume)}\n")
            fh.write(f"show_messages\t\t{1 if game.show_messages else 0}\n")
            fh.write(f"use_mouse\t\t{1 if game.use_mouse else 0}\n")
            fh.write(f"screenblocks\t\t{int(game.screen_size) + 3}\n")
    except OSError:
        pass
