# Live, passive watch of everything the Riot programs move while the user walks through the client:
# network volume per process, remote hosts, local links between the Riot processes, files that appear
# or grow in the Riot folders (typed by their first bytes), and the URLs the clients write in their own logs.
# Needs no elevation and touches no process: psutil counters, the connection table, the DNS cache, files.
# TLS hides contents: what is told apart is WHO talks to WHOM, HOW MUCH, and WHAT LANDS ON DISK.
#
#   python -u tools/live_watch.py [out dir]      -> <out>/events.txt (lines worth a look), <out>/detail.log (all)
import os, re, sys, time, subprocess, collections
import psutil

TICK, WINDOW = 2.0, 10.0
NET_ALERT = 2 << 20            # bytes received by the machine in one window
FILE_ALERT = 512 << 10         # a new / grown file this big is named in the summary
PROC = re.compile(r'(?i)league|riot|vgc|vgtray')
QUIET = re.compile(r'(?i)^Riot Client\.exe$|UxRender|CrashHandler')
ROOTS = [r'C:\Riot Games', r'C:\ProgramData\Riot Games', os.path.expandvars(r'%LOCALAPPDATA%\Riot Games')]
STRONG = re.compile(rb'(?i)\blua\b|luabin|luaobj|building ?block|spell ?script|scripts\.wad|all_lua_files')
URL = re.compile(rb'https?://[A-Za-z0-9._:-]+(?:/[A-Za-z0-9._~%@+-]*){0,3}')
URL_HOT = re.compile(r'(?i)script|lua|logic|spell|abilit|game-?data|bundle|manifest|patch|release|channels|content')
MAGIC = [(b'\x1bLua', 'LUA BYTECODE'), (b'PreL', 'lua preload'), (b'\x89PNG', 'png'), (b'\xff\xd8\xff', 'jpeg'),
         (b'RIFF', 'riff/webp'), (b'\x1a\x45\xdf\xa3', 'webm'), (b'OggS', 'ogg'), (b'\x28\xb5\x2f\xfd', 'zstd'),
         (b'\x1f\x8b', 'gzip'), (b'RMAN', 'riot manifest'), (b'RW', 'wad'), (b'PROP', 'bin'), (b'PTCH', 'bin patch'),
         (b'SQLite', 'sqlite'), (b'{', 'json'), (b'[', 'json/log'), (b'<', 'html/xml'), (b'MZ', 'exe/dll'), (b'PK', 'zip')]

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join('data', 'live', 'watch_' + time.strftime('%Y%m%d_%H%M%S'))
os.makedirs(out, exist_ok=True)
ev_f = open(os.path.join(out, 'events.txt'), 'a', encoding='utf-8', buffering=1)
de_f = open(os.path.join(out, 'detail.log'), 'a', encoding='utf-8', buffering=1)
now = lambda: time.strftime('%H:%M:%S')
def detail(s): de_f.write(f'{now()} {s}\n')
def event(s):
    ev_f.write(f'{now()} {s}\n'); detail('EVENT ' + s); print(f'{now()} {s}', flush=True)
mb = lambda n: f'{n / 1048576:.1f} MB' if n >= 1048576 else f'{n / 1024:.0f} KB'

def kind(path):
    try:
        with open(path, 'rb') as f: b = f.read(4096)
    except OSError:
        return 'locked', False
    hit = b[:4] == b'\x1bLua' or bool(STRONG.search(b))
    for m, name in MAGIC:
        if b.startswith(m): return name, hit
    return b[:4].hex() or 'empty', hit

def walk():
    snap = {}
    for root in ROOTS:
        for dp, dn, fn in os.walk(root):
            try:
                for e in os.scandir(dp):
                    if e.is_file(follow_symlinks=False):
                        st = e.stat(); snap[e.path] = (st.st_size, st.st_mtime_ns)
            except OSError:
                pass
    return snap

