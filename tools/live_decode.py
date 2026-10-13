"""Decode a live capture (tools/live_capture.ps1 + tools/live_session.py) into game packets.

    python tools/live_decode.py <capture.pcapng> [data/live/<gameId> ...] [--raw N]

Without game folders: every folder beside the capture that has session.json + cmdline.txt.
Takes the datagrams between this machine and the match's server (session.json), opens them with the
match's key (cmdline.txt) through the 16.20 transport we already measured on our own server
(server/lnp.py, server/lnp16.py), and writes into the game folder:
    wire.tsv      every datagram, opened:  time  dir  number (hex)  packed flag  ack mask (hex) | -  payload hex
    packets.tsv   every game packet:       time  dir(S2C|C2S)  channel  record flags  extra byte  packet id  net id
                                           body length  body hex
--raw N prints the first N datagrams of each direction undecoded (header check).

IMPORTANT: only a STOPPED capture is whole. pktmon keeps one 16 MB buffer per CPU and writes a buffer to the
file when it fills or at stop, so a copy of a running capture holds the frames of some CPUs only [measured:
a third of the datagrams, all from CPUs 4 and 5]. The transport numbers every datagram, so the script
reports how much of the match is there.
"""
import base64, collections, json, os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
import lnp as L            # noqa: E402
import lnp16               # noqa: E402
import netid16             # noqa: E402
import zstandard           # noqa: E402

SEQ_WRAP = 0x7FFF          # datagram numbers run 1..0x7FFF, then start at 1 again


def datagrams(path):
    """(time s, src ip, src port, dst ip, dst port, udp payload) for every IPv4 UDP packet of a pcapng."""
    d = open(path, "rb").read()
    at, res = 0, {}
    while at + 12 <= len(d):
        typ, n = struct.unpack_from("<II", d, at)
        body = d[at + 8:at + n - 4]
        if typ == 1:                                    # interface description
            unit, o = 1e-6, 8
            while o + 4 <= len(body):
                code, ln = struct.unpack_from("<HH", body, o)
                if code == 9 and ln == 1:               # if_tsresol
                    v = body[o + 4]
                    unit = 2.0 ** -(v & 0x7f) if v & 0x80 else 10.0 ** -v
                if code == 0:
                    break
                o += 4 + (ln + 3 & ~3)
            res[len(res)] = (struct.unpack_from("<H", body)[0], unit)
        elif typ == 6:                                  # enhanced packet
            iface, hi, lo, cap = struct.unpack_from("<IIII", body)
            link, unit = res.get(iface, (1, 1e-6))
            p = body[20:20 + cap]
            o = 0
            if link == 1:
                et = struct.unpack_from(">H", p, 12)[0] if len(p) >= 14 else 0
                o = 14
                if et == 0x8100:
                    et = struct.unpack_from(">H", p, 16)[0]
                    o = 18
                if et not in (0x0800, 0x86DD, 0x0806) and len(p) > 40 and p[0] & 0x0C == 0x08:
                    # pktmon on a Wi-Fi adapter hands over native 802.11 data frames (already decrypted)
                    # under the Ethernet link type: frame header, then LLC/SNAP with the ethertype
                    o = 24 + (6 if p[1] & 3 == 3 else 0) + (2 if p[0] & 0x80 else 0)
                    if p[0] & 0x80 and p[1] & 0x80:
                        o += 4
                    et = struct.unpack_from(">H", p, o + 6)[0] if p[o:o + 6] == b"\xaa\xaa\x03\0\0\0" else 0
                    o += 8
                if et != 0x0800:
                    at += n
                    continue
            elif link != 101:                           # 101 = raw IP
                at += n
                continue
            if len(p) < o + 28 or p[o] >> 4 != 4 or p[o + 9] != 17:
                at += n
                continue
            ihl = (p[o] & 15) * 4
            sp, dp, ulen = struct.unpack_from(">HHH", p, o + ihl)
            ip = lambda b: ".".join(map(str, b))
            yield ((hi << 32 | lo) * unit, ip(p[o + 12:o + 16]), sp, ip(p[o + 16:o + 20]), dp,
                   p[o + ihl + 8:o + ihl + ulen])
        at += n


def split_messages(p):
    """lnp16.split_messages plus what only the live server sends [measured on tutorial 4013821998: every data
    datagram of the sample ends exactly]: the two low bits of the record word are set on channel 1 messages,
    and when both are set one more byte sits before the data (even values 0..0x34 seen; meaning not known yet)."""
    out, at, prev_ch, prev_num = [], 0, 0, 0
    while at + 2 <= len(p):
        w = struct.unpack_from("<H", p, at)[0]; at += 2
        ch = prev_ch
        if not w & 0x10:
            ch = p[at]; at += 1
            prev_num = 0
        num = prev_num + 1
        if not w & 0x08:
            num = struct.unpack_from("<H", p, at)[0]; at += 2
        frag = None
        if w & 0x04:
            frag = struct.unpack_from("<BB", p, at); at += 2
        extra = None
        if w & 3 == 3:
            extra = p[at]; at += 1
        n = w >> 6
        out.append((ch, num, frag, w & 0x3f, extra, p[at:at + n])); at += n
        prev_ch, prev_num = ch, num
    assert at == len(p), "records do not end with the datagram"
    return out


