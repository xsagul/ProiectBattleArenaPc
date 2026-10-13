// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_idct_intrin_sse2.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ee3e60 _load_buffer_8x16
// match: ee43d0 _write_buffer_8x16
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/x86/vp9_idct_intrin_sse2.c"
