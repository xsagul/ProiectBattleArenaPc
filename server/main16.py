"""Our 16.20 game server.

    python server/main16.py [options] <port>            serve one match to a game16 client
    python server/main16.py --sim <seconds> [options]   run the match alone (no client) and print what happened

Options:
    --champion <Name>            the player's champion (default: the recorded one, Garen)
    --bots <A,B,C,D,E,F,G,H,I>   the nine other champions, allies first ('random' = any; default: the recorded ones)
    --roster <file.json>         the whole roster: [{"champion": .., "name": .., "bot": true}, ...] (the launcher's)
    --seed <n>                   the match's random seed
  test aids (game seconds):
    --at "<s>:<x>,<z>"           put the player's champion there
    --attack "<s>:<net id hex>"  an attack order
    --level "<s>:<n>"            give experience up to level n
    --skill "<s>:<slot>"         a skill point (slot 0..3), may repeat as "5:0;6:1"
    --cast "<s>:<slot>:<x>,<z>"  a cast towards a place, may repeat with ';'
    --attack-near "<s>:x"        an attack order on the nearest enemy unit or monster
    --buy "<s>:<item id>"        a purchase (as the shop's request would)
    --shots "<s>,<s>" [--shots-dir <dir>]   the screen saved at those game seconds
    --summoners <a>,<b>          the player's two summoner spells by name (SummonerFlash, SummonerDot = Ignite,
                                 SummonerHeal, SummonerHaste = Ghost, SummonerBarrier, SummonerExhaust, SummonerSmite,
                                 SummonerTeleport, SummonerBoost = Cleanse)
    --skin <n>                   the player's skin number
    --runes <page>               the player's rune page: Conqueror, Electrocute, PressTheAttack, SummonAery,
                                 GraspOfTheUndying (default: by the champion's class)
    --no-fog                     everything is in the player's sight (no fog of war)
    --recall "<s>:x"             the player's champion recalls
    --slay "<s>:x|own"           the nearest enemy champion dies by the player's hand (own: the player dies)
    --raze "<s>:<lane>[:own]"    the next standing structure of the enemy's (own) lane falls, e.g. "30:mid;35:mid"
    --gold <n>                   starting gold
    --speed <x>                  the simulation's time runs x times faster (only with --sim)
"""
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('BA_PATCH', '1620')


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def roster_of(args):
    from core import gamedata as G
    if '--roster' in args:
        return json.load(open(opt(args, '--roster')))
    names = [None] * 10
    if '--champion' in args:
        names[0] = opt(args, '--champion')
    if '--bots' in args:
        seed = int(opt(args, '--seed', 0)) or None
        given = opt(args, '--bots').split(',')
        rnd = G.random_roster(names[0], seed)             # by position: top, jungle, middle, bottom, support
        for i in range(9):
            n = given[i] if i < len(given) else given[-1]
            names[i + 1] = rnd[i + 1] if n == 'random' else n
    return [{'champion': n} if n else {} for n in names]


def options_of(args):
    o = {'no_fog': '--no-fog' in args}
    if '--summoners' in args:
        o['summoners'] = opt(args, '--summoners').split(',')
    if '--skin' in args:
        o['skin'] = int(opt(args, '--skin'))
    if '--runes' in args:
        o['runes'] = opt(args, '--runes')
    return o


