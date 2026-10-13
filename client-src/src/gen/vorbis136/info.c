// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): info.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e72b90 __vorbis_pack_books
// match: e72dd0 __vorbis_pack_comment
// match: e72ee0 _vorbis_analysis_headerout
// match: e73270 _vorbis_comment_clear
// match: e732f0 _vorbis_info_clear
// match: e73470 _vorbis_info_init
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/info.c"
