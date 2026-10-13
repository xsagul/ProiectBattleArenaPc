"""scratch: the byte buffer of a packet (object field {pointer, count}) in clear, for the first n packets of an id"""
import os, struct, sys
os.environ['BA_PATCH'] = '1620'
import packet_emu16 as P


def buffers(pid, ptr_off, n, kinds=((2,), (1,))):
    t = P.table(); emu = P.Emu(); out = []
    for P.KINDS in kinds:
        for tm, ch, p, obj, body in P.packets(P.ROFL, pid):
            tr = {}
            ok, left, o = emu.deserialize(t[pid], pid, obj, body, tr)
            if ok != 1 or left:
                continue
            blocks = tr['blocks']; objp = blocks[0][0]
            state = {}
            def plain(p0, size):
                st = bytearray(emu.u.mem_read(p0, size))
                for off, raw, hid, w in P.plain_fields([(w, a - p0, s, v) for w, a, s, v in tr['writes'] if p0 <= a < p0 + size], size):
                    st[off:off + len(raw)] = raw
                return bytes(st)
            head = plain(objp, t[pid]['size'])
            ptr, cnt = struct.unpack_from('<QI', head, ptr_off)
            out.append((tm, head, plain(ptr, cnt) if cnt else b''))
            emu.heap = P.HEAP + 0x1000
            if len(out) >= n:
                P.KINDS = (1,)
                return out
    P.KINDS = (1,)
    return out


if __name__ == '__main__':
    import waypoints
    pid, off, n = int(sys.argv[1]), int(sys.argv[2], 16), int(sys.argv[3])
    good = bad = 0
    for tm, head, buf in buffers(pid, off, n):
        try:
            ents = waypoints.parse(buf)
            good += 1
            if good <= 3:
                print(f't {tm:.2f} head {head[0x10:0x30].hex()} entries {len(ents)}:', [(hex(e["net"]), round(e["speed"], 1), e["points"][:3]) if isinstance(e, dict) else e for e in ents][:3])
        except Exception as x:
            bad += 1
            if bad <= 3:
                print(f't {tm:.2f} does not parse ({type(x).__name__} {x}): {buf[:40].hex()}')
    print(good, 'parse as 13.3 waypoint entries,', bad, 'do not')
