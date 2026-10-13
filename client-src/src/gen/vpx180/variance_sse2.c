// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): variance_sse2.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f0e8b0 _variance16_sse2
// match: f0e940 _variance32_sse2
// match: f0ea20 _variance4_sse2
// match: f0eab0 _variance64_sse2
// match: f0ec50 _variance8_sse2
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/x86/variance_sse2.c"
