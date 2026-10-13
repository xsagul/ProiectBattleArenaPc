// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): bitwriter_buffer.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f28880 _vpx_wb_bytes_written
// match: f288a0 _vpx_wb_write_bit
// match: f28910 _vpx_wb_write_literal
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/bitwriter_buffer.c"
