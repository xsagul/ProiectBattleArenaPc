// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_aq_complexity.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ebbb80 _vp9_caq_select_segment
// match: ebbd20 _vp9_setup_in_frame_q_adj
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_aq_complexity.c"
