"""What our own 16.20 world takes from a LIVE recording (the real server's packets to a player, measured, not
invented): -> data/live/<gameId>/world16.json, the same keys as the replay-built data/exe1620/world16.json
(tools/world_data16.py) so world16.py reads either.

  barracks   net id -> team, lane, the walk of its first minion, delay to the first move
  waves      first spawn time (game time), time between waves, between two minions, kinds per wave
  spawn      per kind: the 439 fields (it travels inside the 239 container), move speed, the replication blocks
             with their delays (live: three, at +0, +0.1, +0.2 s)
  enter      per barracks: 684's prefix / mark / path / flags and per kind the health triple
  templates  first values of the fight packets (390 938 515 150 1112 1090 818 447 906 972 294 743 118)
  inner      which packets travel together with a 439 inside one 239

Game time = recording time - the client's third 64 (the start of part 2).

    python tools/live_world16.py data/live/<gameId> [until game second, default 400]
"""
import collections, json, os, statistics, struct, sys, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["BA_PATCH"] = "1620"
sys.modules.setdefault("decoded", types.ModuleType("decoded"))
import forms16                # noqa: E402
import live16                 # noqa: E402
import pkt_schema as PS       # noqa: E402
import replication            # noqa: E402
import repl16                 # noqa: E402
import waypoints              # noqa: E402

SPAWN, ENTER_DATA, REPL, MOVE, UNIT_294 = 439, 684, 287, 61, 294
TEMPLATES = (390, 938, 515, 150, 1112, 1090, 818, 447, 906, 972, 294, 743, 118)

_sc = {}


def parse(pid, body):
    if pid not in _sc:
        try:
            _sc[pid] = PS.Schema.load(pid)
        except FileNotFoundError:
            _sc[pid] = None
    sc = _sc[pid]
    if sc is None:
        return None
    try:
        return PS.parse(sc, body)
    except Exception:
        return None


def u32(h):
    return struct.unpack("<I", bytes.fromhex(h))[0]


