// Hashes of names the client computes at run time (names ours). All work on the lower-case letters (A-Z only):
//   Fnv1aLower  FNV-1a with a given start (0x811c9dc5 is FNV's), the .bin hash   rva 0x98a860
//   Fnv1Lower   FNV-1 (multiply, then xor) from 0x811c9dc5                         rva 0x98a8b0
//   ElfHashLower  the ELF (PJW) hash                                                rva 0x971a50
// (ElfKey.h has the ELF hash that lower-cases through the C runtime, rva 0x120eb0.)
#pragma once
#include "types.h"

inline char LowerAscii(char c)
{
    return (unsigned char)(c - 'A') <= 25 ? c + 32 : c;
}

inline u32 Fnv1aLower(const char* s, unsigned int n, u32 h)
{
    while (n--)
        h = (h ^ LowerAscii(*s++)) * 0x1000193;
    return h;
}

u32 Fnv1aLower(const char* s, u32 h = 0x811c9dc5);
u32 Fnv1Lower(const char* s);
u32 ElfHashLower(const char* s);
