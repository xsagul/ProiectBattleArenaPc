// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vpx_subpixel_8t_intrin_avx2.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ef2070 _vpx_convolve8_avg_vert_avx2
// match: ef23c0 _vpx_convolve8_horiz_avx2
// match: ef2580 _vpx_convolve8_vert_avx2
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/x86/vpx_subpixel_8t_intrin_avx2.c"