def main():
    game = sys.argv[1]
    until = float(sys.argv[2]) if len(sys.argv) > 2 else 400.0
    cap = live16.Capture(game)
    g0 = cap.gates[2]
    spawns, enter, moves, repl, first294 = {}, {}, collections.defaultdict(list), collections.defaultdict(list), {}
    templates, inner_kinds = {}, collections.Counter()
    for t, way, ch, pid, net, body in live16.rows(cap.path):
        if way != "S2C" or t < g0:
            continue
        gt = t - g0
        if gt > until:
            break
        if pid == forms16.CONTAINER:
            v = parse(pid, body)
            if v is None:
                continue
            items = forms16.unpack(v)
            if any(p == SPAWN for p, n, b in items):
                inner_kinds[" ".join(str(p) for p, n, b in items)] += 1
            for p, n, b in items:
                if p == SPAWN:
                    s = parse(p, b)
                    if s is None:
                        continue
                    m = u32(s["+0x1c"])
                    spawns.setdefault(m, {"t": gt, "barracks": u32(s["+0x14"]), "kind": int(s["+0x18"], 16),
                                          "wave": int.from_bytes(bytes.fromhex(s["+0x20"]), "little"), "fields": s, "outer": net})
        elif pid == ENTER_DATA and net in spawns and net not in enter:
            v = parse(pid, body)
            if v is not None:
                enter[net] = (gt, v)
        elif pid == REPL:
            v = parse(pid, body)
            if v is None:
                continue
            for n, groups in replication.parse(bytes.fromhex(v["+0x20"]["text"])):
                if n in spawns and len(repl[n]) < 3:
                    repl[n].append((gt, repl16.read_unit(groups, "lane_minion")))
        elif pid == MOVE:
            v = parse(pid, body)
            if v is None:
                continue
            for ent in waypoints.parse(bytes.fromhex(v["+0x18"]["text"])):
                if ent["net"] in spawns:
                    moves[ent["net"]].append((gt, ent["speed"], [waypoints.to_world(p) for p in ent["points"]]))
        elif pid == UNIT_294 and net in spawns and spawns[net]["kind"] not in first294:
            first294[spawns[net]["kind"]] = (round(gt - spawns[net]["t"], 3), body.hex(), parse(pid, body))
        if pid in TEMPLATES and pid not in templates:
            v = parse(pid, body)
            templates[pid] = v if v is not None else {"raw": body.hex()}
    # barracks: team, lane and the walk of the first minion of the first wave seen from it
    barracks = {}
    for net, s in sorted(spawns.items(), key=lambda kv: kv[1]["t"]):
        b = s["barracks"]
        if b in barracks or not moves[net]:
            continue
        walk = []
        for t, speed, pts in moves[net]:
            if len(pts) < 2:
                break
            if not walk:
                walk.append(pts[0])
            walk += pts[1:]
        if len(walk) < 2:
            continue
        start, end = walk[0], walk[-1]
        team = "order" if start[0] + start[1] < 14800 else "chaos"
        dx, dz = abs(end[0] - start[0]), abs(end[1] - start[1])
        lane = "mid" if min(dx, dz) > 0.6 * max(dx, dz) else ("bot" if (dx > dz) == (team == "order") else "top")
        barracks[b] = {"team": team, "lane": lane, "walk": [[round(x, 1), round(z, 1)] for x, z in walk],
                       "first_move_delay": round(moves[net][0][0] - s["t"], 3), "wave_seen": s["wave"]}
    for b, d in barracks.items():
        other = next((o for ob, o in barracks.items() if o["lane"] == d["lane"] and o["team"] != d["team"]), None)
        d["lane_path"] = d["walk"] + (other["walk"][::-1][1:] if other else [])
    ref = next(iter(barracks)) if barracks else None
    wave_start = collections.OrderedDict()
    for s in sorted(spawns.values(), key=lambda s: s["t"]):
        if s["barracks"] == ref:
            wave_start.setdefault(s["wave"], []).append((s["t"], s["kind"]))
    starts = [v[0][0] for v in wave_start.values()]
    gaps = [b - a for v in wave_start.values() for (a, _), (b, _) in zip(v, v[1:])]
    waves = {"first": round(starts[0], 3), "period": round(statistics.median(b - a for a, b in zip(starts, starts[1:])), 3),
             "between_minions": round(statistics.median(gaps), 4),
             "kinds": {str(w): [k for t, k in v] for w, v in wave_start.items() if len(v) >= 6}}
    spawn = {}
    for kind in (4, 5, 6):
        nets = [n for n, s in spawns.items() if s["kind"] == kind and len(repl[n]) >= 2 and moves[n]]
        if not nets:
            continue
        n = nets[0]
        s = spawns[n]
        spawn[str(kind)] = {"fields": s["fields"], "speed": moves[n][0][1],
                            "blocks": [{"delay": round(t - s["t"], 3), "values": v} for t, v in repl[n]],
                            "max_hp_by_wave": {str(spawns[m]["wave"]): repl[m][0][1].get("mMaxHP") for m in nets
                                               if spawns[m]["barracks"] == s["barracks"]},
                            "unit_294": first294.get(kind)}
    ent = {}
    for net, (t, v) in enter.items():
        s = spawns[net]
        b = s["barracks"]
        blob = bytes.fromhex(v["+0x20"]["text"])
        prefix, mark, counter = blob[:26], blob[26], struct.unpack_from("<I", blob, 27)[0]
        e = waypoints.parse(blob[31:])[0]
        d = ent.setdefault(f"{b:x}", {"prefix": prefix.hex(), "mark": mark, "kinds": {},
                                      "path": [list(waypoints.to_world(p)) for p in e["points"]], "flags": e.get("flags", 0)})
        d["kinds"].setdefault(str(s["kind"]), {"health": v["+0x10"]["text"], "speed": e["speed"], "delay": round(t - s["t"], 3)})
    out = {"source": cap.name, "barracks": {f"{b:x}": d for b, d in barracks.items()}, "waves": waves, "spawn": spawn,
           "enter": ent, "templates": {str(k): v for k, v in templates.items()},
           "inner": dict(inner_kinds.most_common(10)), "spawns_seen": len(spawns)}
    path = os.path.join(game, "world16.json")
    json.dump(out, open(path, "w"), indent=1)
    print(f"{len(spawns)} minion spawns seen until game second {until:.0f}; containers holding a spawn: {dict(inner_kinds.most_common(5))}")
    for b, d in barracks.items():
        print(f"barracks {b:x}: {d['team']:5} {d['lane']:3} (wave {d['wave_seen']}) walk {len(d['walk'])} points {d['walk'][0]} -> "
              f"{d['walk'][-1]}, first move after {d['first_move_delay']} s")
    print("waves:", {k: v for k, v in waves.items() if k != "kinds"}, "kinds", dict(list(waves["kinds"].items())[:4]))
    for k, s in spawn.items():
        print(f"kind {k}: speed {s['speed']}, blocks " + ", ".join(f"+{b['delay']} s ({len(b['values'])} values)" for b in s["blocks"]) +
              f"; 294 {s['unit_294'][:2] if s['unit_294'] else None}")
    print("templates:", {k: ("raw" if "raw" in v else "values") for k, v in out["templates"].items()})
    print("->", path)


if __name__ == "__main__":
    main()
