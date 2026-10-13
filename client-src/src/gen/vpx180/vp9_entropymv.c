// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_entropymv.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e96ce0 _inc_mv_component
// match: e96dc0 _vp9_adapt_mv_probs
// match: e97580 _vp9_get_mv_class
// match: e975d0 _vp9_inc_mv
// match: e97650 _vp9_init_mv_probs
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_entropymv.c"
