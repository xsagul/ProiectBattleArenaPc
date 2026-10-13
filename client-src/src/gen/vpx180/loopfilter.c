// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): loopfilter.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f1d850 _filter16
// match: f1dc00 _filter4
// match: f1dda0 _filter8
// match: f1ded0 _flat_mask4
// match: f1df80 _mb_lpf_horizontal_edge_w
// match: f1e2a0 _mb_lpf_vertical_edge_w
// match: f1e550 _vpx_lpf_horizontal_4_c
// match: f1e860 _vpx_lpf_horizontal_8_c
// match: f1ebc0 _vpx_lpf_vertical_4_c
// match: f1ee90 _vpx_lpf_vertical_8_c
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/loopfilter.c"
