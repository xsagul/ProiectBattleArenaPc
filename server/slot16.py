"""Packet 618 (game info), the receiving client's player slot: the handler (rva 0x688230) takes object byte +0x4c,
decodes it (rva 0x6884ce..0x6884fe, table rva 0x1a74cb0) and stores the slot at session +0x41b; the client only
declares the connection established for a slot 1..56 that exists (rva 0x6871c0).

  slot16.py find <file.rofl>     which body byte the reader puts at +0x4c, and what slot the replay's value means
"""
import os, sys
import emu16

T2_RVA = 0x1a74cb0


def slot_of(e, b):
    t = e.img[T2_RVA:T2_RVA + 256]
    rot3 = lambda x: ((x << 3) | (x >> 5)) & 255
    return t[rot3(t[rot3((((~b & 255) + 0x35) & 255) ^ 0xf)])]


def main():
    import rofl2
    from rofl_packets import blocks
    e = emu16.Emu()
    r = rofl2.Rofl2(sys.argv[2])
    body = next(blocks(r.payload(r.records[0])))[4]

    def read(b):
        obj, used, ans = e.read_packet(618, b'\xa6' + bytes(b))
        return bytes(e.mu.mem_read(obj, 552)), used, ans

    base, used, ans = read(body)
    print(f'replay 618: consumed {used} of {len(body) + 1}, answer {ans}, {e.notes[:1]}')
    print(f'object +0x4c = {base[0x4c]:#04x} -> slot {slot_of(e, base[0x4c])}')
    for k in range(0, 64):
        b = bytearray(body); b[k] ^= 0x01
        o, u, a = read(b)
        b[k] ^= 0x41
        o2, u2, a2 = read(b)
        if o[0x4c] != base[0x4c] or o2[0x4c] != base[0x4c]:
            print(f'body byte {k} ({body[k]:#04x}) changes +0x4c: ^1 -> {o[0x4c]:#04x} (answer {a}), ^0x40 -> {o2[0x4c]:#04x} (answer {a2})')
    table = {slot_of(e, v): v for v in range(256)}
    print('object value for slot 1..10:', [hex(table[s]) for s in range(1, 11)])


if __name__ == '__main__':
    main()
