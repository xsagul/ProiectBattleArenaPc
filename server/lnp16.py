"""A first server for the 16.20 client: 13.3's transport (lnp.py) with the 16.20 differences, and the
replay's own packets sent to the client.

  lnp16.py [--replay <file.rofl>] [--netid none|a6|u32] [--frag N] [--stream] <port>

Measured on 16.20 (data/exe1620/match_*; the client's own network.log is the judge):
  client datagram  = 12-byte header (8 zero bytes + 4 bytes) + sealed body; ours = those 4 bytes + sealed body
  hello / accept   = as on 13.3 (client nonce, server nonce, flag; padded to 100)
  message record   = u16 w: length = w >> 6; 0x04 fragment (assumed, as 13.3's bit 0), 0x08 number = previous + 1,
                     0x10 same channel as previous, 0x20 set on every client message but its very first
                     then [u8 channel] [u16 number] [u8 fragment count, u8 fragment index]   (client log: "fragment=(1/12)")
  packet id        = one byte below 251, else two: id = (b0 - 251) * 256 + b1 + 251   (reader rva 0x11c4ae0,
                     251 = 256 - (1401 - 2) // 255, 1401 read at rva 0x1e5947c)
"""
import base64, os, socket, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import json
import lnp as L
import netid16

KEY = '17BLOhi6KZsTtldTsizvHg=='
PEER, NO_EXTRA = 1, 0xFFFFFFFFFFFFFFFF
ID_SPLIT = 251
GAME_INFO = 618


def build(lnp, seq, payload, flag=0, extra=None):
    crc = L.checksum(seq, PEER, NO_EXTRA if extra is None else extra, payload)
    body = struct.pack('<H', seq) + struct.pack('>I', crc) + bytes([flag])
    if extra is not None:
        body += struct.pack('<Q', extra)
    return lnp.seal(body + payload)


def var_id(pid):
    if pid < ID_SPLIT:
        return bytes([pid])
    hi, lo = divmod(pid - ID_SPLIT, 256)
    return bytes([ID_SPLIT + hi, lo])


def read_id(data):
    """(packet id, bytes used)"""
    if data[0] < ID_SPLIT:
        return data[0], 1
    return (data[0] - ID_SPLIT) * 256 + data[1] + ID_SPLIT, 2


def message(channel, number, data, frag=None):
    w = (len(data) << 6) | 0x20 | (0x04 if frag else 0)
    out = struct.pack('<HBH', w, channel, number & 0xFFFF)
    if frag:
        out += struct.pack('<BB', *frag)
    return out + data


def split_messages(p):
    out, at, prev_ch, prev_num = [], 0, 0, 0
    while at + 2 <= len(p):
        w = struct.unpack_from('<H', p, at)[0]; at += 2
        ch = prev_ch
        if not w & 0x10:
            ch = p[at]; at += 1
            prev_num = 0
        num = prev_num + 1
        if not w & 0x08:
            num = struct.unpack_from('<H', p, at)[0]; at += 2
        frag = None
        if w & 0x04:
            frag = struct.unpack_from('<BB', p, at); at += 2
        n = w >> 6
        out.append((ch, num, frag, w & 0x3f, p[at:at + n])); at += n
        prev_ch, prev_num = ch, num
    return out


class Peer:
    def __init__(self):
        self.connected = False
        self.seq = 0
        self.latest = None
        self.mask = 0
        self.msgnum = {}
        self.sent_info = False
        self.count64 = 0             # client packets with id 64 seen (one at connect, one when loading is done)
        self.stream = None           # iterator over the replay's chunk blocks, once the start state is out
        self.pending = None          # next block of the stream
        self.part = None             # --capture: which part of the recorded match is going out (live16.Capture)
        self.t_start = None          # our clock at replay time 0
        self.t_game = None           # our clock when the start state went out (game time 0 of a match of ours)

    def got(self, seq):
        if self.latest is None:
            self.latest, self.mask = seq, 0xFFFFFFFFFFFFFFFF
        elif seq > self.latest:
            self.mask = ((self.mask << (seq - self.latest)) | 1) & 0xFFFFFFFFFFFFFFFF
            self.latest = seq
        elif self.latest - seq < 64:
            self.mask |= 1 << (self.latest - seq)


