// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_ethread.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f2c050 _accumulate_rd_opt
// match: f2c190 _create_enc_workers
// match: f2c440 _enc_row_mt_worker_hook
// match: f2c4d0 _enc_worker_hook
// match: f2c530 _launch_enc_workers
// match: f2c600 _vp9_encode_tiles_mt
// match: f2c800 _vp9_encode_tiles_row_mt
// match: f2ca60 _vp9_row_mt_sync_mem_alloc
// match: f2cb40 _vp9_row_mt_sync_mem_dealloc
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_ethread.c"
