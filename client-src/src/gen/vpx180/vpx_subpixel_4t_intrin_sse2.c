// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vpx_subpixel_4t_intrin_sse2.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: eef640 _vpx_convolve8_horiz_sse2
// match: eefbf0 _vpx_filter_block1d16_h4_sse2
// match: eefd10 _vpx_filter_block1d16_v4_sse2
// match: ef0010 _vpx_filter_block1d4_v4_sse2
// match: ef0160 _vpx_filter_block1d8_h4_sse2
// match: ef0220 _vpx_filter_block1d8_v4_sse2
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/x86/vpx_subpixel_4t_intrin_sse2.c"
