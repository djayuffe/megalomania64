"""Bounded decoder for the DOS resources: LE32 size, then adaptive LZHUF.

4 KiB history, maximum match 60, threshold 2; MSB-first bit stream.
The Huffman tree is maintained in frequency order and rebuilt at 32768.
No original game data is embedded in this module.
"""
import struct

N, F, THRESHOLD = 4096, 60, 2
CHARS = 256 + F - THRESHOLD
TREE = CHARS * 2 - 1
ROOT = TREE - 1


class Bits:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def get(self, count=1):
        if self.pos + count > len(self.data) * 8:
            raise ValueError('truncated LZHUF stream')
        value = 0
        for _ in range(count):
            value = (value << 1) | ((self.data[self.pos // 8] >> (7 - self.pos % 8)) & 1)
            self.pos += 1
        return value


class Huffman:
    def __init__(self):
        self.freq = [1] * CHARS + [0] * (TREE - CHARS) + [65535]
        self.child = [i + TREE for i in range(CHARS)] + [0] * (TREE - CHARS)
        self.parent = [0] * (TREE + CHARS)
        for i in range(CHARS):
            self.parent[i + TREE] = i
        for i in range(CHARS, TREE):
            pair = (i - CHARS) * 2
            self.child[i] = pair
            self.freq[i] = self.freq[pair] + self.freq[pair + 1]
            self.parent[pair] = self.parent[pair + 1] = i

    def rebuild(self):
        leaves = [((self.freq[i] + 1) // 2, self.child[i])
                  for i in range(TREE) if self.child[i] >= TREE]
        for i, (freq, child) in enumerate(leaves):
            self.freq[i], self.child[i] = freq, child
        pair = 0
        for end in range(CHARS, TREE):
            freq = self.freq[pair] + self.freq[pair + 1]
            at = end
            while at > 0 and self.freq[at - 1] > freq:
                self.freq[at], self.child[at] = self.freq[at - 1], self.child[at - 1]
                at -= 1
            self.freq[at], self.child[at] = freq, pair
            pair += 2
        for i in range(TREE):
            child = self.child[i]
            self.parent[child] = i
            if child < TREE:
                self.parent[child + 1] = i
        self.parent[ROOT] = 0

    def update(self, symbol):
        if self.freq[ROOT] == 32768:
            self.rebuild()
        node = self.parent[symbol + TREE]
        while True:
            self.freq[node] += 1
            other = node + 1
            if self.freq[node] > self.freq[other]:
                while self.freq[node] > self.freq[other + 1]:
                    other += 1
                self.freq[node], self.freq[other] = self.freq[other], self.freq[node]
                a, b = self.child[node], self.child[other]
                self.child[node], self.child[other] = b, a
                self.parent[a] = other
                if a < TREE:
                    self.parent[a + 1] = other
                self.parent[b] = node
                if b < TREE:
                    self.parent[b + 1] = node
                node = other
            node = self.parent[node]
            if node == 0:
                break

    def decode(self, bits):
        node = self.child[ROOT]
        while node < TREE:
            node = self.child[node + bits.get()]
        symbol = node - TREE
        self.update(symbol)
        return symbol


# Canonical prefix lengths for the upper six bits of the match distance.
POSITION_LENGTHS = [3] + [4] * 3 + [5] * 8 + [6] * 12 + [7] * 24 + [8] * 16


def position(bits):
    code, previous, length = 0, 0, 0
    for symbol, wanted in enumerate(POSITION_LENGTHS):
        code <<= wanted - previous
        previous = wanted
        while length < wanted:
            value = bits.get() if length == 0 else (value << 1) | bits.get()
            length += 1
        if value == code:
            return (symbol << 6) | bits.get(6)
        code += 1
    raise ValueError('invalid LZHUF position')


def decompress(data, max_output=4 * 1024 * 1024):
    if len(data) < 4:
        raise ValueError('missing LZHUF size')
    size, = struct.unpack_from('<I', data)
    if size > max_output:
        raise ValueError('LZHUF output exceeds limit')
    bits, tree = Bits(data[4:]), Huffman()
    ring = bytearray(b' ' * (N - F) + bytes(F))
    cursor, result = N - F, bytearray()
    while len(result) < size:
        symbol = tree.decode(bits)
        if symbol < 256:
            values = [symbol]
        else:
            count = symbol - 255 + THRESHOLD
            if count > size - len(result):
                raise ValueError('LZHUF match exceeds declared size')
            source = (cursor - position(bits) - 1) & (N - 1)
            values = None
        for i in range(1 if values else count):
            value = values[0] if values else ring[(source + i) & (N - 1)]
            result.append(value)
            ring[cursor] = value
            cursor = (cursor + 1) & (N - 1)
    return bytes(result)
