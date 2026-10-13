"""A champion's Q / W / E / R in the real client against our server, on an enemy champion standing still in the
middle lane, with the screen saved after each cast and tiled into one sheet per spell.

    python tools/spell_client16.py <Champion> [--spells QWER] [--foe-dist 450]

Game seconds: 18 level 18 + all spells learnt, 20 the champion at (6700, 6700) and the dummy at the aimed place, then
a cast every 5.5 s from 23 s (the champion and the dummy are put back before each one); twelve screens from +0.1 to +2.8 s
of each cast. The camera is locked on the champion (space held by tools/game_input.ps1).
Output: data/exe1620/match_sp_<Champion>/ (server.txt, r3dlog.txt, shots/, sheet_<Q|W|E|R>.jpg).
Needs the Vanguard driver stopped (run_match16 refuses otherwise).
"""
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ME = (6700.0, 6700.0)
SHOTS = (0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0, 1.2, 1.4, 1.7, 2.1, 2.8)
FIRST, EVERY = 23.0, 5.5


def main():
    argv = sys.argv[1:]
    champ = argv[0]
    spells = argv[argv.index('--spells') + 1] if '--spells' in argv else 'QWER'
    far = float(argv[argv.index('--foe-dist') + 1]) if '--foe-dist' in argv else 450.0
    foe = (ME[0] + far / math.sqrt(2), ME[1] + far / math.sqrt(2))
    out = os.path.join(ROOT, 'data', 'exe1620', f'match_sp_{champ}')
    shots_dir = os.path.join(out, 'shots')
    if os.path.isdir(shots_dir):
        for f in os.listdir(shots_dir):
            os.remove(os.path.join(shots_dir, f))
    skills = ';'.join(f'{18.2 + 0.05 * i:.2f}:{s}' for i, s in enumerate([3, 0, 1, 2] * 5))
    at, dummy, casts, shots = [f'20:{ME[0]:.0f},{ME[1]:.0f}'], [f'20:{foe[0]:.0f},{foe[1]:.0f}'], [], []
    for k, sp in enumerate(spells):
        t = FIRST + EVERY * k
        at.append(f'{t - 0.8:.2f}:{ME[0]:.0f},{ME[1]:.0f}')
        dummy.append(f'{t - 0.8:.2f}:{foe[0]:.0f},{foe[1]:.0f}')
        casts.append(f'{t:.2f}:{"QWER".index(sp)}:{foe[0]:.0f},{foe[1]:.0f}')
        shots += [t + d for d in SHOTS]
    end = FIRST + EVERY * len(spells) + 1.0
    server = [sys.executable, '-u', os.path.join(ROOT, 'server', 'main16.py'), '--champion', champ] +         (['--no-fog'] if '--no-fog' in argv else []) + [
              '--level', '18:18', '--skill', skills, '--at', ';'.join(at), '--dummy', ';'.join(dummy),
              '--cast', ';'.join(casts), '--shots', ','.join(f'{x:.2f}' for x in shots), '--shots-dir', shots_dir]
    env = dict(os.environ, BA_INPUT=';'.join(f'{s}:key:space' for s in range(16, int(end) + 22, 2)))
    wall = end + 19.0                                    # the game clock starts ~14.5 s after the client does
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'run_match16.py'), f'{wall:.0f}', f'sp_{champ}'] + server,
                   env=env, cwd=ROOT)
    sheets(out, shots_dir, spells)


def sheets(out, shots_dir, spells):
    from PIL import Image, ImageDraw
    for k, sp in enumerate(spells):
        t = FIRST + EVERY * k
        tiles = []
        for d in SHOTS:
            p = os.path.join(shots_dir, f'g{t + d:07.2f}.jpg')
            if not os.path.exists(p):
                continue
            im = Image.open(p)
            w, h = im.size
            im = im.crop((int(w * 0.2), int(h * 0.08), int(w * 0.8), int(h * 0.78)))
            im = im.resize((320, 225))
            ImageDraw.Draw(im).text((6, 4), f'{sp} +{d:.2f}s', fill=(255, 255, 0))
            tiles.append(im)
        if not tiles:
            continue
        sheet = Image.new('RGB', (320 * 4, 225 * 3))
        for i, im in enumerate(tiles):
            sheet.paste(im, (320 * (i % 4), 225 * (i // 4)))
        sheet.save(os.path.join(out, f'sheet_{sp}.jpg'), quality=82)
    print('sheets in', out)


if __name__ == '__main__':
    main()
