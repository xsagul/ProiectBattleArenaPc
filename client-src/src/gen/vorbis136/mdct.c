// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): mdct.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e7b9f0 _mdct_backward
// match: e7bd50 _mdct_bitreverse
// match: e7bf00 _mdct_butterflies
// match: e7c690 _mdct_butterfly_first
// match: e7c840 _mdct_clear
// match: e7c880 _mdct_forward
// match: e7cae0 _mdct_init
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/mdct.c"
