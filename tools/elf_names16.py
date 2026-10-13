"""ELF hash -> name for the 16.20 game: every text in the property bins of every champion wad + Global, DATA, Map11.
Packets name buffs and spells by the ELF hash of the lower-cased name (packets.elf); this names them back.

  python tools/elf_names16.py build            -> data/exe1620/elf_names16.json (~ a few minutes)
  python tools/elf_names16.py find <hex> ..    hex as the packet shows it (little endian '6402ae09') or 0x09ae0264
"""
import io
import json
import os
import re
import sys

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
FINAL = os.path.join(ROOT, 'game16', 'DATA', 'FINAL')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'elf_names16.json')


def elf(name):
    h = 0
    for c in name.lower().encode():
        h = (h << 4) + c
        g = h & 0xf0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xffffffff
    return h


def wads():
    ch = os.path.join(FINAL, 'Champions')
    out = [os.path.join(ch, f) for f in sorted(os.listdir(ch)) if f.endswith('.wad.client') and f.count('.') == 2]
    out += [os.path.join(FINAL, n) for n in ('Global.wad.client', 'DATA.wad.client', 'DATA2.wad.client')]
    out += [os.path.join(FINAL, 'Maps', 'Shipping', 'Map11.wad.client')]
    return [w for w in out if os.path.exists(w)]


def bins(path):
    from wadx import Wad
    w = Wad(path)
    dz = zstandard.ZstdDecompressor()
    for h, (off, cs, us, t, sc) in w.entries.items():
        if us > 8 << 20 or (t & 0xf) not in (0, 3, 4):
            continue
        w.f.seek(off)
        raw = w.f.read(cs)
        if (t & 0xf) == 0:
            head = raw[:4]
        else:
            try:
                head = dz.stream_reader(io.BytesIO(raw), read_across_frames=True).read(4)
            except Exception:
                continue
        if head not in (b'PROP', b'PTCH'):
            continue
        try:
            yield w.read(h)
        except Exception:
            continue


def build():
    names = {}
    for path in wads():
        n = 0
        for d in bins(path):
            n += 1
            for m in re.finditer(rb'[\x20-\x7e]{3,200}', d):
                s = m.group().decode()
                for c in {s, s[1:], s[2:]} | set(re.split(r'[/.:]', s)):
                    if len(c) >= 3:
                        names.setdefault(f'{elf(c):08x}', c)
        print(os.path.basename(path), n, 'bins', len(names), flush=True)
    json.dump(names, open(OUT, 'w'))
    print(len(names), '->', OUT)


_d = None


def name(h):
    """h: int, or the packet's little-endian hex text"""
    global _d
    if _d is None:
        _d = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if isinstance(h, str):
        h = int.from_bytes(bytes.fromhex(h), 'little')
    return _d.get(f'{h:08x}')


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        build()
    else:
        for x in sys.argv[2:]:
            print(x, name(int(x, 16) if x.startswith('0x') else x))