def join_messages(recs):
    """The inverse of split_messages: the same records in the short form the live server uses (channel left
    out when it repeats, number left out when it is the previous one + 1)."""
    out, prev_ch, prev_num, first = bytearray(), 0, 0, True
    for ch, num, frag, flags, extra, data in recs:
        w = (len(data) << 6) | (flags & 0x23) | (0x04 if frag else 0)
        same = not first and ch == prev_ch
        if not same:
            prev_num = 0
        nxt = num == prev_num + 1
        out += struct.pack("<H", w | (0x10 if same else 0) | (0x08 if nxt else 0))
        if not same:
            out.append(ch)
        if not nxt:
            out += struct.pack("<H", num)
        if frag:
            out += bytes(frag)
        if flags & 3 == 3:
            out.append(extra)
        out += data
        prev_ch, prev_num, first = ch, num, False
    return bytes(out)


def replay_ids():
    """Packet ids of the 16.20 replay we already read (spectator stream), or None when it is not there."""
    try:
        os.environ.setdefault("BA_PATCH", "1620")
        import packet_emu16, rofl2
        r = rofl2.Rofl2(packet_emu16.ROFL)
        return collections.Counter(b[2] for _, b in rofl2.stream(r, (1, 2, 3)))
    except Exception as e:
        print("replay not read:", e)
        return None


def match_info(game):
    """(server ip, server port, key bytes, player id) of a recorded match."""
    s = json.load(open(os.path.join(game, "session.json")))
    first = re.match(r'"([^"]*)"', open(os.path.join(game, "cmdline.txt")).read()).group(1).split()
    return s["gameClient"]["serverIp"], s["gameClient"]["serverPort"], base64.b64decode(first[2]), int(first[3])


def numbering(seqs):
    """(present, expected) from the datagram numbers in time order."""
    if not seqs:
        return 0, 0
    at, have = seqs[0], {seqs[0]}
    prev = seqs[0]
    for q in seqs[1:]:
        step = (q - prev) % SEQ_WRAP
        if step > SEQ_WRAP // 2:
            step -= SEQ_WRAP                            # a datagram that came late
        at += step
        have.add(at)
        prev = q
    return len(have), max(have) - min(have) + 1