dns, dns_at = {}, 0.0
def names(force=False):
    global dns_at
    if not force and time.time() - dns_at < 6: return
    dns_at = time.time()
    try:
        t = subprocess.run(['powershell', '-NoProfile', '-Command',
                            'Get-DnsClientCache | ForEach-Object { $_.Entry + "|" + $_.Data }'],
                           capture_output=True, text=True, timeout=20).stdout
        for line in t.splitlines():
            n, _, ip = line.partition('|')
            if re.fullmatch(r'[0-9a-fA-F.:]+', ip.strip()): dns.setdefault(ip.strip(), n.strip())
    except Exception as e:
        detail(f'dns cache: {e!r}')

def procs():
    r = {}
    for p in psutil.process_iter(['pid', 'name']):
        if PROC.search(p.info['name'] or ''): r[p.info['pid']] = p.info['name']
    return r
def io(pid):
    try:
        c = psutil.Process(pid).io_counters(); return c.other_bytes, c.read_bytes
    except Exception:
        return None
def nic():
    r = s = 0
    for n, c in psutil.net_io_counters(pernic=True).items():
        if 'loopback' in n.lower(): continue
        r += c.bytes_recv; s += c.bytes_sent
    return r, s

files = walk()
offsets = {p: sz for p, (sz, _) in files.items() if p.lower().endswith(('.log', '.txt', '.json'))}
known = procs(); last_io = {pid: io(pid) for pid in known}
seen_hosts, seen_links, seen_urls = set(), set(), set()
last_nic = nic()
W = dict(recv=0, sent=0, per=collections.Counter(), disk=collections.Counter(), hosts=[], links=[], files=[], urls=0, hot=[], fbytes=0, fcount=0)
win_start = time.time(); ticks = 0
event(f'watch started: {len(files)} files under watch, riot processes now: {sorted(set(known.values())) or "none"}  -> {out}')
names(True)

