// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): yv12config.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e95a60 _vpx_alloc_frame_buffer
// match: e95ac0 _vpx_free_frame_buffer
// match: e95b00 _vpx_realloc_frame_buffer
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_scale/generic/yv12config.c"
