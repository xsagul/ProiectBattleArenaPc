// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_highbd_iht16x16_add_sse4.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ee1f40 _transpose_16bit_8x8
// match: f16270 _butterfly
// match: f16af0 _idct16_8col
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/x86/vp9_highbd_iht16x16_add_sse4.c"
