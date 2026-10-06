"""Reads the game version (and the champions/skins when present) from a .rofl replay's header, local or by URL (only the
first bytes are fetched). ROFL v1 (up to 14.8): "RIOT" magic, 256-byte signature, u16 header length, u32 file length,
u32 metadata offset, u32 metadata length, ...; the metadata is JSON with gameVersion and statsJson (per player SKIN).
ROFL2 (14.9+) keeps the version in plain text near the start.

    python tools/rofl_version.py <file or URL> [...]
"""
import json
import re
import struct
import sys
import urllib.request


def head(src, n):
    if src.startswith('http'):
        req = urllib.request.Request(src, headers={'Range': f'bytes=0-{n - 1}', 'User-Agent': 'ba-research'})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read(n)
    with open(src, 'rb') as f:
        return f.read(n)


def info(src):
    b = head(src, 4096)
    if not b.startswith(b'RIOT'):
        return {'error': 'not a rofl'}
    if b[4:6] == b'\x00\x00' and len(b) > 288:
        hl, fl, mo, ml = struct.unpack_from('<HIII', b, 262)
        if mo + ml > len(b):
            b = head(src, mo + ml)
        meta = json.loads(b[mo:mo + ml].decode('utf-8', 'replace'))
        out = {'format': 'ROFL', 'gameVersion': meta.get('gameVersion'), 'length_ms': meta.get('gameLength')}
        try:
            stats = json.loads(meta.get('statsJson', '[]'))
            out['players'] = [(p.get('SKIN'), p.get('NAME') or p.get('RIOT_ID_GAME_NAME')) for p in stats]
        except Exception:
            pass
        return out
    m = re.search(rb'\d+\.\d+\.\d+\.\d+', b)
    return {'format': 'ROFL2?', 'version': m.group(0).decode() if m else None}


if __name__ == '__main__':
    for s in sys.argv[1:]:
        try:
            print(s, info(s))
        except Exception as e:
            print(s, 'error', e)
