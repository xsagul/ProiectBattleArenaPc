// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): loopfilter_sse2.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f1f140 _transpose
// match: f1f300 _transpose8x16
// match: f1f490 _vpx_lpf_horizontal_16_dual_sse2
// match: f20610 _vpx_lpf_horizontal_16_sse2
// match: f20fe0 _vpx_lpf_horizontal_4_dual_sse2
// match: f214e0 _vpx_lpf_horizontal_8_dual_sse2
// match: f21b60 _vpx_lpf_horizontal_8_sse2
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/x86/loopfilter_sse2.c"
