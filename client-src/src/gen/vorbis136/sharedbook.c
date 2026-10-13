// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): sharedbook.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e76b00 __book_maptype1_quantvals
// match: e76bf0 __book_unquantize
// match: e76eb0 __make_words
// match: e770b0 _ov_ilog
// match: e770d0 _sort32a
// match: e77100 _vorbis_book_clear
// match: e776c0 _vorbis_book_init_encode
// match: e777f0 _vorbis_staticbook_destroy
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/sharedbook.c"
