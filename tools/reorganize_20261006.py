"""One-time reorganization of the project (2026-10-06, the user's decision: the native C++ client is abandoned for the
Riot 13.3 exe; keep only what builds the server or the exact client, centralized).

  game/        the Riot 13.3 client (was Desktop\\lol13.3): unpacked exe, ba_host.dll, DATA
  client-src/  the client as raw source: the exe's memory images, function / handler / import maps, ba_host.c and the
               scripts that build the unpacked exe
  server/      our game server (lnp_server.py and the modules it runs on)
  launcher/    the out-of-game client page (www/) and its local server
  tools/       learning and inspection tools, bin/ (bainfo, luac, unluac), gpu_sponge/, third_party/
  data/        what the server and tools read: exe133/ (packet formats, tables), lua133, lcu133, lcu/13.3, hashes,
               rofl (the 13.3 replay), replays/maknee13_2
  docs/, toolchain/

  reorganize_20261006.py plan      what would move / go to the Recycle Bin / be rewritten
  reorganize_20261006.py run       do it
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OLD_GAME = r'C:\Users\Sorin\Desktop\lol13.3'
NEW_GAME = os.path.join(ROOT, 'game')
J = lambda *p: os.path.join(ROOT, *p)  # noqa: E731

SERVER_MODS = ['bin_tree', 'c2s_codec', 'c2s_emu', 'create_hero', 'decoded', 'exe_dis', 'game_info', 'items133', 'lnp',
               'lnp_server', 'lol_packets', 'name_hashes', 'packet_emu', 'pkt_codec', 'pkt_modes', 'pkt_schema',
               'pkt_tree', 'positions', 'repl_codec', 'replay_window', 'replication', 'rofl_packets', 'spell_calc',
               'spell_effects', 'spell_engine', 'spell_info', 'spell_templates', 'sync552', 'waypoints', 'world']
CLIENT_SRC_CODE = ['build_unpacked.py', 'resolve_imports.py', 'read_stubs.py', 'ba_host.c', 'ba_host_imports.h', 'ba_host.dll']
CLIENT_SRC_DATA = ['exe_image_unpacked.bin', 'exe_image_t900.bin', 'exe_image_match78.bin', 'exe_image.bin',
                   'functions.txt', 'handler_table.txt', 'handler_digest.txt', 'import_table.txt']
GPU = ['d3d11_proxy.c', 'd3d11.def', 'd3d11.dll']

TRASH = [
    # the native C++ client / server / lobby and their data and builds
    'game-data', 'build-clang', 'build-test', 'build-tools', 'client', 'server', 'common', 'cmake', 'CMakeLists.txt',
    'build.ps1', 'scoreboard_scene.bin', 'eog_scene.bin', 'vfx.txt', 'match.basr', 'data-path.txt', 'data-path.12.23.bak',
    'Interceptare 4.20.cmd', 'Joaca BattleArena.cmd', 'Joaca 13.3.cmd', 'Reda replay 13.3.cmd',
    'Porneste 13.3 despachetat.cmd', 'lobby/src', 'lobby/www', 'lobby/CMakeLists.txt', 'lcu-data/14.1',
    'toolchain/cmake-4.4.3-windows-x86_64', 'toolchain/RenderDoc_1.46_64',
    # tools of abandoned directions (14.1 / 12.23 / 4.20 / C++ client visuals / real Riot client login)
    'tools/cdragon_lcu.py', 'tools/disasm_shaders.py', 'tools/fetch_wads.py', 'tools/lol420_decode.py',
    'tools/lol420_proxy.py', 'tools/raf.py', 'tools/replay_facts.py', 'tools/riot_services.py', 'tools/shader_toc.py',
    'tools/verify_lobby.py', 'tools/sponge/shader_index.py', 'tools/sponge/texture_index.py', 'tools/sponge/palette.py',
    'tools/sponge/explain_draw.py', 'tools/sponge/export_replay.py', 'tools/sponge/d3d11.new.dll',
    'tools/sponge/d3d11.prev.dll', 'research/exe133/replay_13.3.barp', 'research/rofl/12.7_Control.rofl',
    'research/rofl/KR-5736537983_12.3.rofl', 'research/replays/lrf_lrs_indexed.zip.txt', 'research/replays/test',
]
RESEARCH_KEEP = {'exe133', 'lua133', 'lcu133', 'clients133', 'hashes', 'rofl', 'replays'}


def plan():
    moves, trash = [], []
    for t in TRASH:
        if os.path.exists(J(t)):
            trash.append(J(t))
    for name in os.listdir(J('research')):
        if name not in RESEARCH_KEEP:
            trash.append(J('research', name))
    for d in os.listdir(J('research', 'exe133')):
        p = J('research', 'exe133', d, 'frames')
        if d.startswith('match_') and os.path.isdir(p):
            trash.append(p)
    # moves (from, to); order matters: the C++ server/ goes to the bin before the new server/ is made
    moves.append((OLD_GAME, NEW_GAME))
    for f in CLIENT_SRC_DATA:
        moves.append((J('research', 'exe133', f), J('client-src', f)))
    for f in CLIENT_SRC_CODE:
        moves.append((J('tools', 'sponge', f), J('client-src', f)))
    for m in SERVER_MODS:
        moves.append((J('tools', 'sponge', m + '.py'), J('server', m + '.py')))
    for f in GPU:
        moves.append((J('tools', 'sponge', f), J('tools', 'gpu_sponge', f)))
    for f in os.listdir(J('tools', 'sponge')):
        src = J('tools', 'sponge', f)
        if f in CLIENT_SRC_CODE or f in GPU or f[:-3] in SERVER_MODS or f == '__pycache__' or os.path.isdir(src):
            continue
        if J('tools', 'sponge', f) in trash:
            continue
        moves.append((src, J('tools', f)))
    moves.append((J('lobby', 'www13'), J('launcher', 'www')))
    moves.append((J('tools', 'lobby_dev_server.py'), J('launcher', 'lobby_server.py')))
    moves.append((J('lcu-data', '13.3'), J('data', 'lcu', '13.3')))
    moves.append((J('third_party'), J('tools', 'third_party')))
    moves.append((J('research'), J('data')))     # last: everything left in research is data
    return moves, trash


# ------------------------------------------------------------------------------------------------- path rewriting
def rewrite_text(path, s):
    rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
    top = rel.split('/')[0]
    o = s
    # the game: absolute paths, every spelling (not lol13.3-clients)
    for old in (r'C:\\\\Users\\\\Sorin\\\\Desktop\\\\lol13\.3', r'C:\\Users\\Sorin\\Desktop\\lol13\.3',
                r'C:/Users/Sorin/Desktop/lol13\.3', r'/c/Users/Sorin/Desktop/lol13\.3'):
        sep = '\\\\' if old.startswith(r'C:\\\\') else ('\\' if old.startswith('C:\\') else '/')
        new = NEW_GAME.replace('\\', sep) if sep != '/' else NEW_GAME.replace('\\', '/')
        if old.startswith('/c/'):
            new = '/c/' + NEW_GAME[3:].replace('\\', '/')
        s = re.sub(old + r'(?![-\w])', lambda m: new, s)
    s = re.sub(r'Desktop\\lol13\.3(?![-\w])', r'ProiectBattleArenaPc\\game', s)
    # files that were two levels deep (tools/sponge) are one level deep now
    if top in ('server', 'tools', 'client-src') and rel.count('/') == 1 and path.endswith(('.py', '.sh', '.ps1', '.js')):
        s = re.sub(r"(os\.path\.join\((?:HERE|here|_HERE|os\.path\.dirname\([^)]*\)\)?)\s*,\s*)'\.\.'\s*,\s*'\.\.'", r"\1'..'", s)
        s = s.replace('"$(dirname "$0")/../.."', '"$(dirname "$0")/.."').replace('$HERE/../..', '$HERE/..')
        s = s.replace('cd "$(dirname "$0")/../.."', 'cd "$(dirname "$0")/.."')
    # exe artifacts -> client-src
    for f in CLIENT_SRC_DATA:
        s = s.replace(f"os.path.join(RES, '{f}')", f"os.path.join(RES, '..', '..', 'client-src', '{f}')")
        s = s.replace(f"os.path.join(OUT, '{f}')", f"os.path.join(OUT, '..', '..', 'client-src', '{f}')")
        s = s.replace(f"os.path.join(P.RES, '{f}')", f"os.path.join(P.RES, '..', '..', 'client-src', '{f}')")
        s = s.replace(f"'research', 'exe133', '{f}'", f"'client-src', '{f}'")
        s = s.replace(f"research/exe133/{f}", f"client-src/{f}")
    # research -> data, lcu-data -> data/lcu, builds -> tools/bin
    s = s.replace("'lcu-data', '13.3'", "'data', 'lcu', '13.3'").replace('lcu-data/13.3', 'data/lcu/13.3')
    s = s.replace("'research', ", "'data', ").replace('research/', 'data/').replace('research\\\\', 'data\\\\')
    s = s.replace("'build-test', 'bin', 'bainfo.exe'", "'tools', 'bin', 'bainfo.exe'").replace('build-test/bin/bainfo', 'tools/bin/bainfo')
    s = s.replace('build-tools/', 'tools/bin/')
    # moved files named by path
    for m in SERVER_MODS:
        s = s.replace(f'tools/sponge/{m}.py', f'server/{m}.py').replace(f'tools\\sponge\\{m}.py', f'server\\{m}.py')
    for f in CLIENT_SRC_CODE:
        s = s.replace(f'tools/sponge/{f}', f'client-src/{f}')
    for f in GPU:
        s = s.replace(f'tools/sponge/{f}', f'tools/gpu_sponge/{f}')
    s = s.replace('tools/lobby_dev_server.py', 'launcher/lobby_server.py').replace('tools\\lobby_dev_server.py', 'launcher\\lobby_server.py')
    s = s.replace("'lobby', 'www13'", "'launcher', 'www'")
    for m in SERVER_MODS:
        s = s.replace(f"'tools', 'sponge', '{m}.py'", f"'server', '{m}.py'")
    s = s.replace("'tools', 'sponge', ", "'tools', ")
    s = s.replace('lobby/www13', 'launcher/www').replace('tools/sponge/', 'tools/').replace('tools\\sponge\\', 'tools\\')
    # tools (and client-src scripts) find the server's modules
    if top in ('tools', 'client-src') and path.endswith('.py') and 'sys.path.insert(0, HERE)' in s and "'server'" not in s:
        s = s.replace('sys.path.insert(0, HERE)', "sys.path.insert(0, HERE)\nsys.path.insert(0, os.path.join(HERE, '..', 'server'))", 1)
    return s, s != o


def rewrite_all(do):
    exts = ('.py', '.sh', '.ps1', '.cmd', '.js', '.c', '.md', '.json5')
    changed = []
    roots = ['server', 'tools', 'client-src', 'launcher', 'docs'] if do else ['tools', 'lobby', 'docs']
    for r in roots:
        for d, dirs, fs in os.walk(J(r)):
            dirs[:] = [x for x in dirs if x not in ('third_party', '__pycache__', 'bin', 'www')]
            for f in fs:
                if not f.endswith(exts):
                    continue
                p = os.path.join(d, f)
                if f == os.path.basename(__file__):
                    continue
                s = open(p, 'rb').read().decode('utf8', errors='surrogateescape')
                crlf = '\r\n' in s
                new, ch = rewrite_text(p, s.replace('\r\n', '\n'))
                if ch:
                    changed.append(p)
                    if do:
                        open(p, 'wb').write((new.replace('\n', '\r\n') if crlf else new).encode('utf8', errors='surrogateescape'))
    for extra in [J('Joaca 13.3 (client).cmd'), J('README.md'), J('.claude', 'launch.json')]:
        if os.path.exists(extra):
            s = open(extra, encoding='utf8').read()
            new, ch = rewrite_text(J('docs', 'x.md'), s)
            if ch:
                changed.append(extra)
                if do:
                    open(extra, 'w', encoding='utf8').write(new)
    return changed


def recycle(paths):
    ps = ['Add-Type -AssemblyName Microsoft.VisualBasic',
          '$fs=[Microsoft.VisualBasic.FileIO.FileSystem]',
          '$ui=[Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs',
          '$bin=[Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin']
    for p in paths:
        q = p.replace("'", "''")
        ps.append(f"if (Test-Path -LiteralPath '{q}' -PathType Container) {{ $fs::DeleteDirectory('{q}',$ui,$bin) }} "
                  f"elseif (Test-Path -LiteralPath '{q}') {{ $fs::DeleteFile('{q}',$ui,$bin) }}")
    script = os.path.join(os.environ.get('TEMP', '.'), 'ba_recycle.ps1')
    open(script, 'w', encoding='utf-8-sig').write('\n'.join(ps))
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script], check=True)


def size(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    moves, trash = plan()
    if mode == 'plan':
        print('to the Recycle Bin:')
        tot = 0
        for p in trash:
            n = size(p)
            tot += n
            print(f'  {n / 1e6:9.1f} MB  {os.path.relpath(p, ROOT)}')
        print(f'  total {tot / 1e9:.2f} GB')
        print('moves:')
        for a, b in moves:
            print(f'  {a if a.startswith(OLD_GAME) else os.path.relpath(a, ROOT)}  ->  {os.path.relpath(b, ROOT)}')
        ch = rewrite_all(False)
        print(f'files whose paths would be rewritten (before the moves): {len(ch)}')
        return
    recycle(trash)
    for a, b in moves:
        if not os.path.exists(a):
            print('missing, skipped:', a)
            continue
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if os.path.exists(b) and os.path.isdir(b) and os.path.isdir(a):
            for x in os.listdir(a):       # research -> data where data/ already holds lcu/
                shutil.move(os.path.join(a, x), os.path.join(b, x))
            os.rmdir(a)
        else:
            shutil.move(a, b)
    for empty in ('tools/sponge', 'lobby', 'lcu-data'):
        p = J(empty)
        if os.path.isdir(p):
            left = [x for x in os.listdir(p) if x != '__pycache__']
            if not left:
                shutil.rmtree(p)
            else:
                print('not empty, kept:', empty, left)
    ch = rewrite_all(True)
    print('paths rewritten in', len(ch), 'files')


if __name__ == '__main__':
    main()