def decode_game(udp, game, raw=0, rep=None):
    ip, port, key, player = match_info(game)
    lnp = L.Lnp(key)
    seen, grams = set(), []
    for t, sip, sp, dip, dp, data in udp:
        if (sip, sp) == (ip, port):
            way = "S2C"
        elif (dip, dp) == (ip, port):
            way = "C2S"
        else:
            continue
        if (way, data) in seen:                         # the same frame seen on a second capture point
            continue
        seen.add((way, data))
        grams.append((t, way, data))
    print(f"=== {os.path.basename(os.path.normpath(game))}: server {ip}:{port}")
    if not grams:
        print("   no datagrams with this server in the capture")
        return
    grams.sort(key=lambda g: g[0])                      # buffers of different CPUs are not in time order
    t0 = grams[0][0]
    n_way = collections.Counter(w for _, w, _ in grams)
    print(f"datagrams {dict(n_way)}  span {grams[-1][0] - t0:.1f} s  bytes "
          f"{ {w: sum(len(d) for _, x, d in grams if x == w) for w in n_way} }")
    if raw:
        for way in ("C2S", "S2C"):
            for t, w, d in [g for g in grams if g[1] == way][:raw]:
                print(f"  {t - t0:8.3f} {w} {len(d):4}  {d[:16].hex()} ...")

    head = {"C2S": 12, "S2C": 4}
    peers = (player, 1, 0)
    crc_ok, crc_bad, peer_used = collections.Counter(), collections.Counter(), collections.Counter()
    kinds = collections.Counter()
    ids = {"S2C": collections.Counter(), "C2S": collections.Counter()}
    size = {"S2C": collections.Counter(), "C2S": collections.Counter()}
    seqs = {"S2C": [], "C2S": []}
    parts = {}
    rec_flags = collections.Counter()
    dec = zstandard.ZstdDecompressor()
    wire = open(os.path.join(game, "wire.tsv"), "w", encoding="utf-8")
    out = open(os.path.join(game, "packets.tsv"), "w", encoding="utf-8")
    unread = same_bytes = other_bytes = same_id = other_id = 0
    for t, way, d in grams:
        m = L.parse(lnp.open(d[head[way]:]))
        extra = lnp16.NO_EXTRA if m["extra"] is None else m["extra"]
        good = [p for p in peers if L.checksum(m["seq"], p, extra, m["payload"]) == m["crc"]]
        if not good:
            crc_bad[way] += 1
            continue
        crc_ok[way] += 1
        peer_used[good[0]] += 1
        p = m["payload"]
        wire.write(f"{t - t0:.6f}\t{way}\t{m['seq']:04x}\t{m['flag']}\t"
                   f"{'-' if m['extra'] is None else '%016x' % m['extra']}\t{p.hex()}\n")
        if m["seq"] & 0x8000:
            kinds[way, "ack"] += 1
            continue
        if m["seq"] == 0:
            kinds[way, f"control {len(p)} B"] += 1
            continue
        seqs[way].append(m["seq"])
        if not p:
            kinds[way, "keepalive"] += 1
            continue
        kinds[way, "data"] += 1
        if m["flag"]:
            p = dec.decompress(p, max_output_size=0x100000)
            kinds[way, "data, packed"] += 1
        try:
            msgs = split_messages(p)
        except Exception:
            unread += 1
            continue
        if join_messages(msgs) == p:
            same_bytes += 1
        else:
            other_bytes += 1
        for ch, num, frag, flags, extra, data in msgs:
            rec_flags[way, flags & 0x23, ch] += 1
            if frag:
                got = parts.setdefault((way, ch, num), {})
                got[frag[1]] = data
                if len(got) < frag[0]:
                    continue
                data = b"".join(got[i] for i in range(frag[0]))
                del parts[way, ch, num]
                kinds[way, "message from fragments"] += 1
            if not data:
                continue
            try:
                pid, used = lnp16.read_id(data)
                net, k = netid16.decode(data[used:])
            except Exception:
                unread += 1
                continue
            body = data[used + k:]
            if lnp16.var_id(pid) + netid16.encode(net) == data[:used + k]:
                same_id += 1
            else:
                other_id += 1
            ids[way][pid] += 1
            size[way][pid] += len(body)
            out.write(f"{t - t0:.3f}\t{way}\t{ch}\t{flags & 0x23:02x}\t{'' if extra is None else extra}\t{pid}\t{net:08x}"
                      f"\t{len(body)}\t{body.hex()}\n")
    out.close()
    wire.close()
    whole = True
    for way in ("S2C", "C2S"):
        have, expect = numbering(seqs[way])
        share = 100.0 * have / expect if expect else 0.0
        whole = whole and share > 99.5
        print(f"{way} numbered datagrams: {have} of {expect} ({share:.1f} %)")
    if not whole:
        print("   PARTIAL CAPTURE: stop pktmon (Enter in its window) and convert again before trusting anything below")
    print(f"checksum ok {dict(crc_ok)}  bad {dict(crc_bad)}  peer id that fits {dict(peer_used)}")
    print("datagram kinds:", ", ".join(f"{w} {k}: {v}" for (w, k), v in sorted(kinds.items())))
    print(f"messages not read {unread}, fragment sets left open {len(parts)}; written back byte for byte: "
          f"datagrams {same_bytes} of {same_bytes + other_bytes}, packet id + net id {same_id} of {same_id + other_id}")
    for way in ("S2C", "C2S"):
        c = ids[way]
        print(f"{way}: {sum(c.values())} packets, {len(c)} distinct ids, {sum(size[way].values())} body bytes")
        print("   " + "  ".join(f"{pid}x{n}" for pid, n in c.most_common(40)))
        print("   per channel (record flags & 0x23): " + ", ".join(
            f"ch {ch} flags {f:#04x}: {n}" for (w, f, ch), n in sorted(rec_flags.items()) if w == way))
    if rep:
        live = ids["S2C"]
        only_live = sorted(set(live) - set(rep))
        print(f"against the replay (spectator stream, {len(rep)} ids): {len(set(live) & set(rep))} ids in both, "
              f"{len(only_live)} only in the live match:")
        print("   " + "  ".join(f"{pid}x{live[pid]}" for pid in only_live))


def main():
    args = sys.argv[1:]
    raw = 0
    if "--raw" in args:
        i = args.index("--raw")
        raw = int(args[i + 1])
        del args[i:i + 2]
    cap, games = args[0], args[1:]
    if not games:
        root = os.path.dirname(os.path.abspath(cap))
        games = [os.path.join(root, n) for n in sorted(os.listdir(root))
                 if os.path.exists(os.path.join(root, n, "session.json")) and os.path.exists(os.path.join(root, n, "cmdline.txt"))]
    udp = list(datagrams(cap))
    print(f"capture: {len(udp)} UDP datagrams (IPv4)")
    rep = replay_ids()
    for game in games:
        decode_game(udp, game, raw, rep)


if __name__ == "__main__":
    main()
