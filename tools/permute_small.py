"""The variant searcher on what the generic lifter got almost right: functions gen_small lifts to C++ whose
compiled code is not the client's yet. Each is written to its own file, searched for a while, and a body that
comes out identical is kept in tools/small_found.json for gen_small to use (it verifies it again in its shard).
No model is involved: this can run for hours on the processor alone.

  permute_small.py <first rva hex> <end rva hex> [--seconds N per function] [--limit N] [--seed N]
"""
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import match_func as M  # noqa: E402
import gen_small as S  # noqa: E402
import gen_sources as G  # noqa: E402
import permute  # noqa: E402

FOUND = os.path.join(HERE, 'small_found.json')
WORK = os.path.join(M.OUT, 'permute_small')
NL = chr(10)


def found():
    return json.load(open(FOUND, encoding='utf-8')) if os.path.exists(FOUND) else {}


def main():
    a = sys.argv[1:]
    first, end = int(a[0], 16), int(a[1], 16)
    seconds = float(a[a.index('--seconds') + 1]) if '--seconds' in a else 30
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else None
    rng = random.Random(int(a[a.index('--seed') + 1]) if '--seed' in a else 0)
    os.makedirs(WORK, exist_ok=True)
    im = G.Image()
    A = S.lift_all(S.Image(), first, end)
    done = found()
    todo = [r for r in sorted(A['lifted']) if r not in im.done and f'{r:x}' not in done]
    rng.shuffle(todo)
    tried = won = 0
    t0 = time.time()
    for rva in todo:
        if limit is not None and tried >= limit:
            break
        item = S.render(A, rva, {})
        if not item:
            continue
        path = os.path.join(WORK, f's{rva:x}.cpp')
        with open(path, 'w', encoding='utf-8', newline=NL) as f:
            f.write(NL.join(S.source(A, {rva: item}, 'one lifted function', probe=True)) + NL)
        try:
            obj = M.compile_obj(path, M.FLAGS)
            if M.compare(path, item['symbol'], rva, M.FLAGS, obj)[3] is None:
                continue                    # identical alone: its shard's generator has (or will have) it
            tokens = permute.search(path, rva, seconds / 60, quiet=True)
        except SystemExit as e:
            print(f'{rva:x}: skipped: {str(e)[:120]}')
            continue
        tried += 1
        if tokens:
            won += 1
            done = found()
            done[f'{rva:x}'] = dict(symbol=item['symbol'], head=item['lines'][0],
                                    body=permute.text_of(tokens).split(NL))
            with open(FOUND, 'w', encoding='utf-8', newline=NL) as f:
                json.dump(done, f, indent=1, sort_keys=True)
        print(f'--- {tried} searched, {won} found, {time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':
    main()
