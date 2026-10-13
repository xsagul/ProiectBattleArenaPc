// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_pred_common.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f28e00 _vp9_compound_reference_allowed
// match: f28e30 _vp9_get_pred_context_comp_ref_p
// match: f28ff0 _vp9_get_pred_context_single_ref_p1
// match: f29170 _vp9_get_pred_context_single_ref_p2
// match: f29330 _vp9_get_reference_mode_context
// match: f293d0 _vp9_setup_compound_reference_mode
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_pred_common.c"
