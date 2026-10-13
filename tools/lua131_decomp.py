"""Decompile every Lua script of the 1.0.0.131 client (Desktop/probe_istorice_lol/client 1.31: 32-bit Lua 5.1
.luaobj, BuildingBlocks tables) to Lua source with unluac -> data/lua131/decomp/<dir>/<name>.lua

    python tools/lua131_decomp.py [workers]
"""
import concurrent.futures as cf
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.expanduser('~'), 'Desktop', 'probe_istorice_lol', 'client 1.31')
OUT = os.path.join(ROOT, 'data', 'lua131', 'decomp')
JAVA = os.path.join(ROOT, 'toolchain', 'jdk-21.0.12.1+1-jre', 'bin', 'java.exe')
UNLUAC = os.path.join(ROOT, 'tools', 'bin', 'unluac.jar')


def one(p):
    rel = os.path.relpath(p, SRC)
    dst = os.path.join(OUT, os.path.splitext(rel)[0] + '.lua')
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = subprocess.run([JAVA, '-jar', UNLUAC, p], capture_output=True)
    open(dst, 'wb').write(r.stdout if r.returncode == 0 else b'-- unluac failed: ' + r.stderr[:500])
    return 1 if r.returncode == 0 else -1


def main():
    files = [os.path.join(d, f) for d, _, fs in os.walk(SRC) for f in fs if f.lower().endswith('.luaobj')]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    with cf.ThreadPoolExecutor(n) as ex:
        res = list(ex.map(one, files))
    print(len(files), 'scripts;', res.count(1), 'decompiled now,', res.count(-1), 'failed ->', OUT)


if __name__ == '__main__':
    main()
