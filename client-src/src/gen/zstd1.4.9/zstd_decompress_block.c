// zstd 1.4.9 (facebook/zstd), compiled by Riot as C: zstd_decompress_block.c, the functions of it that are in the client (tools/match_objs.py).
// match: c8b660 _BIT_initDStream -O2
// match: c8e790 _BIT_readBitsFast -O2
// match: c8e7c0 _BIT_reloadDStream -O2
// match: c8e850 _ZSTD_buildFSETable -O2
// match: c8e880 _ZSTD_buildFSETable_body_default -O2
// match: c8eac0 _ZSTD_buildSeqTable -O2
// match: c8ec80 _ZSTD_checkContinuity -O2
// match: c8ecc0 _ZSTD_decodeLiteralsBlock -O2
// match: c8efe0 _ZSTD_decodeSeqHeaders -O2
// match: c8f1a0 _ZSTD_decompressBlock_internal -O2
// match: c8f310 _ZSTD_decompressSequencesLong_default -O2
// match: c903f0 _ZSTD_decompressSequences_default -O2
// match: c90ce0 _ZSTD_execSequenceEnd -O2
// match: c90de0 _ZSTD_getcBlockSize -O2
// match: c90e40 _ZSTD_safecopy -O2
#include "../../../../tools/third_party/zstd-1.4.9/lib/decompress/zstd_decompress_block.c"
