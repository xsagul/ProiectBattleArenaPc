// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_quantize.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: e933c0 _vp9_frame_init_quantizer
// match: e933e0 _vp9_init_plane_quantizers
// match: e93620 _vp9_init_quantizer
// match: e93de0 _vp9_qindex_to_quantizer
// match: e93e10 _vp9_quantize_fp_32x32_c
// match: e94010 _vp9_regular_quantize_b_4x4
// match: e940b0 _vp9_set_quantizer
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_quantize.c"
