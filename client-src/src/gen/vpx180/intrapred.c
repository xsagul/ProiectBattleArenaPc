// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): intrapred.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ef35d0 _d117_predictor
// match: ef39f0 _d135_predictor
// match: ef3b10 _d153_predictor
// match: ef3d90 _d207_predictor
// match: ef3eb0 _d45_predictor
// match: ef4070 _d63_predictor
// match: ef4190 _dc_left_predictor
// match: ef42a0 _dc_predictor
// match: ef4430 _dc_top_predictor
// match: ef4540 _tm_predictor
#include "../../../../tools/third_party/libvpx-1.8.0/vpx_dsp/intrapred.c"
