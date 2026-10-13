"""scratch: everything the real 16.20 stream says about one unit, in order (the 13.3 x_minion_life idea).
   x_life.py <net id hex | first-minion> [seconds, default 25]"""
import struct, sys, types
sys.modules['decoded'] = types.ModuleType('decoded')
import packet_emu16 as P, rofl2, replication, waypoints

def main():
    r = rofl2.Rofl2(P.ROFL)
    who = sys.argv[1]
    span = float(sys.argv[2]) if len(sys.argv) > 2 else 25
    t = P.table(); emu = P.Emu()
    net = None if who == 'first-minion' else int(who, 16)
    t0 = None
    for e, (tm, ch, pid, obj, body) in rofl2.stream(r, (1,)):
        if t0 is not None and tm > t0 + span:
            break
        if net is None and pid != 439:
            continue
        tr = {}
        ok, left, o = emu.deserialize(t[pid], pid, obj, body, tr)
        emu.heap = P.HEAP + 0x1000
        if ok != 1:
            continue
        blocks = P.decoded_blocks(emu, tr)
        flds = [(off, raw) for off, raw, hid, w in P.meaningful(blocks[0][1]) if off >= 0x10]
        if net is None:
            net = next(struct.unpack('<I', raw)[0] for off, raw in flds if off == 0x1c)
            print(f'first lane minion: {net:#x}')
        nb = struct.pack('<I', net)
        inside = any(raw == nb for off, raw in flds)
        extra = ''
        if pid in (61, 287):
            # buffers: look for the unit inside
            ptr_off = 0x18 if pid == 61 else 0x20
            buf = b''.join(f[1] for f in blocks[1][1]) if len(blocks) > 1 else b''
            try:
                if pid == 61:
                    ents = [x for x in waypoints.parse(buf) if x['net'] == net]
                    if not ents: continue
                    extra = f"move: speed {ents[0]['speed']:.0f} points {[tuple(round(c) for c in waypoints.to_world(p)) for p in ents[0]['points']]}"
                else:
                    us = [g for n, g in replication.parse(buf) if n == net]
                    if not us: continue
                    import repl16
                    extra = 'replication: ' + str({k: (round(v, 1) if isinstance(v, float) else hex(v)) for k, v in repl16.read_unit(us[0], 'lane_minion').items()})
            except Exception as x:
                extra = f'(buffer not read: {x})'
            inside = True
        if obj != net and not inside:
            continue
        if t0 is None: t0 = tm
        desc = extra or ' '.join(f'+{off:#x}={raw.hex() if len(raw) <= 12 else raw[:6].hex() + ".."}' for off, raw in flds)
        texts = [bytes(b''.join(f[1] for f in bl[1])).rstrip(b'\0') for bl in blocks[1:]]
        texts = [x.decode() for x in texts if x and all(32 <= c < 127 for c in x)]
        print(f'{tm:8.3f} id {pid:5} about {obj:08x} ch {ch} {len(body):3} B  {desc[:230]} {texts if texts and not extra else ""}')

main()