while True:
    time.sleep(TICK); ticks += 1
    # processes
    cur = procs()
    # window helpers come and go all the time: told once per name, the rest only in the detail log
    for pid in cur.keys() - known.keys():
        (detail if QUIET.search(cur[pid]) and cur[pid] in known.values() else event)(f'PROC start {cur[pid]} ({pid})')
    for pid in known.keys() - cur.keys():
        (detail if QUIET.search(known[pid]) and known[pid] in cur.values() else event)(f'PROC exit  {known[pid]} ({pid})')
    known = cur
    # volume
    n = nic(); W['recv'] += n[0] - last_nic[0]; W['sent'] += n[1] - last_nic[1]; last_nic = n
    for pid, name in cur.items():
        c = io(pid); p = last_io.get(pid)
        if c and p: W['per'][name] += max(0, c[0] - p[0]); W['disk'][name] += max(0, c[1] - p[1])
        last_io[pid] = c
    # connections
    try:
        conns = psutil.net_connections('inet')
    except Exception:
        conns = []
    listen = {c.laddr.port: c.pid for c in conns if c.status == psutil.CONN_LISTEN and c.laddr}
    unknown = False
    for c in conns:
        if c.pid not in cur or not c.raddr: continue
        ip, port = c.raddr.ip, c.raddr.port
        if ip.startswith('127.') or ip == '::1':
            peer = cur.get(listen.get(port)) or (psutil.Process(listen[port]).name() if port in listen and psutil.pid_exists(listen[port]) else None)
            key = (cur[c.pid], peer or f'port {port}')
            if peer and key not in seen_links and key[0] != key[1]:
                seen_links.add(key); W['links'].append(f'{key[0]} -> {key[1]}')
            continue
        key = (cur[c.pid], ip, port)
        if key not in seen_hosts:
            seen_hosts.add(key)
            if ip not in dns: unknown = True
            W['hosts'].append(key)
    if unknown: names()
    # files + logs (every second tick)
    if ticks % 2 == 0:
        snap = walk()
        for p, (sz, mt) in snap.items():
            old = files.get(p)
            if old and old == (sz, mt): continue
            grew = sz - (old[0] if old else 0)
            low = p.lower()
            if low.endswith(('.log', '.txt', '.json')) and 'logs' in low:
                start = offsets.get(p, 0)
                if sz < start: start = 0
                try:
                    with open(p, 'rb') as f:
                        f.seek(start); chunk = f.read(4 << 20)
                    offsets[p] = start + len(chunk)
                except OSError:
                    chunk = b''
                for u in set(URL.findall(chunk)):
                    u = re.sub(r'\d{3,}|[0-9a-f]{8}-[0-9a-f-]{20,}', '#', u.decode('latin-1'))
                    if u not in seen_urls:
                        seen_urls.add(u); W['urls'] += 1; detail(f'URL {os.path.basename(p)} {u}')
                        if URL_HOT.search(u.split('/', 3)[-1] if u.count('/') > 2 else ''): W['hot'].append(u)
                for line in chunk.splitlines():
                    if STRONG.search(line):
                        event(f'LOG MENTIONS SCRIPT ({os.path.basename(p)}): {line[:260].decode("latin-1")}')
                continue
            k, hit = kind(p)
            detail(f'FILE {"new" if not old else "chg"} {k} {sz} ({grew:+d}) {p}')
            if grew > 0: W['fbytes'] += grew; W['fcount'] += 1
            if hit: event(f'!!! LUA / SCRIPT CONTENT IN FILE: {k} {mb(sz)} {p}')
            elif grew >= FILE_ALERT: W['files'].append((grew, k, p))
        for p in files.keys() - snap.keys(): detail(f'FILE gone {p}')
        files = snap
    # window summary
    if time.time() - win_start >= WINDOW:
        win_start = time.time()
        line = f'net in {mb(W["recv"])} out {mb(W["sent"])}'
        top = [f'{n} {mb(b)}' for n, b in W['per'].most_common(3) if b >= 256 << 10]
        # ipc = sockets, pipes, device calls (network AND local links); disk = file reads
        if top: line += ' | ipc ' + ', '.join(top)
        dk = [f'{n} {mb(b)}' for n, b in W['disk'].most_common(2) if b >= 4 << 20]
        if dk: line += ' | disk ' + ', '.join(dk)
        detail('WINDOW ' + line + f' | files +{W["fcount"]} {mb(W["fbytes"])} | new urls {W["urls"]}')
        parts = []
        if W['hosts']:
            names()
            hs = collections.OrderedDict()
            for name, ip, port in W['hosts']: hs.setdefault(f'{dns.get(ip, ip)}:{port}', set()).add(name.replace('.exe', ''))
            for h, who in hs.items(): detail(f'HOST {h} <- {",".join(sorted(who))}')
            parts.append('new hosts: ' + ', '.join(f'{h} ({"/".join(sorted(w))})' for h, w in list(hs.items())[:6]) + (f' +{len(hs) - 6}' if len(hs) > 6 else ''))
        if W['links']: parts.append('local links: ' + ', '.join(W['links'][:6]))
        if W['files']:
            parts.append('files: ' + ', '.join(f'{k} {mb(g)} {os.sep.join(p.split(os.sep)[-3:])}' for g, k, p in sorted(W['files'], reverse=True)[:4]))
        if W['hot']: parts.append('urls: ' + ', '.join(W['hot'][:5]) + (f' +{len(W["hot"]) - 5}' if len(W['hot']) > 5 else ''))
        if parts or (W['recv'] >= NET_ALERT and known):
            event(line + (' | ' + ' | '.join(parts) if parts else '') + (f' | files +{W["fcount"]} {mb(W["fbytes"])}' if W['fcount'] else ''))
        W = dict(recv=0, sent=0, per=collections.Counter(), disk=collections.Counter(), hosts=[], links=[], files=[], urls=0, hot=[], fbytes=0, fcount=0)
