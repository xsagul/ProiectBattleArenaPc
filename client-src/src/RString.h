// A string type used for many global names (the type name is ours). A string made from a literal points at the
// literal; bit 0 of the third word says the characters are the string's own (given back to the pool when it dies),
// so a literal's length is rounded up to an even number there (rva 0x7a320 and 382 more initializers like it).
#pragma once
#include "types.h"

u32 StrLen(const char* s);   // rva 0x9daf30

struct RString
{
    const char* data;
    u32 size;
    u32 capacity;           // bit 0: data is owned

    RString(const char* s)
    {
        u32 n = StrLen(s);
        data = s;
        size = n;
        if (n & 1)
            ++n;
        capacity = n;
    }
    ~RString();             // rva 0x9bab90, not inline: every global's atexit callback jumps to it
};
