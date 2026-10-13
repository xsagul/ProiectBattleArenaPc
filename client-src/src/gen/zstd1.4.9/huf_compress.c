// zstd 1.4.9 (facebook/zstd), compiled by Riot as C: huf_compress.c, the functions of it that are in the client (tools/match_objs.py).
// match: c53230 _HUF_buildCTable_wksp -O2
// match: c534c0 _HUF_buildTree -O2
// match: c53640 _HUF_compress1X_repeat -O2
// match: c536a0 _HUF_compress1X_usingCTable_internal_body -O2
// match: c538f0 _HUF_compress4X_repeat -O2
// match: c53950 _HUF_compress4X_usingCTable_internal -O2
// match: c53a50 _HUF_compressCTable_internal -O2
// match: c53ab0 _HUF_compress_internal -O2
// match: c53da0 _HUF_estimateCompressedSize -O2
// match: c53e20 _HUF_getNbBits -O2
// match: c53e50 _HUF_setMaxHeight -O2
// match: c54080 _HUF_validateCTable -O2
// match: c540d0 _HUF_writeCTable -O2
#include "../../../../tools/third_party/zstd-1.4.9/lib/compress/huf_compress.c"
