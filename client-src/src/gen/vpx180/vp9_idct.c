// libvpx 1.8.0 (configured for x86-win32-vs15, C files; frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vp9_idct.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvpx-1.8.0 -Itools/third_party/libvpx-1.8.0-build -DNDEBUG -DWIN32 -D_CRT_SECURE_NO_WARNINGS
// match: ee3670 _vp9_idct16x16_add
// match: ee36c0 _vp9_idct32x32_add
// match: ee3740 _vp9_idct8x8_add
// match: ee38a0 _vp9_iht16x16_add
// match: ee3ac0 _vp9_iht4x4_add
// match: ee3dd0 _vp9_iht8x8_add
// match: ee3e30 _vp9_iwht4x4_add
#include "../../../../tools/third_party/libvpx-1.8.0/vp9/common/vp9_idct.c"
