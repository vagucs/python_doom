# python_doom

![DOOM rodando em Python com pygame](screenshot/doom.png)

**Vídeo:** [DOOM rodando em Python](https://youtu.be/2JdJ5zfdmkg)

DOOM generic portado de Harbour para **Python 3 + pygame**.

Por **Wagner Nunes da Silva**

- vagucs@bol.com.br
- vagucs@vagucs.com.br
- vagucs@gmail.com
- [www.vagucs.com.br](https://www.vagucs.com.br)
- [LinkedIn](https://www.linkedin.com/in/wagner-nunes-da-silva-b0a15360)

O mesmo motor em outras linguagens: [harbour_doom](https://github.com/vagucs/harbour_doom) · [python_doom](https://github.com/vagucs/python_doom) · [php_doom](https://github.com/vagucs/php_doom) · [node_doom](https://github.com/vagucs/node_doom) · [java_doom](https://github.com/vagucs/java_doom)

Esta árvore é um port de **[harbour_doom](https://github.com/vagucs/harbour_doom)** (`doom_hb`): o mesmo motor Chocolate Doom / doomgeneric que primeiro foi de C para Harbour, agora de Harbour para Python.

English version: [README.md](README.md)

---

## O que é este projeto

O motor do Chocolate Doom / doomgeneric foi traduzido para **Harbour** (`.prg` / `.ch`) com uma camada fina de C para Allegro 4.2.2. Esse trabalho está em [github.com/vagucs/harbour_doom](https://github.com/vagucs/harbour_doom). Este diretório é o **mesmo material de estudo**, em Python:

- Janela e blit: **pygame** (sem Allegro, sem joystick, sem CD-Audio, sem rede)
- Framebuffer: 320×200, 8 bits PLAYPAL, escalado para a janela
- Tic do jogo: 35 Hz (`TICRATE`), igual ao vanilla
- Renderer: BSP, visplanes, `R_DrawColumn` / `R_DrawSpan`, ponto fixo 16.16 `fixed_mul` / `fixed_div`
- Mapa: VERTEXES, LINEDEFS, SIDEDEFS, SECTORS, SEGS, SSECTORS, NODES, THINGS, BLOCKMAP, REJECT
- Jogo: andar, portas, plataformas, interruptores, saída, itens, armas (incluindo motosserra subindo/cortando), barra de status, automap com Tab, som DS*, música MUS, menu ESC (opções, load/save), totalização no intermission, wipe derretendo, inimigos em look/chase/ataque

É necessário um IWAD legal (shareware `doom1.wad` ou comercial `doom.wad` / `doom2.wad` / etc.). Este repositório não distribui WAD comercial.

É um **port educacional condensado** (~25 módulos Python vs 100+ `.prg` Harbour): jogável, com velocidade e comportamento próximos do Harbour, não um dump 1:1 de todas as tabelas de thinkers.

O que não entra nesta árvore Python (o mesmo corte do `boot.prg` Harbour, mais algumas peças do motor completo que ainda só existem no Harbour):

- Rede, música de CD, joystick
- Quantização de paleta `-colors` (experimento só no Harbour)
- Playback de demo, bunny scroll, tabelas `info` completas

---

## Proposta educacional

Este projeto é, antes de tudo, um **material de estudo**. O DOOM (1993) é pequeno o bastante para ser lido de ponta a ponta e denso o bastante para ensinar engenharia de verdade: renderização por BSP, ponto fixo 16.16, laço por tics, sistema de arquivos WAD.

O port Harbour ensinou a ler C com os olhos de outra linguagem. O port Python dá o passo seguinte: não há pré-processador, arrays não começam em 1, e as operações de bit não se escondem num `#translate`.

O que o port pretende ensinar:

- **Seis linguagens, um motor.** C (`base_c/` no harbour_doom) → Harbour ([harbour_doom](https://github.com/vagucs/harbour_doom)) → Python ([python_doom](https://github.com/vagucs/python_doom)) → PHP ([php_doom](https://github.com/vagucs/php_doom)) → TypeScript ([node_doom](https://github.com/vagucs/node_doom)) → Java ([java_doom](https://github.com/vagucs/java_doom)). Os mesmos nomes (`P_Thrust`, `R_DrawColumn`, `A_Look`) para abrir as versões lado a lado.
- **O que os ponteiros faziam.** Python usa objetos e listas; wrap-around, ângulos BAM e overflow 16.16 continuam explícitos (`as_u32`, `shar`, `fixed_mul`) porque inteiros em Python não estouram.
- **Onde um interpretador basta.** O jogo inteiro roda em Python. O pygame fala com a janela/mixer; o numpy acelera o blit 8-bit→RGB e o filtro CRT opcional.
- **Modernização de legado.** Manter o comportamento idêntico, isolar a camada nativa, conferir contra o original.

Sugestão de roteiro:

1. Rode o jogo e leia `main.py` e `doom/game.py` — boot, tic, input.
2. Compare `doom/compat.py` com o Harbour `xhb_compat.prg` / `m_fixed.prg`.
3. Abra `doom/render.py` ao lado de `r_main.prg` / `r_bsp.prg` / `r_segs.prg` / `r_draw.prg`.
4. Siga uma porta a partir do **Espaço** (`use_lines`) até `doom/specials.py`.
5. Siga um tiro a partir do **Ctrl** em `doom/player.py` (`p_pspr`) até `line_attack` e `A_Look`.

---

## De C / Harbour para Python

Python é 0-based, como o C em `base_c/` do harbour_doom. Arrays Harbour eram 1-based; esse deslocamento some aqui.

A tabela abaixo é a mesma comparação em seis linguagens usada em todos os README `*_doom`:

| DOOM em C | [Harbour](https://github.com/vagucs/harbour_doom) | [Python](https://github.com/vagucs/python_doom) | [PHP](https://github.com/vagucs/php_doom) | [Node](https://github.com/vagucs/node_doom) | [Java](https://github.com/vagucs/java_doom) |
|---|---|---|---|---|---|
| `struct` / `typedef struct` | `CLASS ... DATA` | `@dataclass` | `class` + propriedades tipadas | `class` + campos tipados | `class` + campos |
| `thing->x` | `thing:x` | `thing.x` | `$thing->x` | `thing.x` | `thing.x` |
| `NULL` | `NIL` | `None` | `null` | `null` | `null` |
| `array[0]` | `array[1]` | `array[0]` | `$array[0]` | `array[0]` | `array[0]` |
| `&`, `\|`, `^` | `hb_qbitAnd/Or/Xor` | `&`, `\|`, `^` | `&`, `\|`, `^` | `&`, `\|`, `^` | `&`, `\|`, `^` |
| `x >> n` sem sinal | `UShr(x, n)` | `ushr(x, n)` | `Compat::ushr($x, $n)` | `ushr(x, n)` | `Compat.ushr` / `>>>` |
| `x >> n` com sinal | `Shar(x, n)` | `shar(x, n)` | `Compat::shar($x, $n)` | `shar(x, n)` | `Compat.shar` / `>>` |
| estouro de 32 bits | `AsU32` / `AsInt32` | `as_u32` / `as_i32` | `Compat::asU32` / `asI32` | `asU32` / `asI32` | `int` já faz wrap |
| `fixed_t` 16.16 | `FixedMul` / `FixedDiv` | `fixed_mul` / `fixed_div` | `Compat::fixedMul` / `fixedDiv` | `fixedMul` / `fixedDiv` (BigInt) | `fixedMul` / `fixedDiv` (`long`) |
| framebuffer `byte *` | string Harbour | `bytearray` + LUT numpy | `array<int>` + SDL ARGB8888 | `Uint8Array` + SDL ARGB8888 | `int[]` + SDL ARGB8888 |
| Allegro 4.2.2 | GTALLEG / llibg | pygame | SDL2 via FFI | SDL2 via koffi | SDL2 via JNA |
| `Z_Malloc` | GC | GC | GC | GC | GC |
| globais `PUBLIC` | `PUBLIC` / `MEMVAR` | campos em `Game` | campos públicos em `Game` | campos públicos em `Game` | campos públicos em `Game` |
| 100+ arquivos `.prg` | 1:1 com o C | `doom/*.py` condensado | `src/*.php` condensado | `src/*.ts` condensado | `src/doom/*.java` condensado |

### Lado a lado: `P_Thrust`

C (`base_c/p_user.c` no harbour_doom):

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

`->` vira `.`, o shift sem sinal vira `ushr` (ou um helper da tabela fine), e o `+ 1` do índice Harbour desaparece.

---

## Tecnologia

| Camada | Este port | Harbour (`harbour_doom`) |
|---|---|---|
| Linguagem | Python 3.10+ (testado no 3.12) | Harbour / xHarbour |
| Janela, teclas, mixer | pygame 2.x | Allegro 4.2.2 + GTALLEG |
| Blit da paleta / CRT | numpy | C em `doomgeneric_allegro.prg` |
| IWAD | os mesmos lumps | os mesmos |
| Build | `pip install -r requirements.txt` | `compile.bat` / `hbmk2` |

Dependências (`requirements.txt`):

```
pygame>=2.5
numpy>=1.24
```

---

## Desempenho

Taxa típica de desenho no mesmo PC (320×200, janela, IWAD shareware). O jogo continua em 35 Hz (`TICRATE`); `-fps` mostra esse número.

| Port | FPS típico |
|---|---|
| Harbour (`doom_hb`) | ~12 |
| Python (`python_doom`) | ~8 |
| PHP (`php_doom`) | ~20 |
| Node (`node_doom`) | ~100 |
| Java (`java_doom`) | ~180 (travado no vsync) |

---

## Como rodar

Python 3.10+. Neste diretório:

```
pip install -r requirements.txt
python main.py
python main.py -iwad DOOM1.WAD
python main.py -iwad ..\DOOM1.WAD -warp 1 1 -fps
python main.py -iwad DOOM1.WAD -crt
```

Ou `python -m doom` nesta pasta.

Sem `-iwad` procura um argumento `.wad`, depois `doom1.wad` / `DOOM1.WAD` / `doom.wad` / `doom2.wad` no diretório atual, em `DOOMWADDIR` e na pasta pai `doom_minimal`.

---

## Teclas

Controles clássicos do DOOM (este port condensado; sem remap via `default.cfg`).

### Movimento e ações

| Tecla | Ação |
|---|---|
| Setas | Frente, trás, girar |
| **Shift** | Correr |
| **Alt** | Strafe (segurar) |
| **,** / **.** | Strafe esquerda / direita |
| **Ctrl** | Atirar (segurar repete; animação da arma + `A_ReFire`) |
| **Espaço** / **E** | Usar / abrir porta |
| **1** | Punho / motosserra (alterna) |
| **2**–**7** | Pistola, shotgun, chaingun, foguete, plasma, BFG |
| **Enter** | Começar a partir do título |
| **Tab** | Automap (liga/desliga). **+** / **-** zoom, **0** encaixa o mapa, **F** follow, **G** grade, **M** marca, **C** limpa marcas |
| **Esc** | Menu |
| **F2** | Salvar |
| **F3** | Carregar |
| **F11** | Liga/desliga FPS |
| **Alt+Enter** | Tela cheia |
| **+** / **-** | Escala da janela (1–6); zoom do automap enquanto ele está aberto |

As opções **Screen Size** e **Graphic Detail** (HIGH/LOW) mudam a vista 3D (`R_SetViewSize`), não a escala da janela.

O movimento usa **somente as setas** (sem WASD), para as letras ficarem livres para os cheats.

### Cheats (só nostalgia)

Digite no teclado durante o jogo; não precisa de Enter. No skill Nightmare só **IDCLEV** e **IDDT** funcionam (vanilla).

| Código | Efeito |
|---|---|
| **IDDQD** | Modo Deus (_Degreelessness Mode_) |
| **IDKFA** | Todas as armas, munição, chaves e armadura |
| **IDFA** | Armas, munição e armadura (sem chaves) |
| **IDCLIP** / **IDSPISPOPD** | Sem colisão |
| **IDDT** | Cheat do automap (digite com o mapa aberto): todas as paredes, depois os things |
| **IDBEHOLD** | Lista os power-ups; em seguida **V** invulnerabilidade, **S** berserk, **I** invisibilidade, **R** traje anti-radiação, **A** mapa do computador, **L** visor de luz |
| **IDCHOPPERS** | Motosserra |
| **IDMYPOS** | Mostra ângulo e coordenadas |
| **IDCLEV** + 2 dígitos | Warp (`11` = E1M1 ou MAP11) |
| **IDMUS** + 2 dígitos | Troca a música (`11` = faixa de E1M1 / MAP11) |

---

## Parâmetros de linha de comando

### IWAD

| Parâmetro | Descrição |
|---|---|
| `-iwad arquivo.wad` | IWAD a carregar (caminho ou só o nome) |
| `arquivo.wad` | Mesmo efeito, sem `-iwad` |

### Vídeo

| Parâmetro | Descrição |
|---|---|
| `-fullscreen` | Começa em janela de tela cheia |
| `-crt` | Filtro CRT do Harbour `CrtBuild` / `CrtRender`: curvatura do tubo, scanlines, máscara RGB de fósforo, vinheta. Scanlines/máscara ficam nítidas em escala 2× ou maior |
| `-fps` | Mostra os quadros por segundo no canto superior direito |

### Jogo

| Parâmetro | Descrição |
|---|---|
| `-warp e m` | Pula o título e começa no episódio `e` mapa `m` |
| `-skill n` | 0 baby … 4 nightmare (padrão 2, Hurt Me Plenty) |
| `-nomonsters` | Não spawna inimigos |
| `-fast` | Monstros mais rápidos (vanilla `-fast`) |
| `-respawn` | Respawn estilo nightmare |
| `-file wad [wad…]` | PWADs extras depois do IWAD |
| `-record nome` | Grava demo em `nome.lmp` |
| `-playdemo nome` | Toca lump ou `.lmp` e sai |
| `-timedemo nome` | Playback o mais rápido possível e imprime FPS |
| `-nosound` | Desliga SFX e música |
| `-nomusic` | Desliga só a música |

`default.cfg` no diretório de trabalho guarda `mouse_sensitivity`, `sfx_volume`, `music_volume`, `show_messages`, `use_mouse`, `screenblocks`. Mouse virar/andar usa movimento relativo do pygame quando `use_mouse` está ligado. Saves continuam JSON (save binário vanilla não é usado).

Flags só do Harbour **não** implementadas aqui: `-videoc`, `-scaling`, `-gfxmode`, `-colors`, rede/CD/joystick.

---

## Estrutura

```
main.py              entrada: python main.py
requirements.txt     pygame, numpy
doom/                pacote do motor
screenshot/doom.png  screenshot do README
```

| Caminho | Vanilla / Harbour |
|---|---|
| `doom/compat.py` | `m_fixed`, `xhb_compat` |
| `doom/wad.py` | `w_wad` |
| `doom/video.py` | `i_video`, `doomgeneric_allegro` (incluindo `-crt`) |
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
| `doom/enemy.py` | `p_enemy` (look / chase / ataque) |
| `doom/status.py` | `st_stuff` |
| `doom/am_map.py` | `am_map` |
| `doom/sound.py` | `i_sound`, `i_allegrosound` CacheSFX |
| `doom/mus2mid.py` | `mus2mid.c` |
| `doom/menu.py` | `m_menu` |
| `doom/saveg.py` | `p_saveg` (nome de 24 bytes + JSON) |
| `doom/wi_stuff.py` | `wi_stuff` |
| `doom/wipe.py` | `f_wipe` melt |
| `doom/finale.py` | `f_finale` |
| `doom/game.py` | `d_main` `g_game` `d_loop` `boot` |

---

## Linhagem

1. **id Software DOOM** (1993) — motor original
2. **Chocolate Doom / doomgeneric** — C portátil
3. **[harbour_doom](https://github.com/vagucs/harbour_doom)** — Harbour + Allegro 4.2.2 (`Doom_hb.exe`)
4. **[python_doom](https://github.com/vagucs/python_doom)** — Python + pygame (esta árvore)
5. **[php_doom](https://github.com/vagucs/php_doom)** — PHP 8 CLI + SDL2 FFI
6. **[node_doom](https://github.com/vagucs/node_doom)** — Node.js CLI + TypeScript + SDL2 (koffi)
7. **[java_doom](https://github.com/vagucs/java_doom)** — Java 17 CLI + SDL2 (JNA)

---

## Doe

### Patrocínio no GitHub

[github.com/sponsors/vagucs](https://github.com/sponsors/vagucs)

### Ethereum

`0x1b64038A2b1DB73ABd0068d8B9B0d1dC5a90C5F1`

![QR Code Ethereum](docs/qr-ethereum.png)

### PIX

Chave: `vagucs@bol.com.br`

![QR Code PIX](docs/qr-pix.png)
