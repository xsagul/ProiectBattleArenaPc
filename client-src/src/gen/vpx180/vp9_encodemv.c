// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_encodemv.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ebe160 _vp9_write_tree
// match: ecd640 _build_nmv_component_cost_table
// match: ecdb40 _encode_mv_component
// match: ecdd10 _inc_mvs
// match: ecdd70 _update_mv
// match: ecdea0 _vp9_build_nmv_cost_table
// match: ecdee0 _vp9_encode_mv
// match: ecdff0 _vp9_entropy_mv_init
// match: ece030 _vp9_update_mv_count
// match: ece160 _vp9_write_nmv_probs
// match: ece300 _vp9_write_token
// match: ece410 _write_mv_update
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_encodemv.c"
