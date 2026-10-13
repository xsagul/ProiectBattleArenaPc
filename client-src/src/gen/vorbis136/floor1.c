// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): floor1.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e801d0 _floor1_free_info
// match: e80200 _floor1_free_look
// match: e80230 _floor1_pack
// match: e80d10 _floor1_inverse1
// match: e81280 _accumulate_fit
// match: e816f0 _floor1_encode
// match: e81e80 _floor1_fit
// match: e82530 _floor1_interpolate_fit
// match: e82760 _icomp
// match: e82780 _inspect_error
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/floor1.c"