def main():
    args = sys.argv[1:]
    port = int(args[-1])
    opt = lambda name, default=None: args[args.index(name) + 1] if name in args else default
    frag_size = int(opt('--frag', 1000))
    # --slot N: the receiving client's player slot inside the replay's game info (slot16.py; the replay's own is 22)
    slot = int(opt('--slot', 0))
    frag_num = opt('--frag-num', 'same')
    # --own-hero <net id, hex>: that champion is moved by us (hero16.py): its orders are read, our movement packets
    # answer; use with --start and without --stream (the replay's packets about it would fight ours)
    # --world: our own minion waves (world16.py) from the moment the start state is out; no --stream with it
    world = None
    if '--world' in args:
        import world16
        world = world16.World16()
        print(f'own world: {len(world.barracks)} barracks, formats {sorted(world.sc)}', flush=True)
    hero_at = []
    if '--hero-at' in args:
        when, where = opt('--hero-at').split(':')
        hero_at = [float(when), tuple(float(c) for c in where.split(','))]
    hero = None
    if '--own-hero' in args:
        import hero16
        hero = hero16.Hero(int(opt('--own-hero'), 16))
        print(f'own hero {hero.net:#x} starts at ({hero.a[0]:.0f}, {hero.a[1]:.0f})', flush=True)
    replay = None
    if '--replay' in args:
        import rofl2
        replay = rofl2.Rofl2(opt('--replay'))
        print(f'replay {replay.version}, {len(replay.records)} records', flush=True)
    # --capture <data/live/gameId>: a recorded live match (tools/live_decode.py), the real server's own packets to
    # a player, sent in the three parts the real server sent them [measured on custom match 4013831789]: after the
    # client's packet 1 (clock, game info), after its second 64 (the start state), after its third 64 (the match)
    capture = None
    if '--capture' in args:
        import live16
        capture = live16.Capture(opt('--capture'))
        print(f'capture {capture.name}: parts begin at {["%.3f" % g for g in capture.gates]} s of the recording', flush=True)
    lnp = L.Lnp(base64.b64decode(KEY))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', port))
    s.settimeout(0.01)
    nonce = struct.unpack('<Q', os.urandom(8))[0]
    peers, prefix, t0, last_keep = {}, b'', time.time(), 0.0
    now = lambda: time.time() - t0

    def send_data(addr, st, payload, what, quiet=False):
        st.seq = st.seq % 0x7FFF + 1
        s.sendto(prefix + build(lnp, st.seq, payload), addr)
        if not quiet:
            print(f'{now():8.3f} snd data seq {st.seq} len {len(payload)} {what}', flush=True)

    def send_message(addr, st, channel, data, what, quiet=False):
        if len(data) <= frag_size:
            st.msgnum[channel] = st.msgnum.get(channel, 0) + 1
            return send_data(addr, st, message(channel, st.msgnum[channel], data), what, quiet)
        parts = [data[i:i + frag_size] for i in range(0, len(data), frag_size)]
        first = st.msgnum.get(channel, 0) + 1
        for i, part in enumerate(parts):
            # --frag-num seq: every fragment its own message number (13.3's way); same: all carry one number
            num = first + i if frag_num == 'seq' else first
            send_data(addr, st, message(channel, num, part, (len(parts), i)), f'{what} fragment {i + 1}/{len(parts)}', quiet)
        st.msgnum[channel] = first + len(parts) - 1 if frag_num == 'seq' else first

    def packet(pid, netid, body):
        return var_id(pid) + netid16.encode(netid) + body

    def blocks_of(kind_filter):
        from rofl2 import blocks
        for e in replay.records:
            if kind_filter(e):
                for b in blocks(replay.payload(e)):
                    yield b

    def send_blocks(addr, st, items, what):
        """Many replay blocks: short ones packed several to a datagram, long ones as fragments."""
        batch, n = b'', 0
        for t, ch, pid, obj, body in items:
            data = packet(pid, obj, body)
            n += 1
            if len(data) > frag_size:
                if batch:
                    send_data(addr, st, batch, what, quiet=True)
                    batch = b''
                send_message(addr, st, ch, data, f'{what}: packet {pid}', quiet=True)
                continue
            st.msgnum[ch] = st.msgnum.get(ch, 0) + 1
            rec = message(ch, st.msgnum[ch], data)
            if len(batch) + len(rec) > 1000:
                send_data(addr, st, batch, what, quiet=True)
                batch = b''
            batch += rec
        if batch:
            send_data(addr, st, batch, what, quiet=True)
        return n

    def start_part(addr, st, k):
        """--capture: part k of the recorded match starts now; what is left of the part before goes out at once."""
        if st.stream is not None:
            rest = ([st.pending] if st.pending is not None else []) + list(st.stream)
            if rest:
                send_blocks(addr, st, rest, 'capture')
                print(f'{now():8.3f} capture: {len(rest)} packets left of part {st.part} sent at once', flush=True)
        st.part, st.pending = k, None
        st.stream, st.t_start = capture.part(k), now()
        print(f'{now():8.3f} capture: part {k} begins', flush=True)

    def pump(addr, st):
        """The replay's chunk blocks whose time has come (--stream); our own world's packets (--world)."""
        if capture and st.stream is None and st.part == 1 and now() - st.t_start > 2.0:
            start_part(addr, st, 2)          # the client's third 64 did not come: the match goes on as recorded
        if world is not None and st.t_game is not None:
            t = now() - st.t_game
            out = world.tick(t)
            if hero is not None and hero_at and t >= hero_at[0]:
                # test aid (--hero-at "<game second>:<x>,<z>"): the champion is put there at once (a one-point move)
                hero.a = hero.b = hero_at[1]
                hero.t0 = t
                out.append(hero.move_packet(t, [hero_at[1]]))
                print(f'{now():8.3f} hero put at {hero_at[1]}', flush=True)
                hero_at.clear()
            if hero is not None:
                out = out + hero.tick(t, world) + hero.take_events(t, world)
            if out:
                send_blocks(addr, st, [(t, ch, pid, net, body) for ch, pid, net, body in out], 'world')
        if st.stream is None:
            return
        due, limit = [], now() - st.t_start
        while True:
            if st.pending is None:
                st.pending = next(st.stream, None)
                if st.pending is None:
                    st.stream = None
                    print(f'{now():8.3f} stream finished', flush=True)
                    break
            if st.pending[0] > limit or len(due) >= 400:
                break
            due.append(st.pending)
            st.pending = None
        if due:
            send_blocks(addr, st, due, 'stream')

    print(f'listening on udp {port}', flush=True)
    while True:
        try:
            d, addr = s.recvfrom(4096)
        except socket.timeout:
            for a, st in peers.items():
                pump(a, st)
            if now() - last_keep > 0.25:
                last_keep = now()
                for a, st in peers.items():
                    if st.connected:
                        send_data(a, st, b'', 'keepalive', quiet=True)
            continue
        except ConnectionResetError:
            continue
        prefix = d[8:12]
        m = L.parse(lnp.open(d[12:]))
        p, seq = m['payload'], m['seq']
        st = peers.setdefault(addr, Peer())
        if seq & 0x8000:
            continue
        if seq == 0 and len(p) == 500:
            cn, guess = struct.unpack_from('<QQ', p)
            if guess == nonce and not st.connected:
                st.connected = True
                print(f'{now():8.3f} client connected', flush=True)
            s.sendto(prefix + build(lnp, 0, struct.pack('<QQB', cn, nonce, p[16]).ljust(100, b'\0')), addr)
            continue
        if seq == 0:
            print(f'{now():8.3f} control len {len(p)}: {p[:24].hex()}', flush=True)
            continue
        st.got(seq)
        s.sendto(prefix + build(lnp, (-st.latest) & 0xFFFF, b'', extra=st.mask), addr)
        pump(addr, st)
        if m['flag']:
            import zstandard
            p = zstandard.ZstdDecompressor().decompress(p, max_output_size=0x10000)
        for ch, num, frag, flags, data in split_messages(p):
            pid, used = read_id(data) if data else (None, 0)
            print(f'{now():8.3f} rcv ch {ch} num {num} flags {flags:#04x} id {pid} len {len(data)}: {data[used:used + 40].hex()}',
                  flush=True)
            if pid == 1 and capture and not st.sent_info:
                st.sent_info = True
                start_part(addr, st, 0)
            if pid == 64:
                st.count64 += 1
                if capture and st.count64 in (2, 3):
                    start_part(addr, st, st.count64 - 1)
                if st.count64 == 2 and replay and '--start' in args:
                    # the start state = the first keyframe (on 13.3 it held StartSpawn and Game Start)
                    n = send_blocks(addr, st, blocks_of(lambda e: e['type'] == 2 and e['id'] == 1), 'start state')
                    print(f'{now():8.3f} snd start state: {n} packets of keyframe 1', flush=True)
                    st.t_game = now()
                    if hero is not None:
                        for c, opid, onet, obody in hero.start(0.0):
                            send_message(addr, st, c, packet(opid, onet, obody), f'our packet {opid} (state of the champion)')
                    if '--stream' in args:
                        st.stream, st.t_start = blocks_of(lambda e: e['type'] == 1), now()
                    elif '--pass-kinds' in args:
                        # control experiment: after the start state only the replay's packets of these ids
                        kinds = {int(x) for x in opt('--pass-kinds').split(',')}
                        st.stream, st.t_start = (b for b in blocks_of(lambda e: e['type'] == 1) if b[2] in kinds), now()
            if pid == 544 and hero is not None and st.t_game is not None:
                out, slot = hero.on_skill_up(data[used:], now() - st.t_game)
                print(f'{now():8.3f} skill-up request: slot {slot} -> {len(out)} packet(s) of ours (levels {hero.levels})', flush=True)
                for c, opid, onet, obody in out:
                    send_message(addr, st, c, packet(opid, onet, obody), f'our packet {opid}')
            if pid == 1032 and hero is not None and st.t_game is not None:
                t = now() - st.t_game
                out, o = hero.on_order(data[used:], t, world)
                if o:
                    print(f'{now():8.3f} order: place ({o["place"][0]:.0f}, {o["place"][1]:.0f}) target {o["target"]:#x} kind {o["kind"]:#04x}'
                          f' -> {len(out)} packet(s) of ours', flush=True)
                for c, opid, onet, obody in out:
                    send_message(addr, st, c, packet(opid, onet, obody), f'our packet {opid}')
            if pid == 1 and replay and not st.sent_info:
                st.sent_info = True
                if '--small-first' in args:     # a short packet from the start state, to test delivery without fragments
                    t, c, bid, obj, body = next(blocks_of(lambda e: e['type'] == 2))
                    send_message(addr, st, 1, packet(bid, obj, body), f'packet {bid} netid {obj:#x} ({len(body)} B)')
                t, c, bid, obj, body = next(blocks_of(lambda e: e['type'] == 3))
                assert bid == GAME_INFO, bid
                if slot:
                    info = json.load(open(os.path.join(HERE, '..', 'data', 'exe1620', 'slot618.json')))
                    body = bytearray(body)
                    body[info['body_index']] = info['wire_byte_for_slot'][str(slot)]
                    body = bytes(body)
                send_message(addr, st, 1, packet(GAME_INFO, obj, body), f'packet {GAME_INFO} netid {obj:#x} ({len(body)} B)')


if __name__ == '__main__':
    main()
