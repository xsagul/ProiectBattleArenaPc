// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_frame_scale_ssse3.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ee4e70 _convolve8_8_even_offset_ssse3
// match: ee4ed0 _convolve8_8_odd_offset_ssse3
// match: ee4f40 _scale_1_to_2_phase_0_row
// match: ee4fe0 _scale_plane_1_to_2_phase_0
// match: ee53e0 _scale_plane_2_to_1_bilinear
// match: ee54c0 _scale_plane_2_to_1_general
// match: ee5a70 _scale_plane_2_to_1_phase_0
// match: ee5ae0 _scale_plane_4_to_1_bilinear
// match: ee5ca0 _scale_plane_4_to_1_general
// match: ee6090 _scale_plane_4_to_1_phase_0
// match: ee6110 _scale_plane_4_to_3_general
// match: ee6b00 _shuffle_filter_odd_ssse3
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/x86/vp9_frame_scale_ssse3.c"
