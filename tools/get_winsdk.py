"""Headers and libraries of one Windows SDK from Microsoft's own packages, unpacked into toolchain/ without installing
anything on the system: the SDK is a package of the Visual Studio release manifest (the same fixed 17.2.0 channel as
get_msvc.py); each part is an .msi plus the .cab files it names, unpacked with "msiexec /a" (an administrative image:
files only, no registration).

Which SDK Riot built 13.3 with is measured, not assumed: the client carries the static C runtime (ucrt) and its objects
say compiler build 27412 (Rich header); `check` prints the build inside an unpacked SDK's libucrt.lib.

  get_winsdk.py list                         SDK packages of the channel
  get_winsdk.py get <version> [part ...]     parts: ucrt (default), headers, libs      e.g. get 10.0.18362
  get_winsdk.py check <version>              compiler build of the objects in ucrt/x86/libucrt.lib
"""
import collections
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CHANNEL = 'https://aka.ms/vs/17/release/154549238_-178854694/channel'
PARTS = {
    'ucrt': ['Universal CRT Headers Libraries and Sources-x86_en-us.msi'],
    'headers': ['Windows SDK Desktop Headers x86-x86_en-us.msi', 'Windows SDK for Windows Store Apps Headers-x86_en-us.msi'],
    'libs': ['Windows SDK Desktop Libs x86-x86_en-us.msi', 'Windows SDK for Windows Store Apps Libs-x86_en-us.msi'],
}


def get(url):
    return urllib.request.urlopen(url, timeout=300).read()


def manifest():
    ch = json.loads(get(CHANNEL).decode('utf-8-sig'))
    vsman = [p['url'] for it in ch['channelItems'] if it.get('id') == 'Microsoft.VisualStudio.Manifests.VisualStudio'
             for p in it['payloads']][0]
    return json.loads(get(vsman).decode('utf-8-sig'))


def sdk_packages(man):
    return {p['id'].split('_', 1)[1]: p for p in man['packages'] if re.match(r'Win1[01]SDK_10\.', p['id'])}


def out_dir(version):
    return os.path.abspath(os.path.join(ROOT, 'toolchain', 'winsdk-' + version))


def fetch(pay, folder):
    dst = os.path.join(folder, os.path.basename(pay['fileName'].replace('\\', '/')))
    if not os.path.exists(dst):
        data = get(pay['url'])
        if pay.get('sha256') and hashlib.sha256(data).hexdigest().lower() != pay['sha256'].lower():
            raise SystemExit(f'checksum mismatch: {pay["fileName"]}')
        open(dst, 'wb').write(data)
    return dst


def cmd_get(version, parts):
    pkg = sdk_packages(manifest()).get(version)
    if not pkg:
        raise SystemExit(f'no SDK {version} in this channel')
    pays = {os.path.basename(p['fileName'].replace('\\', '/')).lower(): p for p in pkg['payloads']}
    out = out_dir(version)
    down = os.path.join(out, '_packages')
    os.makedirs(down, exist_ok=True)
    for part in parts:
        for name in PARTS[part]:
            msi = fetch(pays[name.lower()], down)
            # the cabinets an msi needs are named in its string pool
            cabs = sorted(set(m.decode() for m in re.findall(rb'[0-9a-f]{32}\.cab', open(msi, 'rb').read())))
            size = 0
            for cab in cabs:
                size += os.path.getsize(fetch(pays[cab], down))
            r = subprocess.run(['msiexec', '/a', msi, '/qn', 'TARGETDIR=' + out])
            print(f'{name}: {len(cabs)} cabinets, {size // 1048576} MiB (sha256 checked), msiexec /a -> {r.returncode}')
    print('->', out)


def lib_members(path):
    d = open(path, 'rb').read()
    i = 8
    while i < len(d):
        size = int(d[i + 48:i + 58])
        yield d[i:i + 16], d[i + 60:i + 60 + size]
        i += 60 + size + (size & 1)


def comp_id(obj):
    """(tool id, compiler build) an object file was made with, from its @comp.id symbol."""
    if len(obj) < 20:
        return None
    machine, nsec, _, symptr, nsym = struct.unpack_from('<HHIII', obj, 0)
    width = 18
    if machine == 0 and nsec == 0xffff:
        if struct.unpack_from('<H', obj, 4)[0] < 2:
            return None                                         # an import member
        symptr, nsym = struct.unpack_from('<II', obj, 48)       # /bigobj
        width = 20
    if not symptr or symptr + width * nsym > len(obj):
        return None
    for k in range(nsym):
        s = obj[symptr + width * k:symptr + width * k + width]
        if s[:8] == b'@comp.id':
            v = struct.unpack_from('<I', s, 8)[0]
            return v >> 16, v & 0xffff
    return None


def cmd_check(version):
    hits = []
    for base, _, files in os.walk(out_dir(version)):
        if 'libucrt.lib' in files and base.replace('\\', '/').lower().endswith('ucrt/x86'):
            hits.append(os.path.join(base, 'libucrt.lib'))
    if not hits:
        raise SystemExit('no ucrt/x86/libucrt.lib under ' + out_dir(version))
    c = collections.Counter(comp_id(b) for n, b in lib_members(hits[0]) if n[:2] not in (b'/ ', b'//'))
    print(hits[0])
    for (tool, build), n in sorted((k, v) for k, v in c.items() if k):
        print(f'  tool id {tool} build {build}: {n} objects')


def main():
    if len(sys.argv) > 2 and sys.argv[1] == 'get':
        cmd_get(sys.argv[2], sys.argv[3:] or ['ucrt'])
    elif len(sys.argv) > 2 and sys.argv[1] == 'check':
        cmd_check(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == 'list':
        for v, p in sorted(sdk_packages(manifest()).items()):
            print(v, p['version'], f'{sum(x["size"] for x in p["payloads"]) // 1048576} MiB in all')
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