def hooks_of(args):
    """test aids as functions run before every frame"""
    hooks = []

    def timed(name, fn):
        if name not in args:
            return
        for item in opt(args, name).split(';'):
            when, rest = item.split(':', 1)
            state = {'done': False}

            def hook(s, t, when=float(when), rest=rest, state=state):
                if not state['done'] and t >= when:
                    state['done'] = True
                    fn(s, rest)
            hooks.append(hook)

    def put(s, rest):
        s.player.teleport(tuple(float(c) for c in rest.split(',')))
        s.player.order = None
    timed('--at', put)
    timed('--attack', lambda s, rest: s.player.order_attack(int(rest, 16)))
    timed('--skill', lambda s, rest: s.log(f'skill {rest}: {s.player.level_spell(int(rest))}'))

    def level(s, rest):
        h = s.player
        table = s.game.data['xp_per_level']
        h.add_xp(table[int(rest) - 2] - h.xp + 1)
    timed('--level', level)

    def cast(s, rest):
        slot, where = rest.split(':')
        x, z = (float(c) for c in where.split(','))
        if s.game.spells is not None:
            s.log(s.game.spells.request(s.player, {'slot': int(slot), 'target': 0, 'target_place': (x, z), 'cursor': (x, z),
                                                   'caster_place': s.player.pos, 'flags': 0, 'hash': 0}))
    timed('--cast', cast)

    def near(s, rest):
        h = s.player
        c = [u for u in s.game.units.values() if u.alive and u.targetable and u.team != h.team]
        if c:
            u = min(c, key=lambda u: (u.pos[0] - h.pos[0]) ** 2 + (u.pos[1] - h.pos[1]) ** 2)
            h.order_attack(u.net)
            s.log(f'attack order on the nearest unit: {u}')
    timed('--attack-near', near)                         # "<s>:x" an attack order on the nearest enemy / monster

    def raze(s, rest):
        g, h = s.game, s.player
        lane, team = rest, (200 if h.team == 100 else 100)
        if ':' in rest:
            lane, side = rest.split(':')
            team = h.team if side == 'own' else team
        order = [('turret', 'outer'), ('turret', 'inner'), ('turret', 'inhibitor'), ('inhibitor', None), ('turret', 'nexus'), ('nexus', None)]
        for kind, tier in order:
            for u in g.structures:
                if u.alive and u.team == team and u.kind == kind and (tier is None or u.tier == tier) and \
                        (kind in ('nexus',) or tier == 'nexus' or u.lane == lane):
                    killer = h if team != h.team else next(e for e in g.heroes if e.team != h.team)
                    u.hp = 0.0
                    u.set('mHP', 0.0)
                    g.kill(u, killer)
                    s.log(f'razed: {u}')
                    return
    def slay(s, rest):
        g, h = s.game, s.player
        own = rest == 'own'
        c = [u for u in g.heroes if u.alive and u is not h and (u.team == h.team) == own]
        if own:
            c, killer = [h], min((u for u in g.heroes if u.team != h.team), key=lambda u: (u.pos[0] - h.pos[0]) ** 2 + (u.pos[1] - h.pos[1]) ** 2)
        else:
            killer = h
        if c:
            u = min(c, key=lambda u: (u.pos[0] - h.pos[0]) ** 2 + (u.pos[1] - h.pos[1]) ** 2)
            u.last_hit_by[killer.net] = g.t
            g.deal(killer, u, u.hp + 1000.0, 2, basic=True)
            s.log(f'slain: {u.name} by {killer.name}')
    def dummy(s, rest):
        g, h = s.game, s.player
        u = next(e for e in g.heroes if e.team != h.team)
        u.brain = None
        u.order = None
        u.target = None
        u.path = None
        u.teleport(tuple(float(c) for c in rest.split(',')))
        u.set_hp(u.max_hp)
        s.log(f'dummy: {u.name} stands at {rest}')
    def run_py(s, rest):
        exec(compile(open(rest, encoding='utf-8').read(), rest, 'exec'), {'s': s, 'g': s.game, 'me': s.player})
    timed('--py', run_py)                                # "<s>:<file.py>" a test script run at that game second (s, g, me)
    timed('--dummy', dummy)                              # "<s>:x,z" an enemy champion is put there, whole, and stands still
    timed('--recall', lambda s, rest: s.log(s.game.spells.recall(s.player)))      # "<s>:x" the player recalls
    timed('--slay', slay)                                # "<s>:x" the nearest enemy champion dies by the player; "<s>:own" the player dies
    timed('--raze', raze)                                # "<s>:<lane>[:own]" the lane's next standing structure falls
    timed('--buy', lambda s, rest: s.log(s.game.shop.buy(s.player, int(rest))))      # "<s>:<item id>"

    # --shots "62.3,62.6" [--shots-dir <dir>]: the screen saved at those game seconds (a thread: the loop goes on)
    if '--shots' in args:
        import threading
        out = opt(args, '--shots-dir', os.path.join(HERE, '..', 'data', 'exe1620', 'shots'))
        os.makedirs(out, exist_ok=True)
        times = sorted(float(x) for x in opt(args, '--shots').split(','))

        def grab(name):
            try:
                from PIL import ImageGrab
                im = ImageGrab.grab()
                im.convert('RGB').resize((1280, 720)).save(os.path.join(out, name), quality=80)
            except Exception as e:
                print('shot failed:', e, flush=True)

        def shots(s, t):
            while times and t >= times[0]:
                when = times.pop(0)
                threading.Thread(target=grab, args=(f'g{when:07.2f}.jpg',), daemon=True).start()
        hooks.append(shots)

    # --key "<s>:<key>": a key press in the game window at a game second (test input timed by the game clock)
    return hooks


