// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): bitrate.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e744a0 _vorbis_bitrate_addblock
// match: e74930 _vorbis_bitrate_clear
// match: e74950 _vorbis_bitrate_flushpacket
// match: e749f0 _vorbis_bitrate_init
// match: e74b50 _vorbis_bitrate_managed
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/bitrate.c"
