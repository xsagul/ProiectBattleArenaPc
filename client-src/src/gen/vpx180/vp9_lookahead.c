// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_lookahead.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e9ea10 _vp9_lookahead_depth
// match: e9ea20 _vp9_lookahead_destroy
// match: e9ea80 _vp9_lookahead_init
// match: e9eb60 _vp9_lookahead_peek
// match: e9ebc0 _vp9_lookahead_pop
// match: e9ec10 _vp9_lookahead_push
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_lookahead.c"
