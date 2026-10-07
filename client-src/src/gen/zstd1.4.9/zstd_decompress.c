// zstd 1.4.9 (facebook/zstd), compiled by Riot as C: zstd_decompress.c, the functions of it that are in the client (tools/match_objs.py).
// match: c4d5c0 _ZSTD_cpuid -O2
// match: c4f400 _ZSTD_DCtx_selectFrameDDict -O2
// match: c4f4d0 _ZSTD_checkOutBuffer -O2
// match: c4f540 _ZSTD_createDStream -O2
// match: c4f570 _ZSTD_createDCtx_advanced -O2
// match: c4f5e0 _ZSTD_decodeFrameHeader -O2
// match: c4f6b0 _ZSTD_decompressBegin -O2
// match: c4f7a0 _ZSTD_decompressBegin_usingDDict -O2
// match: c4f8d0 _ZSTD_decompressContinue -O2
// match: c4fe10 _ZSTD_decompressContinueStream -O2
// match: c4fed0 _ZSTD_decompressDCtx -O2
// match: c4ff00 _ZSTD_decompressFrame -O2
// match: c501f0 _ZSTD_decompressMultiFrame -O2
// match: c50440 _ZSTD_decompressStream -O2
// match: c50e30 _ZSTD_findFrameSizeInfo -O2
// match: c50fb0 _ZSTD_frameHeaderSize_internal -O2
// match: c51010 _ZSTD_freeDCtx -O2
// match: c51130 _ZSTD_getDDict -O2
// match: c51190 _ZSTD_getDictID_fromDict -O2
// match: c511b0 _ZSTD_getFrameHeader_advanced -O2
// match: c51420 _ZSTD_initDCtx_internal -O2
// match: c51570 _ZSTD_loadDEntropy -O2
#include "../../../../tools/third_party/zstd-1.4.9/lib/decompress/zstd_decompress.c"
