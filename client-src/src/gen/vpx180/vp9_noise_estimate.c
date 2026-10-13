// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_noise_estimate.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: eb5a60 _vp9_noise_estimate_extract_level
// match: eb5aa0 _vp9_noise_estimate_init
// match: eb5b30 _vp9_update_noise_estimate
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/encoder/vp9_noise_estimate.c"
