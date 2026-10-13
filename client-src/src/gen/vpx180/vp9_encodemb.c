// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_encodemb.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f2a0d0 _encode_block
// match: f2a4b0 _vp9_encode_block_intra
// match: f2ab00 _vp9_encode_intra_block_plane
// match: f2abf0 _vp9_encode_sb
// match: f2ad30 _vp9_optimize_b
// match: f2ba40 _vp9_subtract_plane
// match: f2bab0 _vp9_xform_quant
// match: f2bcd0 _vp9_xform_quant_dc
// match: f2be70 _vp9_xform_quant_fp
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_encodemb.c"
