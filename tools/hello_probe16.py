"""Which answer does the 16.20 client accept to its hello? Tries reply shapes one after another.

    python tools/hello_probe16.py <port>          (run through tools/run_match16.py)

The client knocks every 0.1 s with payload [u64 client nonce][u64 x][01][01][u64 protocol version][u64 t].
On 13.3 the accepted answer was [client nonce][server nonce][flag] padded to 100 bytes, after which the
client's next hello carried the server nonce as x. Each variant here is sent for 0.8 s; a variant counts
as accepted when the client's x becomes our nonce, or the client stops sending hellos / sends something else.
"""
import base64, os, socket, struct, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server"))
import lnp as L

KEY = "17BLOhi6KZsTtldTsizvHg=="
PEER, NO_EXTRA = 1, 0xFFFFFFFFFFFFFFFF
ID_LEN = 12


def build(lnp, seq, payload, peer=PEER):
    crc = L.checksum(seq, peer, NO_EXTRA, payload)
    return lnp.seal(struct.pack("<H", seq) + struct.pack(">I", crc) + b"\0" + payload)


def variants(hello, header, sn):
    """name -> datagram bytes builder input (prefix, payload)"""
    cn = hello[:8]
    nonce = struct.pack("<Q", sn)
    old = cn + nonce + hello[16:17]
    mirror = cn + nonce + hello[16:26] + hello[26:34]
    swapped = nonce + cn + hello[16:26] + hello[26:34]
    res = []
    for pname, prefix in (("no header", b""), ("4-byte header", header[8:12]), ("12-byte header", header)):
        for name, body, size in (("13.3 shape/100", old, 100), ("mirror/100", mirror, 100), ("mirror/500", mirror, 500),
                                 ("13.3 shape/500", old, 500), ("swapped/100", swapped, 100), ("swapped/500", swapped, 500)):
            res.append((f"{pname}, {name}", prefix, body.ljust(size, b"\0")))
    return res


def main():
    port = int(sys.argv[1])
    lnp = L.Lnp(base64.b64decode(KEY))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", port))
    s.settimeout(0.5)
    sn = struct.unpack("<Q", os.urandom(8))[0]
    print(f"server nonce {sn:016x}", flush=True)
    t0, plan, idx, started, last_x = time.time(), None, -1, 0.0, None
    while time.time() - t0 < 40:
        try:
            d, addr = s.recvfrom(4096)
        except socket.timeout:
            continue
        t = time.time() - t0
        m = L.parse(lnp.open(d[ID_LEN:]))
        p = m["payload"]
        if m["seq"] != 0 or len(p) != 500:
            print(f"{t:7.3f} client sent something else: {len(d)} bytes seq {m['seq']:#06x} flag {m['flag']} "
                  f"payload {len(p)} {p[:24].hex()}  (during: {plan[idx][0] if plan and idx >= 0 else '-'})", flush=True)
            continue
        x = p[8:16].hex()
        if x != last_x:
            print(f"{t:7.3f} hello x = {x}{'  == our nonce: ACCEPTED ' + plan[idx][0] if x == struct.pack('<Q', sn).hex() else ''}",
                  flush=True)
            last_x = x
        if plan is None:
            plan = variants(p, d[:ID_LEN], sn)
        if idx < 0 or t - started > 0.8:
            idx += 1
            started = t
            if idx >= len(plan):
                print(f"{t:7.3f} all {len(plan)} variants tried", flush=True)
                break
            print(f"{t:7.3f} trying: {plan[idx][0]}", flush=True)
        name, prefix, payload = plan[idx]
        s.sendto(prefix + build(lnp, 0, payload), addr)


if __name__ == "__main__":
    main()
