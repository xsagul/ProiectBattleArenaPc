"""The 16.20 game server's transport, as a reusable piece: one UDP socket, the client's handshake, acks and keepalives,
messages split / packed / fragmented, packets in and out. The game logic sits in a handler object:

    handler.on_connect(conn)
    handler.on_packet(conn, channel, packet id, net id, body, record flags)
    handler.tick(conn)                      called about every 10 ms and after every datagram

    conn.send(channel, pid, net, body)      one packet (fragmented when longer than FRAG)
    conn.send_many([(channel, pid, net, body), ...])   many packets, short ones several to a datagram

What the wire looks like is measured on 16.20 (lnp16.py's docstring; data/exe1620/match_*, the client's network.log).
"""
import base64
import os
import socket
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lnp as L          # noqa: E402
import lnp16             # noqa: E402
import netid16           # noqa: E402

FRAG = 1000              # a 10.7 KB datagram is dropped by the client: fragments of 1000 [measured]
PACK = 1000              # short packets packed into one datagram up to this size


class Conn:
    def __init__(self, server, addr):
        self.server, self.addr = server, addr
        self.connected = False
        self.seq = 0
        self.latest = None
        self.mask = 0
        self.msgnum = {}
        self.data = {}           # the handler's own state for this client

    def got(self, seq):
        if self.latest is None:
            self.latest, self.mask = seq, 0xFFFFFFFFFFFFFFFF
        elif seq > self.latest:
            self.mask = ((self.mask << (seq - self.latest)) | 1) & 0xFFFFFFFFFFFFFFFF
            self.latest = seq
        elif self.latest - seq < 64:
            self.mask |= 1 << (self.latest - seq)

    def datagram(self, payload):
        self.seq = self.seq % 0x7FFF + 1
        self.server.sock.sendto(self.server.prefix + lnp16.build(self.server.lnp, self.seq, payload), self.addr)

    def _record(self, channel, data, frag=None, number=None):
        if number is None:
            self.msgnum[channel] = self.msgnum.get(channel, 0) + 1
            number = self.msgnum[channel]
        return lnp16.message(channel, number, data, frag)

    def send(self, channel, pid, net, body):
        self.send_many([(channel, pid, net, body)])

    def send_many(self, items):
        batch = b''
        for channel, pid, net, body in items:
            data = lnp16.var_id(pid) + netid16.encode(net) + body
            if len(data) > FRAG:
                if batch:
                    self.datagram(batch)
                    batch = b''
                parts = [data[i:i + FRAG] for i in range(0, len(data), FRAG)]
                first = self.msgnum.get(channel, 0) + 1
                for i, part in enumerate(parts):            # every fragment carries the same message number [measured]
                    self.datagram(self._record(channel, part, (len(parts), i), first))
                self.msgnum[channel] = first
                continue
            rec = self._record(channel, data)
            if len(batch) + len(rec) > PACK:
                self.datagram(batch)
                batch = b''
            batch += rec
        if batch:
            self.datagram(batch)
        self.server.sent += len(items)


class Server:
    def __init__(self, port, handler, key=lnp16.KEY, log=print):
        self.port, self.handler, self.log = port, handler, log
        self.lnp = L.Lnp(base64.b64decode(key))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', port))
        self.sock.settimeout(0.005)
        self.nonce = struct.unpack('<Q', os.urandom(8))[0]
        self.conns = {}
        self.prefix = b''
        self.t0 = time.time()
        self.sent = 0
        self.last_keep = 0.0
        self.last_tick = 0.0

    def now(self):
        return time.time() - self.t0

    def run(self, seconds=None):
        self.log(f'listening on udp {self.port}')
        while seconds is None or self.now() < seconds:
            try:
                d, addr = self.sock.recvfrom(65536)
            except socket.timeout:
                self.idle()
                continue
            except ConnectionResetError:
                continue
            self.datagram(d, addr)
            self.idle()

    def idle(self):
        t = self.now()
        if t - self.last_tick >= 0.010:
            self.last_tick = t
            for c in list(self.conns.values()):
                if c.connected:
                    self.handler.tick(c)
        if t - self.last_keep > 0.25:
            self.last_keep = t
            for c in self.conns.values():
                if c.connected:
                    c.datagram(b'')

    def datagram(self, d, addr):
        self.prefix = d[8:12]
        m = L.parse(self.lnp.open(d[12:]))
        p, seq = m['payload'], m['seq']
        c = self.conns.get(addr)
        if c is None:
            c = self.conns[addr] = Conn(self, addr)
        if seq & 0x8000:
            return
        if seq == 0 and len(p) == 500:
            cn, guess = struct.unpack_from('<QQ', p)
            if guess == self.nonce and not c.connected:
                c.connected = True
                self.log(f'{self.now():8.3f} client connected')
                self.handler.on_connect(c)
            self.sock.sendto(self.prefix + lnp16.build(self.lnp, 0, struct.pack('<QQB', cn, self.nonce, p[16]).ljust(100, b'\0')), addr)
            return
        if seq == 0:
            return
        c.got(seq)
        self.sock.sendto(self.prefix + lnp16.build(self.lnp, (-c.latest) & 0xFFFF, b'', extra=c.mask), addr)
        if m['flag']:
            import zstandard
            p = zstandard.ZstdDecompressor().decompress(p, max_output_size=0x10000)
        for ch, num, frag, flags, data in lnp16.split_messages(p):
            if not data:
                continue
            pid, used = lnp16.read_id(data)
            net, k = netid16.decode(data[used:])
            self.handler.on_packet(c, ch, pid, net, data[used + k:], flags)
