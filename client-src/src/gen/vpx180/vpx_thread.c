// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vpx_thread.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e96600 _execute
// match: e96630 _init
// match: e96650 _sync
// match: e966a0 _reset
// match: e96790 _launch
// match: e967f0 _end
// match: e96880 _thread_loop@4
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_util/vpx_thread.c"
