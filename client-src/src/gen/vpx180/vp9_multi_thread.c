// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_multi_thread.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ece5c0 _vp9_assign_tile_to_thread
// match: ece600 _vp9_enc_grp_get_next_job
// match: ece640 _vp9_get_tiles_proc_status
// match: ece6e0 _vp9_multi_thread_tile_init
// match: ece770 _vp9_prepare_job_queue
// match: ece8f0 _vp9_row_mt_alloc_rd_thresh
// match: ece9a0 _vp9_row_mt_mem_alloc
// match: ecec20 _vp9_row_mt_mem_dealloc
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_multi_thread.c"
