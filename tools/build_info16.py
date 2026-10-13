"""The game info packet (618: the roster the loading screen and the scoreboard show) as a template our server can
fill for any roster.

618's whole format is not learnt (its last struct, the match configuration, defeats the learner), but its player
records are: this tool runs the client's own reader over the recorded live 618 (the emulator, once), takes the wire
span of every player record (struct 0xfcca30 with its child) and of every per-player entry of the second list
(struct 0xfc6e10), decodes each with the learnt struct formats, and writes data/exe1620/info16.json:
    {'body': hex of the recorded packet, 'players': [{'span': [a, b], 'key': struct, 'values': {...}}, ...],
     'extras': [...]}
The server re-encodes the records it changes and splices them into the recorded bytes (core/session.py).

    python tools/build_info16.py [data/live/<gameId>]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
os.environ['BA_PATCH'] = '1620'
game = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(ROOT, 'data', 'live', '4013831789')
os.environ['BA_LIVE'] = game
import types                                  # noqa: E402
sys.modules.setdefault('decoded', types.ModuleType('decoded'))
import pkt_schema as PS                       # noqa: E402
import pkt_tree as PT                         # noqa: E402

PLAYER, EXTRA = 0xfcca30, 0xfc6e10
SKIP = 1


def main():
    T = PT.Tree(618)
    body = T.body
    sc = PS.Schema.load(618)
    out = {'body': body.hex(), 'players': [], 'extras': []}
    for fn, name in ((PLAYER, 'players'), (EXTRA, 'extras')):
        key = f'{fn:#x}'
        for inst in T.of(fn):
            # the reader's cursor counts from the net id byte in front of the body: the body's offset is one less
            a, b = inst['start'] - SKIP, inst['end'] - SKIP
            try:
                v, end = PS.parse_struct(sc, key, body, a)
                assert a < end <= b, f'ends at {end}'
            except Exception as e:
                print(f'{name} at {a}..{b}: not parsed ({type(e).__name__} {e})')
                continue
            # the header bits as recorded: every field's mode, and the bits that belong to no field we know. The
            # client's reader refuses a record written with other (to our format, equivalent) modes, so the server
            # keeps these and changes values only [measured: emulator check, x_618]
            st = sc.structs[key]
            bits0 = int.from_bytes(body[a:a + st['header']], 'little')
            forced = {str(fl['bit']): (bits0 >> fl['bit']) & ((1 << fl['width']) - 1) for fl in st['fields']}
            spare = bits0
            for fl in st['fields']:
                spare &= ~(((1 << fl['width']) - 1) << fl['bit'])
            again = sc.encode_struct(key, v, {key: dict({int(k): m for k, m in forced.items()}, spare=spare)})
            back, end2 = PS.parse_struct(sc, key, again + body[end:b], 0)
            # 'tail': bytes of the span after the fields we read (kept as they are)
            out[name].append({'span': [a, b], 'key': key, 'values': v, 'tail': body[end:b].hex(), 'same': again == body[a:end],
                              'modes': forced, 'spare': spare,
                              'reads_back': back == v})
    json.dump(out, open(os.path.join(ROOT, 'data', 'exe1620', 'info16.json'), 'w'), indent=1)
    print(f'618: {len(body)} B; {len(out["players"])} player records, {len(out["extras"])} extra records; '
          f're-encoded identical: {sum(p["same"] for p in out["players"])} + {sum(p["same"] for p in out["extras"])}; '
          f'read back to the same values: {sum(p["reads_back"] for p in out["extras"])}')
    for p in out['players'][:3] + out['extras'][:2]:
        print(p['span'], json.dumps(p['values'])[:1500])


if __name__ == '__main__':
    main()
