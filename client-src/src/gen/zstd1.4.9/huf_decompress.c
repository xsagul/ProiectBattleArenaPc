// zstd 1.4.9 (facebook/zstd), compiled by Riot as C: huf_decompress.c, the functions of it that are in the client (tools/match_objs.py).
// match: c8b640 _BIT_endOfDStream -O2
// match: c8b800 _HUF_decompress1X1_usingDTable_internal_body -O2
// match: c8ba50 _HUF_decompress1X2_usingDTable_internal_body -O2
// match: c8bd80 _HUF_decompress4X1_usingDTable_internal -O2
// match: c8cb40 _HUF_decompress4X2_DCtx_wksp_bmi2 -O2
// match: c8cba0 _HUF_decompress4X2_usingDTable_internal -O2
// match: c8dbc0 _HUF_decompress4X_hufOnly_wksp_bmi2 -O2
// match: c8dc40 _HUF_fillDTableX2 -O2
// match: c8dec0 _HUF_readDTableX1_wksp_bmi2 -O2
// match: c8e2d0 _HUF_readDTableX2_wksp -O2
// match: c8e5e0 _HUF_selectDecoder -O2
#include "../../../../tools/third_party/zstd-1.4.9/lib/decompress/huf_decompress.c"
