// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): codebook.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e77840 _decode_packed_entry_number
// match: e779d0 _vorbis_book_decode
// match: e77a00 _vorbis_book_decodev_add
// match: e77ca0 _vorbis_book_decodev_set
// match: e77f20 _vorbis_book_decodevs_add
// match: e781a0 _vorbis_book_decodevv_add
// match: e783d0 _vorbis_book_encode
// match: e78420 _vorbis_staticbook_pack
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/codebook.c"
