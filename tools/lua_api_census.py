"""Which engine functions Riot's Lua scripts need: every global a script reads (GETGLOBAL) that no script of its
closure defines (SETGLOBAL), the closure being the script and what it loads (DoLuaShared / DoLuaLevel "Name").

    python tools/lua_api_census.py                  -> data/lua133/api_census.txt (all 169 scripts)
    python tools/lua_api_census.py Leashy [..]      the API one script (and what it loads) needs

The listings (data/lua133/listing/*.txt, luac -l -l of the 13.3 client's .luabin64) are the input; the engine's side
is server/core/luaapi.py, and the census says which of its functions exist ('ok') or not yet ('MISSING').
"""
import collections
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, 'data', 'lua133', 'listing')
OUT = os.path.join(ROOT, 'data', 'lua133', 'api_census.txt')
sys.path.insert(0, os.path.join(ROOT, 'server'))

GET = re.compile(r'GETGLOBAL\s+\d+ -?\d+\s+; (\w+)')
SET = re.compile(r'SETGLOBAL\s+\d+ -?\d+\s+; (\w+)')
LOADS = re.compile(r'GETGLOBAL\s+\d+ -?\d+\s+; (DoLuaShared|DoLuaLevel)\s*\n.*?LOADK\s+\d+ -?\d+\s+; "(\w+)"')
# Lua's own library: not the engine's
LUA_LIB = set('assert collectgarbage dofile error getfenv getmetatable ipairs load loadfile loadstring next pairs pcall print '
              'rawequal rawget rawset select setfenv setmetatable tonumber tostring type unpack xpcall _G _VERSION coroutine '
              'debug io math os package string table module require gcinfo newproxy'.split())


def scripts():
    """short name -> listing path (the last part of the file name: DATA__Scripts__Leashy -> Leashy)"""
    out = {}
    for p in sorted(glob.glob(os.path.join(LIST, '*.txt'))):
        base = os.path.basename(p)[:-4]
        out.setdefault(base.split('__')[-1], p)
        out[base] = p
    return out


def read(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    return set(GET.findall(text)), set(SET.findall(text)), [m[1] for m in LOADS.findall(text)]


def closure(name, table, seen=None):
    seen = set() if seen is None else seen
    if name in seen or name not in table:
        return seen
    seen.add(name)
    for dep in read(table[name])[2]:
        closure(dep, table, seen)
    return seen


def needs(name, table):
    got, made = set(), set()
    for n in closure(name, table):
        g, s, _ = read(table[n])
        got |= g
        made |= s
    return sorted(x for x in got - made - LUA_LIB)


def engine():
    try:
        from core import luaapi
        return set(luaapi.FUNCTIONS) | set(luaapi.CONSTANTS)
    except Exception:
        return set()


def main():
    table = scripts()
    have = engine()
    names = sys.argv[1:]
    if names:
        for n in names:
            need = needs(n, table)
            miss = [x for x in need if x not in have]
            print(f'{n}: loads {sorted(closure(n, table) - {n})}; {len(need)} engine names, {len(miss)} missing')
            print('  missing:', ' '.join(miss))
        return
    count = collections.Counter()
    per = {}
    for base, p in table.items():
        if '__' not in base:
            continue
        need = needs(base, table)
        per[base] = need
        count.update(need)
    lines = [f'{len(count)} engine names over {len(per)} scripts; {len([x for x in count if x in have])} done', '']
    for n, c in count.most_common():
        lines.append(f'{"ok     " if n in have else "MISSING"} {c:4d}  {n}')
    open(OUT, 'w').write('\n'.join(lines) + '\n')
    print(lines[0], '->', OUT)


if __name__ == '__main__':
    main()
