// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_aq_variance.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e95d60 _aq_variance
// match: ebbea0 _block_variance
// match: ebc030 _vp9_block_energy
// match: ebc0d0 _vp9_get_sub_block_energy
// match: ebc290 _vp9_log_block_var
// match: ebc2e0 _vp9_vaq_frame_setup
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_aq_variance.c"
