"""A portable MSVC toolset from Microsoft's own Visual Studio packages, without installing Visual Studio: the packages
of one release channel's manifest are .vsix (zip) files whose Contents/ go into toolchain/<out>/.

The 13.3 client's own code and its final link were made with MSVC 14.32 build 31328 (Rich header of
game/League of Legends.exe: C / C++ objects and linker, export and resource tools at build 31328; no LTCG entries).
That is the toolset of Visual Studio 2022 17.2.0 exactly (Tools package 14.32.31328); later 17.2.x servicing releases
carry newer builds (17.2.23 has 31342), so the default channel is the fixed 17.2.0 one, taken from Microsoft's
fixed-version bootstrapper for 17.2.0 (vs_setup_bootstrapper.json: installChannelUri).

  get_msvc.py [channel url] [out dir name] [package id,package id,...]

Older toolsets that prebuilt libraries inside the client were made with come from the same manifest, e.g. the
VS2017 one:  get_msvc.py https://aka.ms/vs/17/release/154549238_-178854694/channel msvc-14.16.27048
  Microsoft.VisualC.14.16.Tools.HostX86.TargetX86,Microsoft.VisualC.14.16.Tools.HostX86.TargetX86.Resources,Microsoft.VisualC.14.16.CRT.Headers
"""
import hashlib
import io
import json
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CHANNEL = sys.argv[1] if len(sys.argv) > 1 else 'https://aka.ms/vs/17/release/154549238_-178854694/channel'
OUT = os.path.join(ROOT, 'toolchain', sys.argv[2] if len(sys.argv) > 2 else 'msvc-14.32.31328')
WANT = [
    'Microsoft.VC.14.32.17.2.Tools.HostX64.TargetX86.base',
    'Microsoft.VC.14.32.17.2.Tools.HostX64.TargetX86.Res.base',
    'Microsoft.VC.14.32.17.2.CRT.Headers.base',
    'Microsoft.VC.14.32.17.2.CRT.x86.Desktop.base',
    'Microsoft.VC.14.32.17.2.CRT.x86.Store.base',
    'Microsoft.VC.14.32.17.2.CRT.Source.base',
]


if len(sys.argv) > 3:
    WANT = sys.argv[3].split(',')


def get(url):
    return urllib.request.urlopen(url).read()


def main():
    ch = json.loads(get(CHANNEL).decode('utf-8-sig'))
    vsman = [p['url'] for it in ch['channelItems'] if it.get('id') == 'Microsoft.VisualStudio.Manifests.VisualStudio'
             for p in it['payloads']][0]
    man = json.loads(get(vsman).decode('utf-8-sig'))
    pk = {}
    for p in man['packages']:
        if p['id'] in WANT and p.get('language') in (None, 'neutral', 'en-US'):
            pk.setdefault(p['id'], p)
    os.makedirs(OUT, exist_ok=True)
    for pid in WANT:
        p = pk.get(pid)
        if not p:
            print('not in this channel:', pid)
            continue
        for pay in p.get('payloads', []):
            data = get(pay['url'])
            if pay.get('sha256') and hashlib.sha256(data).hexdigest().lower() != pay['sha256'].lower():
                raise SystemExit(f'checksum mismatch: {pay["fileName"]}')
            z = zipfile.ZipFile(io.BytesIO(data))
            n = 0
            for name in z.namelist():
                if name.startswith('Contents/'):
                    dst = os.path.join(OUT, name[len('Contents/'):].replace('%20', ' '))
                    if name.endswith('/'):
                        continue
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    open(dst, 'wb').write(z.read(name))
                    n += 1
            print(f'{pid} {p["version"]}: {pay["fileName"]} {len(data) // 1024} KiB, {n} files (sha256 checked)')
    print('->', OUT)


if __name__ == '__main__':
    main()
