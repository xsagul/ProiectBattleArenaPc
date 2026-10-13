// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_alloccommon.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e96190 _free_seg_map
// match: e961d0 _vp9_alloc_context_buffers
// match: e963f0 _vp9_alloc_loop_filter
// match: e96450 _vp9_free_context_buffers
// match: e964d0 _vp9_free_ref_frame_buffers
// match: e96530 _vp9_init_context_buffers
// match: e96570 _vp9_remove_common
// match: e965b0 _vp9_set_mb_mi
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_alloccommon.c"
