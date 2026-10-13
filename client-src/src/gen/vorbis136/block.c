// libvorbis 1.3.6 (frame pointers kept), prebuilt for the client with Visual Studio 2017 (ours: MSVC 14.16.27048): block.c, the functions of it that are in the client (tools/match_objs.py).
// compiler: msvc-14.16.27048
// flags: -O2 -Oy- -Itools/third_party/libvorbis-1.3.6/include -Itools/third_party/libvorbis-1.3.6/lib -Itools/third_party/libogg-1.3.3/include -DNDEBUG -DWIN32
// match: e734a0 __preextrapolate_helper
// match: e735b0 __vds_shared_init
// match: e739d0 __vorbis_block_alloc
// match: e73a30 __vorbis_block_ripcord
// match: e73aa0 _vorbis_analysis_blockout
// match: e73d90 _vorbis_analysis_buffer
// match: e73e50 _vorbis_analysis_init
// match: e73ec0 _vorbis_analysis_wrote
// match: e740b0 _vorbis_block_clear
// match: e74130 _vorbis_block_init
// match: e741a0 _vorbis_dsp_clear
#include "../../../../tools/third_party/libvorbis-1.3.6/lib/block.c"
