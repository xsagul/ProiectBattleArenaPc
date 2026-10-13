"""What our own 16.20 world takes from the 16.20 replay (measured, not invented): -> data/exe1620/world16.json

  barracks   net id -> team (by where its minions start), lane (by where they go), the walk of its first minion as a
             polyline of world points from its first move to where it first stands still
  waves      first spawn time, time between waves, time between two minions of a wave, kinds per wave number
  spawn      per kind (4 melee, 5 caster, 6 cannon): the spawn packet's fields, the delay to the first move, the move
             speed, the two replication blocks the real server sends for a new minion (values by name, repl16.py) and
             their delays
  attack     per kind: the fields of a minion's attack packet (390) and the damage packets (150) that follow

    python tools/world_data16.py
"""
import collections, json, os, statistics, struct, sys, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["BA_PATCH"] = "1620"
sys.modules["decoded"] = types.ModuleType("decoded")
import packet_emu16 as P      # noqa: E402
import pkt_schema as PS       # noqa: E402
import pkt_tree as PT         # noqa: E402
import replication            # noqa: E402
import repl16                 # noqa: E402
import rofl2                  # noqa: E402
import waypoints              # noqa: E402
import roles16 as R           # noqa: E402

UNTIL = 200.0                 # seconds of the replay read (six waves)


class Dec:
    """decode packets of one id through the client's reader and the learnt format"""
    def __init__(self, pid):
        self.pid, self.sc, self.T = pid, PS.Schema.load(pid), PT.Tree(pid)

    def __call__(self, obj, body):
        return PS.decode(self.T, self.sc, P.wire(self.pid, obj, body))


def main():
    r = rofl2.Rofl2(P.ROFL)
    dec = {pid: Dec(pid) for pid in (R.MINION_SPAWN, R.MOVE, R.REPLICATION)}
    spawns, moves, repl = {}, collections.defaultdict(list), collections.defaultdict(list)
    for e, (t, ch, pid, obj, body) in rofl2.stream(r, (1,)):
        if t > UNTIL:
            break
        if pid == R.MINION_SPAWN:
            v = dec[pid](obj, body)
            net = struct.unpack("<I", bytes.fromhex(v["+0x1c"]))[0]
            spawns[net] = {"t": t, "barracks": struct.unpack("<I", bytes.fromhex(v["+0x14"]))[0], "kind": int(v["+0x18"], 16),
                           "wave": int.from_bytes(bytes.fromhex(v["+0x20"]), "little"), "fields": v}
        elif pid == R.MOVE:
            v = dec[pid](obj, body)
            for ent in waypoints.parse(bytes.fromhex(v["+0x18"]["text"])):
                if ent["net"] in spawns:
                    moves[ent["net"]].append((t, ent["speed"], [waypoints.to_world(p) for p in ent["points"]]))
        elif pid == R.REPLICATION:
            v = dec[pid](obj, body)
            for net, groups in replication.parse(bytes.fromhex(v["+0x20"]["text"])):
                if net in spawns and len(repl[net]) < 2:
                    repl[net].append((t, repl16.read_unit(groups, "lane_minion")))
    # barracks: team, lane and the walk of the first minion of the first wave
    barracks = {}
    for net, s in sorted(spawns.items(), key=lambda kv: kv[1]["t"]):
        b = s["barracks"]
        if b in barracks or s["wave"] != 1 or not moves[net]:
            continue
        walk = []
        for t, speed, pts in moves[net]:
            if len(pts) < 2:
                break
            if not walk:
                walk.append(pts[0])
            walk += pts[1:]
        start, end = walk[0], walk[-1]
        team = "order" if start[0] + start[1] < 14800 else "chaos"
        dx, dz = abs(end[0] - start[0]), abs(end[1] - start[1])
        lane = "mid" if min(dx, dz) > 0.6 * max(dx, dz) else ("bot" if (dx > dz) == (team == "order") else "top")
        barracks[b] = {"team": team, "lane": lane, "walk": [[round(x, 1), round(z, 1)] for x, z in walk],
                       "first_move_delay": round(moves[net][0][0] - s["t"], 3)}
    # the whole lane for each barracks: its own walk, then the other team's walk of the same lane backwards
    for b, d in barracks.items():
        other = next(o for ob, o in barracks.items() if o["lane"] == d["lane"] and o["team"] != d["team"])
        d["lane_path"] = d["walk"] + other["walk"][::-1][1:]
    times = sorted({round(s["t"], 3) for s in spawns.values() if s["barracks"] == next(iter(barracks))})
    wave_start = collections.OrderedDict()
    for s in sorted(spawns.values(), key=lambda s: s["t"]):
        if s["barracks"] == next(iter(barracks)):
            wave_start.setdefault(s["wave"], []).append((s["t"], s["kind"]))
    starts = [v[0][0] for v in wave_start.values()]
    gaps = [b - a for v in wave_start.values() for (a, _), (b, _) in zip(v, v[1:])]
    waves = {"first": round(starts[0], 3), "period": round(statistics.median(b - a for a, b in zip(starts, starts[1:])), 3),
             "between_minions": round(statistics.median(gaps), 4),
             "kinds": {str(w): [k for t, k in v] for w, v in wave_start.items() if len(v) >= 6}}
    spawn = {}
    for kind in (4, 5, 6):
        nets = [n for n, s in spawns.items() if s["kind"] == kind and len(repl[n]) == 2 and moves[n]]
        if not nets:
            continue
        n = nets[0]
        s = spawns[n]
        spawn[str(kind)] = {"fields": s["fields"], "speed": moves[n][0][1],
                            "blocks": [{"delay": round(t - s["t"], 3), "values": v} for t, v in repl[n]],
                            "max_hp_by_wave": {str(spawns[m]["wave"]): repl[m][0][1].get("mMaxHP") for m in nets
                                               if spawns[m]["barracks"] == s["barracks"]}}
    out = {"barracks": {f"{b:x}": d for b, d in barracks.items()}, "waves": waves, "spawn": spawn}
    json.dump(out, open(os.path.join(ROOT, "data", "exe1620", "world16.json"), "w"), indent=1)
    for b, d in barracks.items():
        print(f"barracks {b:x}: {d['team']:5} {d['lane']:3} walk {len(d['walk'])} points {d['walk'][0]} -> {d['walk'][-1]}, "
              f"lane {len(d['lane_path'])} points, first move after {d['first_move_delay']} s")
    print("waves:", {k: v for k, v in waves.items() if k != "kinds"}, "kinds", waves["kinds"])
    for k, s in spawn.items():
        b1, b2 = s["blocks"]
        print(f"kind {k}: speed {s['speed']}, block 1 after {b1['delay']} s ({len(b1['values'])} values: mHP {b1['values'].get('mHP')}, "
              f"ActionState {b1['values'].get('ActionState'):#x}), block 2 after {b2['delay']} s ({len(b2['values'])} values: damage "
              f"{b2['values'].get('mBaseAttackDamage')}, range {b2['values'].get('mAttackRange')}, speed {b2['values'].get('mMoveSpeed')})")


if __name__ == "__main__":
    main()
