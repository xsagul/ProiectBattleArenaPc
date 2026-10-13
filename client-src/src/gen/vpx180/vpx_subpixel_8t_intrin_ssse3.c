// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vpx_subpixel_8t_intrin_ssse3.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ee6b60 _shuffle_filter_ssse3
// match: ef03e0 _scaledconvolve_horiz_w4
// match: ef05e0 _scaledconvolve_horiz_w8
// match: ef07f0 _scaledconvolve_vert_w16
// match: ef0a10 _shuffle_filter_convolve8_8_ssse3
// match: ef0a90 _transpose8x8_to_dst
// match: ef1060 _vpx_convolve8_horiz_ssse3
// match: ef15e0 _vpx_filter_block1d16_h4_ssse3
// match: ef16a0 _vpx_filter_block1d16_v4_ssse3
// match: ef1850 _vpx_filter_block1d4_v4_ssse3
// match: ef1950 _vpx_filter_block1d8_h4_ssse3
// match: ef19f0 _vpx_filter_block1d8_v4_ssse3
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/x86/vpx_subpixel_8t_intrin_ssse3.c"
