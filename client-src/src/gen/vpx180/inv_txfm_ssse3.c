// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): inv_txfm_ssse3.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f183d0 _idct32_8x32_quarter_2_stage_4_to_6
// match: f185a0 _idct32_8x32_quarter_3_4_stage_4_to_7
// match: f18dd0 _load_transpose_16bit_8x8
// match: f1c200 _write_buffer_8x8
// match: f1c380 _idct32_135_8x32_quarter_1
// match: f1c4f0 _idct32_135_8x32_quarter_1_2
// match: f1c670 _idct32_135_8x32_quarter_3_4
// match: f1c9a0 _idct32_135_8x32_ssse3
// match: f1ca40 _idct32_34_8x32_quarter_1_2
// match: f1cc50 _idct32_34_8x32_ssse3
// match: f1ce40 _idct8x8_12_add_kernel_ssse3
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/x86/inv_txfm_ssse3.c"
