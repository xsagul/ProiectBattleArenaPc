// match: 91cae0 ?GetBits_91cae0@
#include "PacketBits.h"

u8 GetBits_91cae0(const u8* data, u8 first, u8 count) {
    u8 byte = first >> 3;
    u8 bit = first & 7;
    u8 mask = (u8)((1 << count) - 1);
    u8 result = (data[byte] & (u8)(mask << bit)) >> bit;
    if (bit + count > 8) {
        ++byte;
        mask >>= 8 - bit;
        result |= (data[byte] & mask) << (8 - bit);
    }
    return result;
}
