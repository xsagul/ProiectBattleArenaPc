// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): envelope.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e7d3f0 __ve_envelope_clear
// match: e7d680 __ve_envelope_mark
// match: e7d960 __ve_envelope_shift
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/envelope.c"
