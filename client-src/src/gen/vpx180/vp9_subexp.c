// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_subexp.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ebe260 _vpx_write
// match: f29710 _remap_prob
// match: f29790 _vp9_cond_prob_diff_update
// match: f299d0 _vp9_prob_diff_update_savings_search
// match: f29ad0 _vp9_prob_diff_update_savings_search_model
// match: f29fb0 _vp9_write_prob_diff_update
// match: f2a090 _vpx_write_literal
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_subexp.c"
