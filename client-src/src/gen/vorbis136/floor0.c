// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): floor0.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e7fc80 _floor0_free_info
// match: e7fcb0 _floor0_free_look
// match: e7fdf0 _floor0_look
// match: e7fe30 _floor0_inverse1
// match: e7ff70 _floor0_inverse2
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/floor0.c"
