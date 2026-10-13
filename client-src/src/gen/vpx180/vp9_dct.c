// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_dct.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: edd080 _fadst16
// match: edd6c0 _fadst4
// match: edd790 _fadst8
// match: edd9f0 _fdct16
// match: edde10 _fdct4
// match: eddea0 _fdct8
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_dct.c"
