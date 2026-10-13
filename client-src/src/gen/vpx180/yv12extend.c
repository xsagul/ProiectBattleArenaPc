// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): yv12extend.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e956e0 _extend_frame
// match: e957b0 _extend_plane
// match: e958a0 _vpx_extend_frame_borders_c
// match: e958c0 _vpx_extend_frame_inner_borders_c
// match: e958e0 _vpx_yv12_copy_frame_c
// match: e959c0 _vpx_yv12_copy_y_c
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_scale/generic/yv12extend.c"