def simulate(args):
    """the match without a client: every frame's packets are made (and so encoded); a digest at the end"""
    import collections
    from core.session import Session
    from core.game import DT
    seconds = float(opt(args, '--sim'))
    s = Session(roster_of(args), log=lambda x: print(x, flush=True) if '--quiet' not in args else None,
                options=options_of(args))
    s.hooks = hooks_of(args)
    if '--gold' in args:
        s.player.gold = float(opt(args, '--gold'))
    g = s.game
    sent = collections.Counter()
    size = 0
    t0 = time.time()
    worst = 0.0
    g.start_packets()
    while g.t < seconds:
        for fn in s.hooks:
            fn(s, g.t + DT)
        f0 = time.perf_counter()
        out = g.step(DT)
        worst = max(worst, time.perf_counter() - f0)
        for ch, pid, net, body in out:
            sent[pid] += 1
            size += len(body) + 3
    dt = time.time() - t0
    print(f'{seconds:.0f} game s in {dt:.1f} s ({g.frame} frames, mean {1000 * dt / max(1, g.frame):.2f} ms, worst {1000 * worst:.1f} ms); '
          f'{sum(sent.values())} packets, {size / 1024:.0f} KB ({size / 1024 / seconds:.1f} KB/s)')
    print('packets by id:', dict(sorted(sent.items())))
    for lane in ('top', 'mid', 'bot'):
        ms = [m for m in g.minions if m.alive and m.lane == lane]
        o = [m for m in ms if m.team == 100]
        c = [m for m in ms if m.team == 200]
        front = lambda xs: tuple(round(v) for v in max(xs, key=lambda m: m.lane_i).pos) if xs else None
        print(f'  {lane}: order {len(o)} (front {front(o)}), chaos {len(c)} (front {front(c)})')
    for h in g.heroes:
        print(f'  {h.name:12} lvl {h.level} hp {h.hp:.0f}/{h.max_hp:.0f} gold {h.gold:.0f} k/d/a {h.kills}/{h.deaths}/{h.assists} cs {h.cs} '
              f'at ({h.pos[0]:.0f}, {h.pos[1]:.0f}) {"" if h.alive else "DEAD"}')
    down = [s_ for s_ in g.structures if not s_.alive]
    print(f'  structures down: {len(down)}', [(x.kind, x.team, x.lane, x.tier) for x in down], '| over:', g.over)


def main():
    args = sys.argv[1:]
    if '--sim' in args:
        return simulate(args)
    import net16
    from core.session import Session
    port = int(args[-1])
    t0 = time.time()
    s = Session(roster_of(args), options=options_of(args))
    s.hooks = hooks_of(args)
    if '--gold' in args:
        s.player.gold = s.player.gold_total = float(opt(args, '--gold'))
    s.server = net16.Server(port, s, log=s.log_fn)
    s.log(f'ready in {time.time() - t0:.1f} s: ' + ', '.join(f'{h.name}{"" if h.bot else " (player)"}' for h in s.game.heroes))
    s.server.run()


if __name__ == '__main__':
    main()
