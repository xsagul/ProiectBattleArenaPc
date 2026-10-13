// RString's out-of-line pieces and the string length helper.
// match: 9bab90 ??1RString@@QAE@XZ
// match: 9daf30 ?StrLen@@YAIPBD@Z
// match: 9c01f0 ?Clear@RString@@
// match: 9da2a0 ?Resize@RString@@
#include "RString.h"

void Pool_Free(void* p);    // rva 0x9d42e0

RString::~RString()
{
    if (capacity & 1)
        Pool_Free((void*)data);
}

void RString::Clear()
{
    if (data != "")
    {
        ((char*)data)[0] = 0;
        size = 0;
    }
}

void RString::Resize(u32 length)
{
    if (length > (capacity & ~1u))
        Reserve(length);
    if (data != "")
        ((char*)data)[length] = 0;
    size = length;
}

u32 StrLen(const char* s)
{
    const char* p = s;
    while (*p)
        ++p;
    return (u32)(p - s);
}
