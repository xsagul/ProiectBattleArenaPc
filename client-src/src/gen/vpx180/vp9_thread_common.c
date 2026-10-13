// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_thread_common.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e9c340 _thread_loop_filter_rows
// match: e9c600 _vp9_accumulate_frame_counts
// match: e9ccd0 _vp9_loop_filter_alloc
// match: e9cf00 _vp9_loop_filter_dealloc
// match: e9cfd0 _vp9_loop_filter_frame_mt
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_thread_common.c"
