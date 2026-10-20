"""C64 disk scene wire format and bounded packet RLE (no game assets)."""
import struct

MAGIC = b'MLI1'
SEGMENTS = (8000, 1000, 1000)


def pack(data):
    data = bytes(data)
    out, at = bytearray(), 0
    while at < len(data):
        run = 1
        while at + run < len(data) and data[at + run] == data[at] and run < 130:
            run += 1
        if run >= 3:
            out.extend((128 + run - 3, data[at])); at += run
        else:
            start = at
            at += run
            while at < len(data) and at - start < 128:
                if data[at:at + 3] == bytes([data[at]]) * 3:
                    break
                at += 1
            out.append(at - start - 1); out.extend(data[start:at])
    return bytes(out)


def unpack(data, size, at=0):
    out = bytearray()
    while len(out) < size:
        if at >= len(data):
            raise ValueError('truncated RLE control')
        ctrl = data[at]; at += 1
        count = ctrl - 125 if ctrl & 128 else ctrl + 1
        if count > size - len(out):
            raise ValueError('RLE packet exceeds segment')
        needed = 1 if ctrl & 128 else count
        if at + needed > len(data):
            raise ValueError('truncated RLE payload')
        out.extend(bytes([data[at]]) * count if ctrl & 128 else data[at:at + count])
        at += needed
    return bytes(out), at


def encode(bitmap, screen, color, multicolor=False, background=0, frames=180):
    if tuple(map(len, (bitmap, screen, color))) != SEGMENTS:
        raise ValueError('scene segment size')
    if not 0 <= background < 16 or not 1 <= frames <= 65535:
        raise ValueError('scene header range')
    return MAGIC + struct.pack('<BBH', bool(multicolor), background, frames) + b''.join(
        pack(segment) for segment in (bitmap, screen, color))


def decode(data):
    if len(data) < 8 or data[:4] != MAGIC:
        raise ValueError('invalid scene magic')
    mode, bg, frames = struct.unpack_from('<BBH', data, 4)
    if mode > 1 or bg > 15 or frames == 0:
        raise ValueError('invalid scene header')
    at, segments = 8, []
    for size in SEGMENTS:
        segment, at = unpack(data, size, at)
        segments.append(segment)
    if at != len(data):
        raise ValueError('trailing scene data')
    return mode, bg, frames, segments
