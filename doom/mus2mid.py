"""
DOOM generic portado de Harbour para Python com pygame.

Por Wagner Nunes da Silva

vagucs@bol.com.br
vagucs@vagucs.com.br
vagucs@gmail.com

www.vagucs.com.br

MUS lump → Standard MIDI File (Chocolate Doom mus2mid.c).
"""

from __future__ import annotations

import struct

NUM_CHANNELS = 16
MIDI_PERCUSSION_CHAN = 9
MUS_PERCUSSION_CHAN = 15

MUS_RELEASEKEY = 0x00
MUS_PRESSKEY = 0x10
MUS_PITCHWHEEL = 0x20
MUS_SYSTEMEVENT = 0x30
MUS_CHANGECONTROLLER = 0x40
MUS_SCOREEND = 0x60

MIDI_HEADER = bytes(
    [
        0x4D,
        0x54,
        0x68,
        0x64,
        0x00,
        0x00,
        0x00,
        0x06,
        0x00,
        0x00,
        0x00,
        0x01,
        0x00,
        0x46,
        0x4D,
        0x54,
        0x72,
        0x6B,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
)

CONTROLLER_MAP = [
    0x00,
    0x20,
    0x01,
    0x07,
    0x0A,
    0x0B,
    0x5B,
    0x5D,
    0x40,
    0x43,
    0x78,
    0x7B,
    0x7E,
    0x7F,
    0x79,
]


class _Midi:
    def __init__(self) -> None:
        self.body = bytearray()
        self.queued = 0
        self.tracksize = 0
        self.velocities = [127] * NUM_CHANNELS
        self.channel_map = [-1] * NUM_CHANNELS

    def write_time(self, time: int) -> None:
        buffer = time & 0x7F
        t = time
        while (t := t >> 7) != 0:
            buffer <<= 8
            buffer |= (t & 0x7F) | 0x80
        while True:
            self.body.append(buffer & 0xFF)
            self.tracksize += 1
            if buffer & 0x80:
                buffer >>= 8
            else:
                self.queued = 0
                return

    def write(self, data: bytes) -> None:
        self.write_time(self.queued)
        self.body.extend(data)
        self.tracksize += len(data)

    def allocate_channel(self) -> int:
        result = max(self.channel_map) + 1
        if result == MIDI_PERCUSSION_CHAN:
            result += 1
        return result

    def midi_channel(self, mus_channel: int) -> int:
        if mus_channel == MUS_PERCUSSION_CHAN:
            return MIDI_PERCUSSION_CHAN
        if self.channel_map[mus_channel] == -1:
            self.channel_map[mus_channel] = self.allocate_channel()
            self.write(bytes([0xB0 | self.channel_map[mus_channel], 0x7B, 0]))
        return self.channel_map[mus_channel]


def mus2mid(mus: bytes) -> bytes | None:
    if len(mus) >= 4 and mus[:4] == b"MThd":
        return mus
    if len(mus) < 16 or mus[:4] != b"MUS\x1a":
        return None
    scorestart = struct.unpack_from("<H", mus, 6)[0]
    pos = scorestart
    out = _Midi()
    hitscoreend = False

    def read_u8() -> int | None:
        nonlocal pos
        if pos >= len(mus):
            return None
        b = mus[pos]
        pos += 1
        return b

    while not hitscoreend:
        while not hitscoreend:
            descriptor = read_u8()
            if descriptor is None:
                return None
            channel = out.midi_channel(descriptor & 0x0F)
            event = descriptor & 0x70
            if event == MUS_RELEASEKEY:
                key = read_u8()
                if key is None:
                    return None
                out.write(bytes([0x80 | channel, key & 0x7F, 0]))
            elif event == MUS_PRESSKEY:
                key = read_u8()
                if key is None:
                    return None
                if key & 0x80:
                    vel = read_u8()
                    if vel is None:
                        return None
                    out.velocities[channel] = vel & 0x7F
                out.write(bytes([0x90 | channel, key & 0x7F, out.velocities[channel]]))
            elif event == MUS_PITCHWHEEL:
                key = read_u8()
                if key is None:
                    break
                wheel = key * 64
                out.write(bytes([0xE0 | channel, wheel & 0x7F, (wheel >> 7) & 0x7F]))
            elif event == MUS_SYSTEMEVENT:
                ctrl = read_u8()
                if ctrl is None or ctrl < 10 or ctrl > 14:
                    return None
                out.write(bytes([0xB0 | channel, CONTROLLER_MAP[ctrl], 0]))
            elif event == MUS_CHANGECONTROLLER:
                ctrl = read_u8()
                val = read_u8()
                if ctrl is None or val is None:
                    return None
                if ctrl == 0:
                    out.write(bytes([0xC0 | channel, val & 0x7F]))
                else:
                    if ctrl < 1 or ctrl > 9:
                        return None
                    working = 0x7F if val & 0x80 else val
                    out.write(bytes([0xB0 | channel, CONTROLLER_MAP[ctrl], working]))
            elif event == MUS_SCOREEND:
                hitscoreend = True
            else:
                return None
            if descriptor & 0x80:
                break
        if not hitscoreend:
            timedelay = 0
            while True:
                working = read_u8()
                if working is None:
                    return None
                timedelay = timedelay * 128 + (working & 0x7F)
                if (working & 0x80) == 0:
                    break
            out.queued += timedelay

    out.write_time(out.queued)
    out.body.extend(b"\xff\x2f\x00")
    out.tracksize += 3
    header = bytearray(MIDI_HEADER)
    header[18] = (out.tracksize >> 24) & 0xFF
    header[19] = (out.tracksize >> 16) & 0xFF
    header[20] = (out.tracksize >> 8) & 0xFF
    header[21] = out.tracksize & 0xFF
    return bytes(header) + bytes(out.body)
