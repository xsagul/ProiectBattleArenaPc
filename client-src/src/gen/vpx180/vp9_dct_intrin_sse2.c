// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_dct_intrin_sse2.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: edefb0 _fadst16_8col
// match: ee0760 _fadst4_sse2
// match: ee08a0 _fadst8_sse2
// match: ee0e30 _fdct16_8col
// match: ee17e0 _fdct4_sse2
// match: ee1890 _fdct8_sse2
// match: ee1b70 _load_buffer_16x16
// match: ee1bd0 _load_buffer_4x4
// match: ee1c40 _load_buffer_8x8
// match: ee1cf0 _right_shift_8x8
// match: ee1e90 _transpose_16bit_16x16
// match: ee2c00 _write_buffer_16x16
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/x86/vp9_dct_intrin_sse2.c"
