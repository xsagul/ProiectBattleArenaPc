// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_blockd.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f28990 _vp9_above_block_mode
// match: f289d0 _vp9_foreach_transformed_block
// match: f28b10 _vp9_foreach_transformed_block_in_plane
// match: f28c30 _vp9_left_block_mode
// match: f28c70 _vp9_set_contexts
// match: f28dd0 _vp9_setup_block_planes
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_blockd.c"
