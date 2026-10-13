// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): psnr.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e95de0 _get_sse
// match: e95f50 _vpx_calc_psnr
// match: e96160 _vpx_get_y_sse
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/psnr.c"
