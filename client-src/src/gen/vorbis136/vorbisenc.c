// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): vorbisenc.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e74b80 _get_setup_template
// match: e74d00 _vorbis_encode_compand_setup
// match: e74dd0 _vorbis_encode_global_stereo
// match: e75110 _vorbis_encode_init_vbr
// match: e751f0 _vorbis_encode_noisebias_setup
// match: e75330 _vorbis_encode_psyset_setup
// match: e753d0 _vorbis_encode_residue_setup
// match: e758a0 _vorbis_encode_setup_init
// match: e76900 _vorbis_encode_setup_setting
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/vorbisenc.c"
