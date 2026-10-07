// RString's out-of-line pieces and the string length helper.
// match: 9bab90 ??1RString@@QAE@XZ
// match: 9daf30 ?StrLen@@YAIPBD@Z
#include "RString.h"

void Pool_Free(void* p);    // rva 0x9d42e0

RString::~RString()
{
    if (capacity & 1)
        Pool_Free((void*)data);
}

u32 StrLen(const char* s)
{
    const char* p = s;
    while (*p)
        ++p;
    return (u32)(p - s);
}
