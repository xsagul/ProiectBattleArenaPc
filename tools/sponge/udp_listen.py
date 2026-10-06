"""The other side of the sponge: what the 13.3 client itself sends when told to join a game server.

  udp_listen.py <port> <seconds> <out.txt>     listens on UDP (and TCP) <port> of every local address, logs each
                                               datagram / connection with its time, sender and bytes; answers nothing
"""
import select, socket, sys, time
port, secs, out = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); u.bind(('0.0.0.0', port))
t = socket.socket(socket.AF_INET, socket.SOCK_STREAM); t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); t.bind(('0.0.0.0', port)); t.listen(4)
t0 = time.time(); conns = []
with open(out, 'w') as f:
    f.write(f'listening on udp+tcp {port}\n'); f.flush()
    while time.time() - t0 < secs:
        r, _, _ = select.select([u, t] + conns, [], [], 0.5)
        for s in r:
            if s is u:
                data, addr = u.recvfrom(65536)
                f.write(f'{time.time() - t0:8.3f} udp from {addr[0]}:{addr[1]} {len(data)} bytes {data.hex()}\n')
            elif s is t:
                c, addr = t.accept(); conns.append(c)
                f.write(f'{time.time() - t0:8.3f} tcp connection from {addr[0]}:{addr[1]}\n')
            else:
                data = s.recv(65536)
                if not data: conns.remove(s); f.write(f'{time.time() - t0:8.3f} tcp closed\n')
                else: f.write(f'{time.time() - t0:8.3f} tcp {len(data)} bytes {data.hex()}\n')
            f.flush()
