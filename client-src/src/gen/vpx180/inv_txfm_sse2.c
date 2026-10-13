// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): inv_txfm_sse2.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f16340 _iadst16_sse2
// match: f16370 _iadst4_sse2
// match: f16470 _iadst8_sse2
// match: f17080 _idct16_sse2
// match: f170b0 _idct16x16_10_pass1
// match: f17470 _idct16x16_10_pass2
// match: f17870 _idct32_1024_8x32
// match: f17aa0 _idct32_1024_8x32_quarter_1
// match: f17c60 _idct32_1024_8x32_quarter_3_4
// match: f17fe0 _idct32_34_8x32_quarter_1
// match: f18110 _idct32_34_8x32_sse2
// match: f18980 _idct4_sse2
// match: f18a30 _idct8
// match: f18be0 _idct8x8_12_add_kernel_sse2
// match: f18e50 _vpx_iadst16_8col_sse2
// match: f1bfe0 _vpx_idct8_sse2
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/x86/inv_txfm_sse2.c"
