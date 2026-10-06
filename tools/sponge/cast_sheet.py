"""Contact sheet of a match's frames around each of our casts: frame times from the bmp files, matched to the server's
"capture asked" lines (lol13.3/sponge/frame_*.bmp + research/exe133/match_<name>/server.txt).

  cast_sheet.py <name> [dt,dt,...]     -> research/exe133/match_<name>/frames/sheet.png
"""
import glob
import os
import re
import sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
name = sys.argv[1]
dts = [float(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '0.15,0.4,0.8,1.5').split(',')]
M = os.path.join(ROOT, 'research', 'exe133', f'match_{name}')
fs = sorted(glob.glob('C:/Users/Sorin/Desktop/lol13.3/sponge/frame_*.bmp'))
mt = [os.path.getmtime(f) for f in fs]
log = open(os.path.join(M, 'server.txt'), encoding='utf8', errors='replace').read()
caps = [float(m) for m in re.findall(r'^\s*([\d.]+)\s+capture asked', log, re.M)]
casts = [(float(t), n) for t, n in re.findall(r'^\s*([\d.]+) snd data .*our 49[: (]+(\w+)', log, re.M)]
off = mt[0] - caps[0]
rows = []
for ct, sp in casts:
    row = []
    for dt in dts:
        i = min(range(len(fs)), key=lambda k: abs(mt[k] - off - ct - dt))
        im = Image.open(fs[i]).crop((650, 180, 1250, 620)).resize((360, 264))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 170, 18), fill=(0, 0, 0))
        d.text((3, 3), f'{sp} +{mt[i] - off - ct:.2f}s', fill=(255, 255, 0))
        row.append(im)
    rows.append(row)
sheet = Image.new('RGB', (360 * len(dts), 264 * max(1, len(rows))))
for r, row in enumerate(rows):
    for c, im in enumerate(row):
        sheet.paste(im, (c * 360, r * 264))
os.makedirs(os.path.join(M, 'frames'), exist_ok=True)
sheet.save(os.path.join(M, 'frames', 'sheet.png'))
print(len(fs), 'frames,', len(casts), 'casts')
