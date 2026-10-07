// The transport's compression step ([Network] EnableCompression / CompressionLevel of game.cfg). Two functions, each
// given a datagram and answering true when it left it as it was:
//   rva 0x2e2a70  compresses the payload of an outgoing datagram when compression is on, the payload is at least the
//                 configured size and the result is smaller, and marks the datagram as compressed;
//   rva 0x2e2020  decompresses the payload of an incoming datagram marked as compressed.
// The work is done by the zstd library inside the client (rva 0xc4ccc0, 0xc4fed0, 0xc4c6c0: argument lists of
// ZSTD_compressCCtx, ZSTD_decompressDCtx, ZSTD_isError; the names are our reading, the library is not rebuilt).
// match: 2e2a70 ?Compress@LnpCompression
// match: 2e2020 ?Decompress@LnpCompression
#include "LnpDatagram.h"

extern "C" u32 ZSTD_compressCCtx(void* context, void* to, u32 capacity, const void* from, u32 size, int level);
extern "C" u32 ZSTD_decompressDCtx(void* context, void* to, u32 capacity, const void* from, u32 size);
extern "C" u32 ZSTD_isError(u32 code);

struct LnpCompression
{
    u8 unknown000[0x14];
    u8 buffer[0x44c];           // +0x014
    void* compressContext;      // +0x460
    void* decompressContext;    // +0x464
    bool enabled;               // +0x468
    u32 smallestSize;           // +0x46c
    int level;                  // +0x470

    bool Compress(LnpDatagram& datagram);
    bool Decompress(LnpDatagram& datagram);
};

bool LnpCompression::Compress(LnpDatagram& datagram)
{
    if (enabled && !datagram.flag40 && datagram.unknown48 <= 0 && datagram.number > 0)
    {
        u32 size = datagram.payload.size;
        if (size != 0 && size >= smallestSize)
        {
            u32 packed = ZSTD_compressCCtx(compressContext, buffer, sizeof(buffer), datagram.payload.data, size, level);
            if (!ZSTD_isError(packed) && packed < size)
            {
                datagram.payload.size = 0;
                datagram.payload.position = 0;
                datagram.payload.Append(buffer, packed);
                datagram.flag40 = 1;
                return false;
            }
        }
    }
    return true;
}

bool LnpCompression::Decompress(LnpDatagram& datagram)
{
    if (datagram.number > 0)
    {
        u32 size = datagram.payload.size;
        if (size != 0 && datagram.flag40)
        {
            u32 unpacked = ZSTD_decompressDCtx(decompressContext, buffer, sizeof(buffer), datagram.payload.data, size);
            if (!ZSTD_isError(unpacked))
            {
                datagram.payload.size = 0;
                datagram.payload.position = 0;
                datagram.payload.Append(buffer, unpacked);
                return false;
            }
        }
    }
    return true;
}
