// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vpx_convolve.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: eee8b0 _convolve_horiz
// match: eee9b0 _convolve_vert
// match: eeee20 _vpx_convolve8_c
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/vpx_convolve.c"
