"""UDP interceptor between the original 4.20 client and the local LeagueSandbox server: forwards every datagram both
ways unchanged and records it (time, direction, bytes), so what Riot's client sends and receives can be decoded later
with tools/lol420_decode.py.

    python tools/lol420_proxy.py [--listen 5119] [--server 5129] [--out research/lol420_capture/<time>.bin]

Record format: per datagram  f64 seconds since start, u8 direction (0 client->server, 1 server->client), u16 length,
bytes. The client is started as usual (it connects to 127.0.0.1:5119); the server runs on --server's port.
"""
import argparse
import os
import select
import socket
import struct
import time

ap = argparse.ArgumentParser()
ap.add_argument('--listen', type=int, default=5119)
ap.add_argument('--server', type=int, default=5129)
ap.add_argument('--out', default=None)
a = ap.parse_args()

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = a.out or os.path.join(root, 'research', 'lol420_capture', time.strftime('%Y%m%d_%H%M%S') + '.bin')
os.makedirs(os.path.dirname(out), exist_ok=True)

front = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
front.bind(('127.0.0.1', a.listen))
back = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
back.bind(('127.0.0.1', 0))
server = ('127.0.0.1', a.server)
client = None
t0 = time.perf_counter()
counts = [0, 0]
print(f'interceptor: client -> 127.0.0.1:{a.listen} -> server 127.0.0.1:{a.server}; recording to {out}', flush=True)
with open(out, 'wb') as f:
    last_report = time.perf_counter()
    while True:
        ready, _, _ = select.select([front, back], [], [], 1.0)
        for s in ready:
            try:
                data, addr = s.recvfrom(65536)
            except ConnectionResetError:
                continue  # Windows reports an earlier send to a closed port this way (client or server gone)
            t = time.perf_counter() - t0
            if s is front:
                client = addr
                back.sendto(data, server)
                d = 0
            else:
                if client is None:
                    continue
                front.sendto(data, client)
                d = 1
            counts[d] += 1
            f.write(struct.pack('<dBH', t, d, len(data)) + data)
        if time.perf_counter() - last_report > 5:
            f.flush()
            last_report = time.perf_counter()
            print(f'  {counts[0]} client->server, {counts[1]} server->client', flush=True)
