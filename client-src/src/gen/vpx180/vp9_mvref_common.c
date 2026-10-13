// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_mvref_common.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ea56a0 _lower_mv_precision
// match: f33120 _find_mv_refs_idx
// match: f33730 _vp9_append_sub8x8_mvs_for_idx
// match: f33870 _vp9_find_best_ref_mvs
// match: f339a0 _vp9_find_mv_refs
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_mvref_common.c"
