#include "C:/Users/Sorin/Desktop/ProiectBattleArenaPc/client-src/src/types.h"
void* Pool_Alloc(u32);
struct OwnedSeed {
    const char* data;
    u32 size;
    u32 capacity;
    OwnedSeed(const char* text);
};
OwnedSeed::OwnedSeed(const char* text) {
    const char* end = text;
    while (*end) ++end;
    size = (u32)(end - text);
    u32 reserved = (size + 1) & ~1u;
    char* output = (char*)Pool_Alloc(reserved + 1);
    capacity = reserved | 1u;
    data = output;
    while (text < end) *output++ = *text++;
    *output = 0;
}
