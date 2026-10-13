// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): variance.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ee9380 _vpx_comp_avg_pred_c
// match: eeddb0 _vpx_variance16x16_c
// match: eede60 _vpx_variance16x32_c
// match: eedf10 _vpx_variance16x8_c
// match: eedfc0 _vpx_variance32x16_c
// match: eee070 _vpx_variance32x32_c
// match: eee120 _vpx_variance32x64_c
// match: eee1d0 _vpx_variance4x4_c
// match: eee270 _vpx_variance4x8_c
// match: eee310 _vpx_variance64x32_c
// match: eee3c0 _vpx_variance64x64_c
// match: eee470 _vpx_variance8x16_c
// match: eee580 _vpx_variance8x4_c
// match: eee680 _vpx_variance8x8_c
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/variance.c"
