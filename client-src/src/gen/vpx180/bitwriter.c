// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): bitwriter.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: f29420 _vpx_start_encode
// match: f29460 _vpx_stop_encode
// match: f29530 _vpx_write_bit
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/bitwriter.c"
