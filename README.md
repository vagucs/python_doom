# doom_python

![DOOM running on Python with pygame](screenshot/doom.png)

**Video:** [DOOM running in Python](https://youtu.be/2JdJ5zfdmkg)

DOOM generic ported from Harbour to **Python 3 + pygame**.

By **Wagner Nunes da Silva**

- vagucs@bol.com.br
- vagucs@vagucs.com.br
- vagucs@gmail.com
- [www.vagucs.com.br](https://www.vagucs.com.br)
- [LinkedIn](https://www.linkedin.com/in/wagner-nunes-da-silva-b0a15360)

This tree is a port of **[harbour_doom](https://github.com/vagucs/harbour_doom)** (`doom_hb`): the same Chocolate Doom / doomgeneric engine that first went from C to Harbour, now from Harbour to Python.

Versão em português: [README.pt.md](README.pt.md)

---

## What this project is

The Chocolate Doom / doomgeneric engine was translated to **Harbour** (`.prg` / `.ch`) with a thin C layer for Allegro 4.2.2. That work lives at [github.com/vagucs/harbour_doom](https://github.com/vagucs/harbour_doom). This directory is the **same study piece again**, in Python:

- Window and blit: **pygame** (no Allegro, no joystick, no CD-Audio, no net)
- Framebuffer: 320×200, 8-bit PLAYPAL, scaled to the window
- Game tick: 35 Hz (`TICRATE`), same as vanilla
- Renderer: BSP, visplanes, `R_DrawColumn` / `R_DrawSpan`, 16.16 `fixed_mul` / `fixed_div`
- Map: VERTEXES, LINEDEFS, SIDEDEFS, SECTORS, SEGS, SSECTORS, NODES, THINGS, BLOCKMAP, REJECT
- Play: walk, doors, lifts, switches, exit, pickups, weapons (including chainsaw raise/cut), status bar, Tab automap, DS* sound, MUS music, ESC menu (options, load/save), intermission tally, melt wipe, monster look/chase/attack

You need a legal IWAD (shareware `doom1.wad` or commercial `doom.wad` / `doom2.wad` / etc.). This repository does not ship commercial WAD data.

It is a **condensed educational port** (~25 Python modules vs 100+ Harbour `.prg` files): playable, Harbour-like speed and behavior, not a 1:1 dump of every thinker table.

Not in this Python tree (same cut as Harbour `boot.prg`, plus a few full-engine pieces still only in Harbour):

- Network, CD music, joystick
- `-colors` palette quantize (Harbour-only experiment)
- Demo playback, bunny scroll, full `info` state tables

---

## Educational purpose

This project is, above all, a **study piece**. DOOM (1993) is small enough to read end to end and dense enough to teach real engine work: BSP rendering, 16.16 fixed-point, a tic-based loop, a WAD file system.

The Harbour port taught how to read C in another language. The Python port makes the next step explicit: there is no preprocessor, no 1-based arrays, and no C bit-ops hiding in `#translate`.

What it is meant to teach:

- **Three languages, one engine.** C (`base_c/` in harbour_doom) → Harbour (`.prg`) → Python (`doom/*.py`). Same names (`P_Thrust`, `R_DrawColumn`, `A_Look`) so you can open the three versions side by side.
- **What pointers were doing.** Python uses objects and lists; wrap-around, BAM angles and 16.16 overflow stay explicit (`as_u32`, `shar`, `fixed_mul`) because Python integers do not wrap.
- **Where an interpreter is enough.** The whole game runs in Python. pygame talks to the window/mixer; numpy speeds the 8-bit→RGB blit and the optional CRT filter.
- **Legacy modernization.** Keep behavior identical, isolate the native layer, verify against the original.

Suggested way to study:

1. Run it, then read `main.py` and `doom/game.py` — boot, tic, input.
2. Compare `doom/compat.py` with Harbour `xhb_compat.prg` / `m_fixed.prg`.
3. Open `doom/render.py` next to `r_main.prg` / `r_bsp.prg` / `r_segs.prg` / `r_draw.prg`.
4. Follow a door from **Space** (`use_lines`) through `doom/specials.py`.
5. Follow a shot from **Ctrl** in `doom/player.py` (`p_pspr`) to `line_attack` and `A_Look`.

---

## From C / Harbour to Python

Python is 0-based, like the C in harbour_doom `base_c/`. Harbour arrays were 1-based; that offset is gone here.

| DOOM in C | Harbour | Python |
|---|---|---|
| `struct` / `typedef struct` | `CLASS ... DATA` | `@dataclass` |
| `thing->x` | `thing:x` | `thing.x` |
| `NULL` | `NIL` | `None` |
| `array[0]` | `array[1]` | `array[0]` |
| `&`, `\|`, `^` | `hb_qbitAnd/Or/Xor` | `&`, `\|`, `^` |
| `x >> n` unsigned | `UShr(x, n)` | `ushr(x, n)` |
| `x >> n` signed | `Shar(x, n)` | `shar(x, n)` |
| 32-bit wrap | `AsU32` / `AsInt32` | `as_u32` / `as_i32` |
| `fixed_t` 16.16 | `FixedMul` / `FixedDiv` | `fixed_mul` / `fixed_div` |
| `byte *` framebuffer | Harbour string | `bytearray` + numpy LUT |
| Allegro 4.2.2 | GTALLEG / llibg | pygame |
| `Z_Malloc` | GC | GC |
| `PUBLIC` globals | `PUBLIC` / `MEMVAR` | fields on `Game` |
| 100+ `.prg` files | 1:1 with C | condensed `doom/*.py` |

### Side-by-side: `P_Thrust`

C (`base_c/p_user.c` in harbour_doom):

```c
void P_Thrust (player_t* player, angle_t angle, fixed_t move)
{
    angle >>= ANGLETOFINESHIFT;
    player->mo->momx += FixedMul(move,finecosine[angle]);
    player->mo->momy += FixedMul(move,finesine[angle]);
}
```

Harbour (`p_user.prg`):

```harbour
PROCEDURE P_Thrust( player, angle, move )
    angle := UShr( angle, ANGLETOFINESHIFT )
    player:mo:momx += FixedMul( move, finecosine[ angle + 1 ] )
    player:mo:momy += FixedMul( move, finesine[ angle + 1 ] )
RETURN
```

Python (`doom/player.py`):

```python
def thrust(mo, angle, move):
    mo.momx += fixed_mul(move, fine_cos(angle))
    mo.momy += fixed_mul(move, fine_sin(angle))
```

`->` becomes `.`, unsigned shift becomes `ushr` (or a fine-table helper), and the Harbour `+ 1` index offset disappears.

---

## Technology

| Layer | This port | Harbour (`harbour_doom`) |
|---|---|---|
| Language | Python 3.10+ (tested on 3.12) | Harbour / xHarbour |
| Window, keys, mixer | pygame 2.x | Allegro 4.2.2 + GTALLEG |
| Palette blit / CRT | numpy | C in `doomgeneric_allegro.prg` |
| IWAD | same WAD lumps | same |
| Build | `pip install -r requirements.txt` | `compile.bat` / `hbmk2` |

Dependencies (`requirements.txt`):

```
pygame>=2.5
numpy>=1.24
```

---

## Performance

Typical blit rate on the same PC (320×200, windowed, shareware IWAD). The game still ticks at 35 Hz (`TICRATE`); `-fps` shows this number.

| Port | Typical FPS |
|---|---|
| Harbour (`doom_hb`) | ~12 |
| Python (`doom_python`) | ~8 |
| PHP (`php_doom`) | ~20 |
| Node (`node_doom`) | ~100 |
| Java (`java_doom`) | ~180 (vsync-locked) |

---

## How to run

Python 3.10+. From this directory:

```
pip install -r requirements.txt
python main.py
python main.py -iwad DOOM1.WAD
python main.py -iwad ..\DOOM1.WAD -warp 1 1 -fps
python main.py -iwad DOOM1.WAD -crt
```

Or `python -m doom` from this folder.

With no `-iwad` it looks for a `.wad` argument, then `doom1.wad` / `DOOM1.WAD` / `doom.wad` / `doom2.wad` in the current directory, `DOOMWADDIR`, and the parent `doom_minimal` folder.

---

## Keys

Classic DOOM controls (this condensed port; not remapped via `default.cfg`).

### Movement and actions

| Key | Action |
|---|---|
| Arrow keys | Forward, back, turn |
| **Shift** | Run |
| **Alt** | Strafe (hold) |
| **,** / **.** | Strafe left / right |
| **Ctrl** | Fire (hold to repeat; weapon animation + `A_ReFire`) |
| **Space** / **E** | Use / open door |
| **1** | Fist / chainsaw (toggle) |
| **2**–**7** | Pistol, shotgun, chaingun, rocket, plasma, BFG |
| **Enter** | Start from the title |
| **Tab** | Automap (toggle). **+** / **-** zoom, **0** fit map, **F** follow, **G** grid, **M** mark, **C** clear marks |
| **Esc** | Menu |
| **F2** | Save |
| **F3** | Load |
| **F11** | Toggle FPS overlay |
| **Alt+Enter** | Fullscreen |
| **+** / **-** | Window scale (1–6); zoom the automap while it is open |

Options **Screen Size** and **Graphic Detail** (HIGH/LOW) change the 3D view (`R_SetViewSize`), not the window scale.

Movement is **arrow keys only** (no WASD), so letter keys stay free for cheat codes.

### Cheats (nostalgia only)

Type these on the keyboard during play; no Enter needed:

| Code | Effect |
|---|---|
| **IDDQD** | God mode (_Degreelessness Mode_) |
| **IDKFA** | All weapons, ammo, keys, and armor |
| **IDDT** | Automap cheat (type while the map is open): all walls, then things |

---

## Command-line parameters

### IWAD

| Parameter | Description |
|---|---|
| `-iwad file.wad` | IWAD to load (path or filename) |
| `file.wad` | Same thing, without `-iwad` |

### Video

| Parameter | Description |
|---|---|
| `-fullscreen` | Start in a fullscreen window |
| `-crt` | CRT filter from Harbour `CrtBuild` / `CrtRender`: tube curvature, scanlines, RGB phosphor mask, vignette. Scanlines/mask show clearly at scale 2× or more |
| `-fps` | Show frames per second at the top-right |

### Game

| Parameter | Description |
|---|---|
| `-warp e m` | Skip the title and start episode `e` map `m` |
| `-skill n` | 0 baby … 4 nightmare (default 2, Hurt Me Plenty) |
| `-nomonsters` | Do not spawn enemies |

Harbour-only flags **not** implemented here: `-videoc`, `-scaling`, `-gfxmode`, `-colors`, `-nosound` / `-nosfx` / `-nomusic`, `-config`, net/CD/joystick.

---

## Layout

```
main.py              entry: python main.py
requirements.txt     pygame, numpy
doom/                engine package
screenshot/doom.png  README screenshot
```

| Path | Vanilla / Harbour |
|---|---|
| `doom/compat.py` | `m_fixed`, `xhb_compat` |
| `doom/wad.py` | `w_wad` |
| `doom/video.py` | `i_video`, `doomgeneric_allegro` (including `-crt`) |
| `doom/v_video.py` | `v_video` |
| `doom/tables.py` | `tables` |
| `doom/r_data.py` | `r_data` |
| `doom/render.py` | `r_main` `r_bsp` `r_segs` `r_plane` `r_draw` |
| `doom/world.py` | `p_setup` |
| `doom/collision.py` | `p_map` `p_maputl` `p_sight` (REJECT) |
| `doom/player.py` | `p_user` `p_pspr` |
| `doom/specials.py` | `p_spec` `p_doors` `p_plats` `p_floor` `p_switch` |
| `doom/mobj.py` | `info` `p_inter` |
| `doom/sprites.py` | `r_things` |
| `doom/enemy.py` | `p_enemy` (look / chase / attack) |
| `doom/status.py` | `st_stuff` |
| `doom/am_map.py` | `am_map` |
| `doom/sound.py` | `i_sound`, `i_allegrosound` CacheSFX |
| `doom/mus2mid.py` | `mus2mid.c` |
| `doom/menu.py` | `m_menu` |
| `doom/saveg.py` | `p_saveg` (24-byte name + JSON) |
| `doom/wi_stuff.py` | `wi_stuff` |
| `doom/wipe.py` | `f_wipe` melt |
| `doom/finale.py` | `f_finale` |
| `doom/game.py` | `d_main` `g_game` `d_loop` `boot` |

---

## Lineage

1. **id Software DOOM** (1993) — original engine
2. **Chocolate Doom / doomgeneric** — portable C
3. **[harbour_doom](https://github.com/vagucs/harbour_doom)** — Harbour + Allegro 4.2.2 (`Doom_hb.exe`)
4. **This tree** — Python + pygame, sourced from that Harbour port (100% of gameplay intent from the `.prg` files; condensed file count)

---

## Donate

### Ethereum

`0x1b64038A2b1DB73ABd0068d8B9B0d1dC5a90C5F1`

![Ethereum QR Code](docs/qr-ethereum.png)

### PIX

Key: `vagucs@bol.com.br`

![PIX QR Code](docs/qr-pix.png)
