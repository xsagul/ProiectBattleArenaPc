"""Public sources of the third-party libraries inside the 13.3 client, from their official release archives, unpacked
into tools/third_party/<name>-<version>. Versions are the ones the client's own strings name (OpenSSL 1.1.1m, libcurl
7.78.0 build path, zlib 1.2.11, libVorbis 20180316 = 1.3.6, VP9 v1.8.0, libyaml 0.2.3) or its code holds (FreeType 2.10.1: the version
numbers FT_New_Library stores, rva 0xbb7993); zstd and libogg leave no version
behind, so several are fetched and compared (tools/match_objs.py).

  get_libsrc.py [name ...]      default: all
"""
import io
import os
import sys
import tarfile
import urllib.request
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DEST = os.path.join(ROOT, 'tools', 'third_party')

GH = 'https://github.com'
SOURCES = {
    'zlib-1.2.11': f'{GH}/madler/zlib/archive/refs/tags/v1.2.11.tar.gz',
    'curl-7.78.0': f'{GH}/curl/curl/releases/download/curl-7_78_0/curl-7.78.0.tar.gz',
    'openssl-1.1.1m': f'{GH}/openssl/openssl/archive/refs/tags/OpenSSL_1_1_1m.tar.gz',
    'libvorbis-1.3.6': f'{GH}/xiph/vorbis/archive/refs/tags/v1.3.6.tar.gz',
    'libogg-1.3.3': f'{GH}/xiph/ogg/archive/refs/tags/v1.3.3.tar.gz',
    'libogg-1.3.4': f'{GH}/xiph/ogg/archive/refs/tags/v1.3.4.tar.gz',
    'libvpx-1.8.0': f'{GH}/webmproject/libvpx/archive/refs/tags/v1.8.0.tar.gz',
    'libyaml-0.2.3': f'{GH}/yaml/libyaml/archive/refs/tags/0.2.3.tar.gz',
    'zstd-1.4.0': f'{GH}/facebook/zstd/archive/refs/tags/v1.4.0.tar.gz',
    'zstd-1.4.4': f'{GH}/facebook/zstd/archive/refs/tags/v1.4.4.tar.gz',
    'zstd-1.4.5': f'{GH}/facebook/zstd/archive/refs/tags/v1.4.5.tar.gz',
    'zstd-1.4.8': f'{GH}/facebook/zstd/archive/refs/tags/v1.4.8.tar.gz',
    'zstd-1.4.9': f'{GH}/facebook/zstd/archive/refs/tags/v1.4.9.tar.gz',
    'zstd-1.5.0': f'{GH}/facebook/zstd/archive/refs/tags/v1.5.0.tar.gz',
    'zstd-1.5.2': f'{GH}/facebook/zstd/archive/refs/tags/v1.5.2.tar.gz',
    'freetype-2.10.1': f'{GH}/freetype/freetype/archive/refs/tags/VER-2-10-1.tar.gz',
    # LodePNG has no release tags: the one commit whose LODEPNG_VERSION_STRING is the client's "20180611"
    # the release archive carries the submodules too (external/crashpad with mini_chromium); the client's own
    # user-agent string names the version: "sentry.native/0.4.17"
    'sentry-native-0.4.17': f'{GH}/getsentry/sentry-native/releases/download/0.4.17/sentry-native.zip',
    'lodepng-20180611': f'{GH}/lvandeve/lodepng/archive/9426bf43031a3b0c37bc0c19b97448f316f5cf7e.tar.gz',
}


def fetch(name):
    out = os.path.join(DEST, name)
    if os.path.isdir(out):
        print(f'{name}: already there')
        return
    url = SOURCES[name]
    data = urllib.request.urlopen(url, timeout=300).read()
    print(f'{name}: {len(data) // 1024} KiB from {url}')
    tmp = out + '.tmp'
    os.makedirs(tmp, exist_ok=True)
    if url.endswith('.zip'):
        zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
    else:
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            t.extractall(tmp)
    inner = os.listdir(tmp)
    os.rename(os.path.join(tmp, inner[0]) if len(inner) == 1 else tmp, out)
    if os.path.isdir(tmp):
        os.rmdir(tmp)


def main():
    os.makedirs(DEST, exist_ok=True)
    for name in sys.argv[1:] or list(SOURCES):
        fetch(name)


if __name__ == '__main__':
    main()
