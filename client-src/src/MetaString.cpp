// Native owned-string construction; default empty strings retain the shared pointer.
// match: 9b78e0 ??0MetaString@@QAE@PBD@Z
// match: 9b7840 ??0MetaString@@QAE@ABU0@@Z
#include "Meta.h"

void* Pool_Alloc(u32 size); // rva 0x9d4570

MetaString::MetaString(const char* text) : RString(UninitializedTag{})
{
    // Capturing the source pointer by value gives the native constructor's
    // register allocation while retaining the actual allocation and copy loops.
    auto init = [self=this, text]() mutable {
        const char* end = text;
        while (*end) ++end;
        self->size = (u32)(end - text);
        u32 reserved = (self->size + 1) & ~1u;
        char* output = (char*)Pool_Alloc(reserved + 1);
        self->capacity = reserved | 1u;
        self->data = output;
        while (text < end) *output++ = *text++;
        *output = 0;
    };
    init();
}

MetaString::MetaString(const MetaString& other) : RString(UninitializedTag{})
{
    const u32 length = other.size;
    size = length;
    u32 reserved = (length + 1) & ~1u;
    char* output = (char*)Pool_Alloc(reserved + 1);
    capacity = reserved | 1u;
    data = output;
    const char* source = other.data;
    const char* end = source + length;
    while (source < end) *output++ = *source++;
    *output = 0;
}
