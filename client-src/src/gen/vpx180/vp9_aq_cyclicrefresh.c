// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_aq_cyclicrefresh.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e9d170 _compute_deltaq
// match: e9d1f0 _cyclic_refresh_update_map
// match: e9d570 _vp9_cyclic_refresh_alloc
// match: e9d600 _vp9_cyclic_refresh_estimate_bits_at_q
// match: e9d730 _vp9_cyclic_refresh_free
// match: e9d760 _vp9_cyclic_refresh_get_rdmult
// match: e9d770 _vp9_cyclic_refresh_limit_q
// match: e9d7a0 _vp9_cyclic_refresh_postencode
// match: e9d9c0 _vp9_cyclic_refresh_rc_bits_per_mb
// match: e9daa0 _vp9_cyclic_refresh_reset_resize
// match: e9db10 _vp9_cyclic_refresh_set_golden_update
// match: e9db80 _vp9_cyclic_refresh_setup
// match: e9de00 _vp9_cyclic_refresh_update_parameters
// match: e9e0c0 _vp9_cyclic_refresh_update_sb_postencode
// match: e9e230 _vp9_cyclic_refresh_update_segment
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_aq_cyclicrefresh.c"
