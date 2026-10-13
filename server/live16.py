"""A recorded live match as a packet source for our server (lnp16.py --capture <data/live/gameId>).

The match is what tools/live_capture.ps1 + tools/live_decode.py wrote: packets.tsv, every packet the real
server sent to the player and every packet the player's client sent, in time order.

The real server sends in three parts, each one the answer to something the client says
[measured on custom match 4013831789; the tutorial 4013821998 has the same order]:
    part 0  right after the client's packet 1:   213, clock 804 + 371 (twice), game info 618
    part 1  right after the client's second 64:  the start state, 4784 packets in one burst
    part 2  right after the client's third 64:   the match itself, to the game end
Left out: 1007 (the answer to the client's ping 841, it repeats 8 bytes of that very ping, so a recorded one
is stale) and 1095 (the echo of the client's own loading progress 197).

  live16.py selftest <data/live/gameId> [seconds]
      starts lnp16.py --capture, plays a minimal client against it (hello, 1, 64, 64, 64) and checks that
      what arrives is the recording's packets, same order, same bytes
"""
import os, socket, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DROP = (1007, 1095)


def rows(path):
    """(time, 'S2C' | 'C2S', channel, packet id, net id, body) of a packets.tsv"""
    for line in open(path, encoding='utf-8'):
        t, way, ch, flags, extra, pid, net, n, body = line.rstrip('\n').split('\t')
        yield float(t), way, int(ch), int(pid), int(net, 16), bytes.fromhex(body)


class Capture:
    def __init__(self, game, drop=DROP):
        self.path = os.path.join(game, 'packets.tsv')
        self.name = os.path.basename(os.path.normpath(game))
        self.drop = set(drop)
        first, ready = None, []
        for t, way, ch, pid, net, body in rows(self.path):
            if way == 'C2S' and pid == 1 and first is None:
                first = t
            if way == 'C2S' and pid == 64:
                ready.append(t)
                if len(ready) == 3:
                    break
        assert first is not None and len(ready) == 3, 'the recording does not hold the client packets 1, 64, 64, 64'
        self.gates = [first, ready[1], ready[2]]

    def part(self, k):
        """(seconds since the part began, channel, packet id, net id, body) of part k"""
        a = self.gates[k]
        b = self.gates[k + 1] if k + 1 < len(self.gates) else float('inf')
        for t, way, ch, pid, net, body in rows(self.path):
            if t >= b:
                break
            if way == 'S2C' and t >= a and pid not in self.drop:
                yield t - a, ch, pid, net, body


def selftest(game, seconds):
    import base64
    import lnp as L
    import lnp16
    import netid16
    cap = Capture(game)
    c2s = {}
    for t, way, ch, pid, net, body in rows(cap.path):       # the real client's own first packets, as recorded
        if way == 'C2S' and pid in (1, 64):
            c2s.setdefault(pid, []).append(body)
        if t > cap.gates[2] + 1:
            break
    port = 5127
    srv = subprocess.Popen([sys.executable, '-W', 'ignore', os.path.join(HERE, 'lnp16.py'), '--capture', game, str(port)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lnp = L.Lnp(base64.b64decode(lnp16.KEY))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    s.settimeout(0.02)
    to = ('127.0.0.1', port)
    head = bytes(8) + b'\x11\x22\x33\x44'
    got, seq, num = [], 0, 0

    def send(payload, number=None):
        nonlocal seq
        if number is None:
            seq += 1
            number = seq
        s.sendto(head + lnp16.build(lnp, number, payload), to)

    def say(pid, body):
        nonlocal num
        num += 1
        send(lnp16.message(1, num, lnp16.var_id(pid) + netid16.encode(0) + body))

    def listen(until):
        while time.time() < until:
            try:
                d, _ = s.recvfrom(65536)
            except socket.timeout:
                continue
            except ConnectionResetError:
                continue
            got.append((time.time() - t0, d))

    try:
        time.sleep(1.5)
        t0 = time.time()
        send(struct.pack('<QQB', 7, 0, 1).ljust(500, b'\0'), 0)
        listen(time.time() + 0.3)
        nonce = None
        for _, d in got:
            m = L.parse(lnp.open(d[4:]))
            if m['seq'] == 0 and len(m['payload']) == 100:
                nonce = struct.unpack_from('<Q', m['payload'], 8)[0]
        assert nonce is not None, 'no answer to the hello'
        send(struct.pack('<QQB', 7, nonce, 1).ljust(500, b'\0'), 0)
        listen(time.time() + 0.2)
        marks = {}
        say(1, c2s[1][0]); say(64, c2s[64][0]); marks[0] = time.time() - t0
        listen(time.time() + 1.0)
        say(64, c2s[64][1]); marks[1] = time.time() - t0
        listen(time.time() + cap.gates[2] - cap.gates[1])
        say(64, c2s[64][2]); marks[2] = time.time() - t0
        listen(time.time() + seconds)
    finally:
        srv.kill()
    log = srv.stdout.read()

    # what arrived, as packets
    parts, mine = {}, []
    for t, d in got:
        m = L.parse(lnp.open(d[4:]))
        if m['seq'] & 0x8000 or m['seq'] == 0 or not m['payload']:
            continue
        for ch, n, frag, flags, data in lnp16.split_messages(m['payload']):
            if frag:
                g = parts.setdefault((ch, n), {})
                g[frag[1]] = data
                if len(g) < frag[0]:
                    continue
                data = b''.join(g[i] for i in range(frag[0]))
                del parts[ch, n]
            pid, used = lnp16.read_id(data)
            net, k = netid16.decode(data[used:])
            mine.append((t, ch, pid, net, data[used + k:]))
    # what the recording says should have arrived by now
    want = []
    for k in (0, 1, 2):
        for t, ch, pid, net, body in cap.part(k):
            if k == 2 and t > seconds - 1.0:
                break
            want.append((ch, pid, net, body))
    have = [(ch, pid, net, body) for _, ch, pid, net, body in mine]
    same = 0
    while same < min(len(want), len(have)) and want[same] == have[same]:
        same += 1
    print(f'recording {cap.name}: parts begin at {["%.3f" % g for g in cap.gates]}; test client said 1 + 64 at {marks[0]:.2f} s, '
          f'64 at {marks[1]:.2f} s, 64 at {marks[2]:.2f} s')
    print(f'datagrams received {len(got)}, packets {len(have)}, fragment sets left open {len(parts)}')
    print(f'expected at least {len(want)} packets (parts 0 and 1 whole, part 2 up to {seconds - 1.0:.1f} s): '
          f'the first {same} are identical and in order' + ('' if same >= len(want) else
          f'; first difference at {same}: want {want[same][:3] if same < len(want) else None}, got {have[same][:3] if same < len(have) else None}'))
    late = [t for t, *_ in mine[len(want) - 1:len(want)]]
    for line in log.splitlines():
        if 'capture' in line or 'Traceback' in line or 'Error' in line:
            print('   server:', line)
    return same >= len(want)


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    if sys.argv[1] == 'selftest':
        ok = selftest(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 12.0)
        sys.exit(0 if ok else 1)
