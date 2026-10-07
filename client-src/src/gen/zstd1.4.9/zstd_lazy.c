// zstd 1.4.9 (facebook/zstd), compiled by Riot as C: zstd_lazy.c, the functions of it that are in the client (tools/match_objs.py).
// match: c61240 _ZSTD_BtFindBestMatch_dictMatchState_selectMLS -O2
// match: c61310 _ZSTD_BtFindBestMatch_extDict_selectMLS -O2
// match: c613e0 _ZSTD_BtFindBestMatch_selectMLS -O2
// match: c614b0 _ZSTD_DUBT_findBestMatch -O2
// match: c61a10 _ZSTD_DUBT_findBetterDictMatch -O2
// match: c61ca0 _ZSTD_HcFindBestMatch_dedicatedDictSearch_selectMLS -O2
// match: c62990 _ZSTD_HcFindBestMatch_dictMatchState_selectMLS -O2
// match: c63490 _ZSTD_HcFindBestMatch_extDict_selectMLS -O2
// match: c63d00 _ZSTD_HcFindBestMatch_selectMLS -O2
// match: c65be0 _ZSTD_compressBlock_greedy -O2
// match: c66890 _ZSTD_compressBlock_greedy_extDict -O2
// match: c66d00 _ZSTD_compressBlock_lazy -O2
// match: c69e50 _ZSTD_compressBlock_lazy_extDict -O2
// match: c6a4a0 _ZSTD_insertDUBT1 -O2
// match: c6a740 _ZSTD_updateDUBT -O2
#include "../../../../tools/third_party/zstd-1.4.9/lib/compress/zstd_lazy.c"
