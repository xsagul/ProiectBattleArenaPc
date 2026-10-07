// The ELF (PJW) hash of a name's lower-case letters.
// match: 120eb0 ?HashElf@@YAIPBD@Z
#include "ElfKey.h"
#include <ctype.h>

u32 HashElf(const char* s)
{
    u32 h = 0;
    for (; *s; ++s)
    {
        h = (h << 4) + tolower(*s);
        u32 g = h & 0xf0000000;
        if (g)
            h ^= (g >> 24) ^ g;
    }
    return h;
}
