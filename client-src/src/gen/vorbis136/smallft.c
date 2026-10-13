// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): smallft.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e7d9c0 _dradf2
// match: e7dbf0 _dradf4
// match: e7ef30 _drft_clear
// match: e7ef70 _drft_forward
// match: e7efa0 _drft_init
// match: e7eff0 _drftf1
// match: e7f1f0 _drfti1
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/smallft.c"
