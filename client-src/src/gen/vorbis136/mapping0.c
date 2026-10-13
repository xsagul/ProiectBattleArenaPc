// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): mapping0.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e84110 _mapping0_free_info
// match: e84140 _mapping0_pack
// match: e842a0 _mapping0_unpack
// match: e84f10 _mapping0_inverse
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/mapping0.c"
