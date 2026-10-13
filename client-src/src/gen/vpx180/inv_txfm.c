// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): inv_txfm.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f12c90 _iadst16_c
// match: f133f0 _iadst8_c
// match: f13670 _idct16_c
// match: f13b90 _idct32_c
// match: f14a80 _idct4_c
// match: f14b20 _idct8_c
// match: f16170 _vpx_iwht4x4_1_add_c
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/inv_txfm.c"
