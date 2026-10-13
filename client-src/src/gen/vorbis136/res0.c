// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): res0.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e829a0 _res0_free_info
// match: e829d0 _res0_free_look
// match: e82a50 _res0_pack
// match: e82b50 _res0_unpack
// match: e82d00 _res0_look
// match: e82f70 _res1_forward
// match: e82fd0 _res1_class
// match: e832d0 _res2_class
// match: e834e0 _res2_forward
// match: e835b0 _res2_inverse
// match: e83750 __01forward
// match: e83a50 __01inverse
// match: e83c80 __encodepart
// match: e83ce0 _local_book_besterror
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/res0.c"
