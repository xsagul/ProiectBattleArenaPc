"""A real 16.20 match from its replay (.rofl, ROFL v2: rofl2.py), in memory: what Riot's server sent the match's
spectators, packet by packet, read with the client's own formats (pkt_schema). The evidence for what a champion's
abilities make the server do - its dialect is the spectator's (see reference notes: 62 ids never reach a player,
e.g. a minion's 439 is top level here and inside a 239 container live), the events and their order are the same.

    R = replaydb16.Replay(path)          the blocks of the replay's chunks, cached as a pickle beside it
    R.rows                               [(time, channel, packet id, net id, body)] in order
    R.parse(pid, body)                   the values (None: no learnt format / not read)
    R.inner(values)                      a 239 container's packets -> [(pid, net, body)]
    R.heroes                             {net id: {'champion', 'player', 'team'}} from the 222 packets (hero creation)
    R.flat()                             every packet with containers opened: (time, channel, pid, net, body, in_container)

    python server/replaydb16.py <file.rofl>        the heroes and the packet ids by count
"""
import collections
import os
import pickle
import struct
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('BA_PATCH', '1620')
sys.modules.setdefault('decoded', types.ModuleType('decoded'))

CONTAINER, REPL, MOVE, HERO, CAST = 239, 287, 61, 222, 1215
READ_ONLY = os.path.join(HERE, '..', 'data', 'exe1620', 'codec_fx')     # formats for reading replays only
CACHE_VERSION = 1


class Replay:
    def __init__(self, path, cache=True):
        """cache: keep the rows as <id>.rows.pkl (60-130 MB a replay) for the next reads"""
        self.path = path
        cache = os.path.splitext(path)[0] + '.rows.pkl'
        if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
            try:
                ver, self.rows = pickle.load(open(cache, 'rb'))
            except Exception:                    # cut short (a process stopped while writing it): read the replay
                ver, self.rows = None, None
                os.remove(cache)
            if ver != CACHE_VERSION:
                self.rows = None
        else:
            self.rows = None
        if self.rows is None:
            import rofl2
            r = rofl2.Rofl2(path)
            self.version = r.version
            self.rows = [(t, ch, pid, obj, bytes(body)) for e, (t, ch, pid, obj, body) in rofl2.stream(r, kinds=(1,))]
            if cache:
                pickle.dump((CACHE_VERSION, self.rows), open(cache, 'wb'), protocol=4)
        self._sc = {}
        self._heroes = None

    def schema(self, pid):
        if pid not in self._sc:
            import pkt_schema as PS
            try:
                if os.path.exists(os.path.join(READ_ONLY, f'{pid}.tree.json')):
                    # [10-12] a format learnt on a 16.20 replay that reads the replays' packets of this id (the server's
                    # own, learnt elsewhere, cannot: 10's instance +0x2c mode 1) - for reading only
                    out, PS.OUT = PS.OUT, READ_ONLY
                    try:
                        self._sc[pid] = PS.Schema.load(pid, borrow=False)
                    finally:
                        PS.OUT = out
                else:
                    self._sc[pid] = PS.Schema.load(pid)
            except Exception:
                self._sc[pid] = None
        return self._sc[pid]

    def parse(self, pid, body):
        import pkt_schema as PS
        sc = self.schema(pid)
        if sc is None:
            return None
        try:
            return PS.parse(sc, body)
        except Exception:
            return None

    def inner(self, values):
        import forms16
        try:
            return forms16.unpack(values)
        except Exception:
            return []

    def flat(self, ids=None, with_container=False, skip=()):
        """every packet, a container's packets in its place: (time, channel, pid, net, body, in_container
        [, the container's row index or None]); skip: ids left out"""
        for k, (t, ch, pid, net, body) in enumerate(self.rows):
            if pid in skip:
                continue
            if pid == CONTAINER:
                v = self.parse(pid, body)
                for p, n, b in (self.inner(v) if v is not None else []):
                    if (ids is None or p in ids) and p not in skip:
                        yield (t, ch, p, n, b, True, k) if with_container else (t, ch, p, n, b, True)
                continue
            if ids is None or pid in ids:
                yield (t, ch, pid, net, body, False, None) if with_container else (t, ch, pid, net, body, False)

    @property
    def heroes(self):
        """{net id: {'champion', 'time'}}: the replay's chunks hold no hero creation (222); a champion's casts (1215)
        carry its name (+0x18 +0xd0 +0x28) - every champion casts something within its first minutes"""
        if self._heroes is None:
            self._heroes = {}
            champs = champion_names()
            for t, ch, pid, net, body in self.rows:
                if pid != CAST or net in self._heroes:
                    continue
                v = self.parse(pid, body)
                name = text(((v or {}).get('+0x18') or {}).get('+0xd0', {}).get('+0x28', {}))
                if name.lower() in champs:
                    self._heroes[net] = {'champion': champs[name.lower()], 'time': t}
        return self._heroes


def text(x):
    try:
        return bytes.fromhex(x['text']).decode('latin-1').rstrip('\0')
    except Exception:
        return ''


_names = None


def champion_names():
    """lower-cased name -> the champion's name as the game writes it"""
    global _names
    if _names is None:
        sys.path.insert(0, os.path.dirname(HERE))
        from server.core import gamedata as G
        _names = {c['alias'].lower(): c['alias'] for c in G.champion_index()}
    return _names


if __name__ == '__main__':
    R = Replay(sys.argv[1])
    print(len(R.rows), 'packets, time', round(R.rows[0][0], 2), '..', round(R.rows[-1][0], 2))
    for n, h in R.heroes.items():
        print(f"  {n:08x} {h['champion']:14s} first cast {h['time']:.1f}")
    print(collections.Counter(r[2] for r in R.rows).most_common(40))
