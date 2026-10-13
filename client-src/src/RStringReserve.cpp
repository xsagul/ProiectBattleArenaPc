// Kept in a separate translation unit: Resize calls Reserve rather than inlining its allocation and copy.
// match: 9cd2a0 ?Reserve@RString@@
#include "RString.h"

void* Pool_Alloc(u32 bytes); // rva 0x9d4570
void Pool_Free(void* p);    // rva 0x9d42e0

void RString::Reserve(u32 length)
{
    u32 available = capacity & ~1u;
    u32 proposal = available + available / 2;
    u32 grown = length > proposal ? length : proposal;
    grown = (grown + 1) & ~1u;
    char* next = (char*)Pool_Alloc(grown + 1);
    const char* p = data;
    const char* end = data + size;
    char* out = next;
    while (p < end)
        *out++ = *p++;
    *out = 0;
    if (capacity & 1)
        Pool_Free((void*)data);
    data = next;
    capacity = grown | 1;
}
