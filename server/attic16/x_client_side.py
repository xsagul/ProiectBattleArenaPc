"""scratch: play the CLIENT's side of our world's movement packets (as x_sim_jumps did on 13.3): every unit walks the
last path it was given at its speed. Measured: how far a new path's first point is from where the client has the
unit (a visible jump), how long a unit stands at the end of its points while the server still moves it (a stall),
and how many pairs of standing units overlap."""
import math, statistics, struct, sys
import world16, waypoints, lol_packets
import pkt_schema as PS

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 120
W = world16.World16()
sc61, sc684 = PS.Schema.load(61), PS.Schema.load(684)
# decode our own packets without the emulator: keep what we encode
client = {}      # net -> dict(points, speed, t0)
jumps, stalls, stall_time = [], 0, {}
orig_move = W.move
def cpos(c, t):
    pts = c['pts']; d = (t - c['t0']) * c['speed']
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if d <= L: return (a[0] + (b[0]-a[0]) * d / L, a[1] + (b[1]-a[1]) * d / L) if L else b
        d -= L
    return pts[-1]
def at_end(c, t):
    return (t - c['t0']) * c['speed'] >= sum(math.dist(a, b) for a, b in zip(c['pts'], c['pts'][1:])) - 1e-6
now = [0.0]
def move(m, points):
    pts = [waypoints.to_world(world16.to_cell(p)) for p in points]
    c = client.get(m.net)
    if c is not None:
        jumps.append((math.dist(cpos(c, now[0]), pts[0]), now[0], m.net))
    client[m.net] = {'pts': pts, 'speed': m.speed, 't0': now[0]}
    orig_move(m, points)
W.move = move
orig_spawn = W.spawn
def spawn(t, b, kind, wave):
    orig_spawn(t, b, kind, wave)
    m = W.units[W.next_net]
    en = W.data['enter'][f'{b:x}']
    client[m.net] = {'pts': [tuple(q) for q in en['path']], 'speed': m.speed, 't0': t + 0.033}
W.spawn = spawn
t = 0.0; overlaps = checks = 0
while t < secs:
    now[0] = t
    W.tick(t)
    for m in W.units.values():
        c = client.get(m.net)
        if c and m.alive and m.moving and at_end(c, t):
            stall_time[m.net] = stall_time.get(m.net, 0) + 1 / 30
    if int(t * 30) % 30 == 0:
        st = [m for m in W.units.values() if m.alive and not m.moving and m.started]
        for i, a in enumerate(st):
            for b in st[i + 1:]:
                checks += 1
                overlaps += math.dist(a.xy, b.xy) < world16.BODY * 0.8
    t += 1 / 30
# server vs client place at the end
gap = [math.dist(cpos(client[m.net], t), m.xy) for m in W.units.values() if m.alive and m.net in client]
js = [j[0] for j in jumps]
print(f'{secs:.0f} s, {len(client)} units, {len(js)} moves sent')
print(f'jump at a new path: median {statistics.median(js):.1f}, 95% {sorted(js)[int(len(js) * .95)]:.1f}, max {max(js):.1f} units; over 60: {sum(1 for j in js if j > 60)}')
bad = sorted(stall_time.items(), key=lambda kv: -kv[1])[:5]
print(f'units that stood at the end of their points while the server moved them: {sum(1 for v in stall_time.values() if v > 0.3)} (longest {[(hex(n), round(v, 2)) for n, v in bad]})')
print(f'server vs client place now: median {statistics.median(gap):.1f}, max {max(gap):.1f}')
print(f'standing units closer than 0.8 body: {overlaps} of {checks} pairs checked')
big = sorted(jumps, reverse=True)[:4]
print('largest jumps (units, time, net):', [(round(a), round(b, 1), hex(c)) for a, b, c in big])
