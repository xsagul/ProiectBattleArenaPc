"""Rebuild the whole ability evidence chain unattended: cast scan + samples of every replay (in parallel parts), the
per-champion shard, every champion's template, the geometry. The old outputs are kept beside (<dir>_old).

    python tools/rebuild_evidence16.py [parts, default 6]      -> log data/replays16/rebuild.log

Why (10-12): replay effect packets (10) could not be read when the evidence was built; replaydb16 reads them now
(data/exe1620/codec_fx), so the templates can hold the real server's effects and their ends (584).
"""
import glob
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data', 'replays16')
SPELLS = os.path.join(ROOT, 'data', 'exe1620', 'spells16')
LOG = os.path.join(DATA, 'rebuild.log')
ENV = dict(os.environ, BA_PATCH='1620', PYTHONIOENCODING='utf-8')


def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + msg + '\n')
    print(msg, flush=True)


def keep_old(path):
    old = path.rstrip('/\\') + '_old'
    if os.path.exists(path) and not os.path.exists(old):
        shutil.move(path, old) if os.path.isdir(path) and path != SPELLS else shutil.copytree(path, old)
    os.makedirs(path, exist_ok=True)


def run(args, out):
    with open(out, 'w', encoding='utf-8') as f:
        return subprocess.Popen([sys.executable, '-u'] + args, cwd=ROOT, env=ENV, stdout=f, stderr=subprocess.STDOUT)


def main():
    parts = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    t0 = time.time()
    for d in ('casts', 'samples'):
        keep_old(os.path.join(DATA, d))
    keep_old(SPELLS)
    ids = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(DATA, 'rofl', '*.rofl')))
    log(f'{len(ids)} replays, {parts} parts')
    chunks = [ids[i::parts] for i in range(parts)]
    procs = []
    for i, ch in enumerate(chunks):
        # one part: its scan, then its samples
        script = (f"import subprocess, sys; ids = {ch!r}; "
                  f"subprocess.run([sys.executable, '-u', 'tools/replay_evidence16.py', 'scan'] + ids); "
                  f"subprocess.run([sys.executable, '-u', 'tools/replay_evidence16.py', 'samples'] + ids)")
        procs.append(run(['-c', script], os.path.join(DATA, f'rebuild_part_{i:02d}.log')))
    for p in procs:
        p.wait()
    n_c = len(glob.glob(os.path.join(DATA, 'casts', '*.pkl')))
    n_s = len(glob.glob(os.path.join(DATA, 'samples', '*.pkl')))
    log(f'scan + samples done: {n_c} casts, {n_s} samples files ({(time.time() - t0) / 60:.0f} min)')
    if n_c < len(ids) * 0.9 or n_s < len(ids) * 0.9:
        log('too few outputs: stopping (the old evidence is in *_old)')
        return
    r = subprocess.run([sys.executable, '-u', 'tools/spell_templates16.py', 'shard'], cwd=ROOT, env=ENV,
                       capture_output=True, text=True)
    log('shard: ' + (r.stdout.strip().splitlines() or ['(no output)'])[-1])
    champs = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(DATA, 'by_champ', '*.pkl')))
    log(f'templates for {len(champs)} champions')
    with open(os.path.join(DATA, 'rebuild_templates.log'), 'w', encoding='utf-8') as f:
        subprocess.run([sys.executable, '-u', 'tools/spell_templates16.py'] + champs, cwd=ROOT, env=ENV, stdout=f,
                       stderr=subprocess.STDOUT)
    with open(os.path.join(DATA, 'rebuild_geom.log'), 'w', encoding='utf-8') as f:
        subprocess.run([sys.executable, '-u', 'tools/spell_geom16.py'], cwd=ROOT, env=ENV, stdout=f, stderr=subprocess.STDOUT)
    log(f'all done in {(time.time() - t0) / 60:.0f} min')


if __name__ == '__main__':
    main()
