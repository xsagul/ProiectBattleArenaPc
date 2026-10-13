"""The nine champions nobody plays (the recording's bots: their champion, place and team come from the start state),
moved and fought by our server with the champion's own packets (hero16.Hero: movement 61, attack 906 + 972, damage,
death and return as the live server's recipes).

The rules are ours (as the 13.3 world's bots, LeagueSandbox-like): each bot has a lane (its role in the game info:
TOP / MIDDLE / BOTTOM; JUNGLE and UTILITY go with MIDDLE and BOTTOM - there are no jungle camps yet); it walks its
lane's polyline (the minions' own lane, world16), stands behind its lane's front minion (420 back for a ranged
champion, 140 for a melee one), attacks the weakest enemy minion in reach, an enemy champion that comes near when it
is healthy, an enemy structure with two of its own minions under it; never stands in an enemy turret's reach without
two of its own minions there; goes home under 30 % health, back out at 90 %; heals at the fountain.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hero16    # noqa: E402

THINK = 0.25
LEAVE = 15.5               # bots leave the fountain once its gates open (15.084, measured)
SIGHT = 900.0
TURRET_DANGER = 775.0 + 88.4 + 150.0
ROLE_LANE = {'TOP': 'top', 'MIDDLE': 'mid', 'BOTTOM': 'bot', 'UTILITY': 'bot', 'JUNGLE': 'mid'}


class Bot(hero16.Hero):
    def __init__(self, net, champion, team, role, place, values, world):
        super().__init__(net, speed=345.0, place=place, values=values)
        self.set_champion(champion)
        self.speed = self.base['speed']
        self.team, self.role = team, role
        self.lane = ROLE_LANE.get(role, 'mid')
        self.ranged = self.range > 300
        self.ATTACK_PERIOD = 1.0 / 0.65 if not self.ranged else 1.0 / 0.66
        self.max_hp = self.hp = self.stats_at(1)['mMaxHP']
        self.world = world
        b = next((b for b, d in world.barracks.items() if d['team'] == team and d['lane'] == self.lane), None)
        self.lane_path = world.paths[b] if b is not None else None
        self.poly = None              # a walk along points: (Path, start time)
        self.goal = None
        self.next_think = LEAVE
        self.retreat = False

    # ---------------------------------------------------------------- where it is
    def place(self, t=None):
        t = self.now if t is None else t
        if self.poly is not None:
            path, t0 = self.poly
            return path.at((t - t0) * self.speed)
        return super().place(t)

    def walk_points(self, t, points):
        """a walk through points from where it is now -> the movement packet"""
        import world16
        here = self.place(t)
        pts = [here] + [p for p in points if math.dist(p, here) > 1.0]
        self.poly = (world16.Path(pts), t)
        self.a = self.b = pts[-1]
        self.t0 = t
        return self.move_packet(t, pts)

    # ---------------------------------------------------------------- what it does
    def think(self, t, world):
        out = []
        self.now = t
        if not self.alive or t < self.next_think:
            return out
        self.next_think = t + THINK
        here = self.place(t)
        if math.dist(here, self.home) < 1000.0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 0.085 * self.max_hp * THINK * 4)
            out.append(self.replication(t, {'mHP': self.hp}))
        if self.retreat and self.hp >= 0.9 * self.max_hp:
            self.retreat = False
        if not self.retreat and self.hp < 0.3 * self.max_hp:
            self.retreat, self.target = True, None
        if self.retreat:
            return out + self.go(t, self.home)
        tgt = world.unit(self.target) if self.target else None
        if tgt is None or not tgt.alive or math.dist(here, tgt.place()) > SIGHT + 300:
            tgt = self.choose(t, here, world)
            self.target = tgt.net if tgt is not None else None
        if tgt is not None:
            self.poly = None                       # hero16.Hero.tick chases and attacks the target
            return out
        return out + self.go(t, self.post(t, world))

    def go(self, t, goal):
        if goal is None:
            return []
        here = self.place(t)
        if math.dist(here, goal) < 60 or (self.goal is not None and math.dist(self.goal, goal) < 120 and self.poly is not None):
            return []
        self.goal = goal
        pts = self.route(here, goal)
        if len(pts) == 1:
            return [hero16.Hero.walk(self, t, goal)]        # off the lane (the fountain): around walls on the grid
        return [self.walk_points(t, pts)]

    def route(self, here, goal):
        """along the lane's polyline between the two points (the lanes are open ground), else straight"""
        P = self.lane_path
        if P is None:
            return [goal]
        sa, sb = self.along(here), self.along(goal)
        if sa is None or sb is None:
            return [goal]
        if abs(sa - sb) < 1.0:
            return [goal]
        idx = [i for i, c in enumerate(P.cum) if min(sa, sb) < c < max(sa, sb)]
        pts = [P.p[i] for i in (idx if sb > sa else reversed(idx))]
        return pts + [goal]

    def along(self, p):
        """the lane distance of the lane point nearest to p (None when p is far from the lane: the fountain)"""
        P = self.lane_path
        best = None
        for i in range(len(P.p) - 1):
            a, b = P.p[i], P.p[i + 1]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz or 1.0
            k = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
            q = (a[0] + dx * k, a[1] + dz * k)
            d = math.dist(p, q)
            if best is None or d < best[0]:
                best = (d, P.cum[i] + k * math.sqrt(L2))
        return best[1] if best and best[0] < 1500 else None

    def post(self, t, world):
        """behind the lane's front minion of its own team, else behind its first standing turret of the lane"""
        P = self.lane_path
        if P is None:
            return self.home
        mine = [m.s for m in world.units.values() if m.alive and m.team == self.team and m.lane == self.lane and m.started]
        back = 420.0 if self.ranged else 140.0
        if mine:
            s = max(mine) - back
        else:
            own = []
            if world.structs is not None:
                order = {'outer': 0, 'inner': 1, 'inhibitor': 2}
                own = sorted((order[x.tier], self.along(x.xy)) for x in world.structs.all.values()
                             if x.alive and x.team == self.team and x.lane == self.lane and x.tier in order)
            s = (own[0][1] - 250.0) if own and own[0][1] is not None else 2500.0
        for _ in range(12):
            q = P.at(s)
            if not self.danger(q, world):
                break
            s -= 200.0
        return P.at(max(s, 600.0))

    def danger(self, q, world):
        if world.structs is None:
            return False
        for x in world.structs.all.values():
            if x.alive and x.team != self.team and x.tier not in ('dampener', 'hq', 'fountain') and math.dist(q, x.xy) < TURRET_DANGER:
                cover = sum(1 for m in world.units.values() if m.alive and m.team == self.team and math.dist(m.xy, x.xy) < 863.4)
                if cover < 2:
                    return True
        return False

    def choose(self, t, here, world):
        if self.hp > 0.45 * self.max_hp:
            champs = [(math.dist(here, h.place()), h) for h in world.champions()
                      if h.alive and h.team != self.team and h is not self]
            champs = [c for c in champs if c[0] <= SIGHT * 0.7 and not self.danger(c[1].place(), world)]
            if champs:
                return min(champs, key=lambda c: c[0])[1]
        best = None
        for m in world.units.values():
            if m.alive and m.team != self.team and math.dist(here, m.xy) <= self.range + 350 and not self.danger(m.xy, world):
                if best is None or m.hp < best.hp:
                    best = m
        if best is not None:
            return best
        if world.structs is not None:
            s = world.structs.near(self.team, here, self.range + 500)
            if s is not None:
                cover = sum(1 for m in world.units.values() if m.alive and m.team == self.team and math.dist(m.xy, s.xy) < 863.4)
                if cover >= 2:
                    return s
        return None


class Bots:
    def __init__(self, world, rec, player_net):
        """rec: match16.Recording (the start state's champions, their values and roles)"""
        self.list = []
        roles = rec.roles() if hasattr(rec, 'roles') else {}
        for net, place in rec.heroes():
            if net == player_net:
                continue
            team = 'order' if place[0] + place[1] < 14800 else 'chaos'
            b = Bot(net, rec.champions.get(net, 'Garen'), team, roles.get(net, 'MIDDLE'), place, rec.hero_values(net), world)
            self.list.append(b)
            world.heroes[net] = b

    def tick(self, t, world):
        out = []
        for b in self.list:
            out += b.think(t, world)
            out += b.tick(t, world)
        return out
