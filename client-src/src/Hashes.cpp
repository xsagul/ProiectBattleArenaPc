// The run-time name hashes (Hashes.h).
// match: 98a860 ?Fnv1aLower@@YAIPBDI@Z
// match: 98a8b0 ?Fnv1Lower@@YAIPBD@Z
// match: 971a50 ?ElfHashLower@@YAIPBD@Z
#include "Hashes.h"
#include <string.h>

u32 Fnv1aLower(const char* s, u32 h)
{
    return Fnv1aLower(s, strlen(s), h);
}

u32 Fnv1Lower(const char* s)
{
    u32 h = 0x811c9dc5;
    for (; *s; ++s)
        h = h * 0x1000193 ^ LowerAscii(*s);
    return h;
}

u32 ElfHashLower(const char* s)
{
    u32 h = 0;
    for (; *s; ++s)
    {
        h = (h << 4) + LowerAscii(*s);
        u32 g = h & 0xf0000000;
        if (g)
            h ^= (g >> 24) ^ g;
    }
    return h;
}
