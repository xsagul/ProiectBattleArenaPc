// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_loopfilter.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e98dc0 _build_masks
// match: e98fd0 _build_y_mask
// match: e99140 _filter_selectively_horiz
// match: e993c0 _filter_selectively_vert_row2
// match: e995e0 _loop_filter_rows
// match: e99760 _update_sharpness
// match: e997f0 _vp9_adjust_mask
// match: e99eb0 _vp9_build_mask_frame
// match: e99fa0 _vp9_filter_block_plane_non420
// match: e9a630 _vp9_filter_block_plane_ss00
// match: e9a830 _vp9_filter_block_plane_ss11
// match: e9aa70 _vp9_loop_filter_data_reset
// match: e9aac0 _vp9_loop_filter_frame
// match: e9ab20 _vp9_loop_filter_frame_init
// match: e9ac90 _vp9_loop_filter_init
// match: e9acf0 _vp9_setup_mask
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_loopfilter.c"
