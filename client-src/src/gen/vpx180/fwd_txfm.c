// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): fwd_txfm.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ef5310 _vpx_fdct16x16_c
// match: ef5b70 _vpx_fdct32
// match: ef6f50 _vpx_fdct4x4_c
// match: ef7140 _vpx_fdct8x8_c
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/fwd_txfm.c"
