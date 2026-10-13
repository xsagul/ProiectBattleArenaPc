// match: 9be7d0 ??4RString@@
#include "RString.h"

void Pool_Free(void* p); // rva 0x9d42e0
void StringPool_Init(); // rva 0x9d43c0
extern bool g_string_pool_ready; // va 0x3715e75

// The allocator remains an external service here; its implementation and state still need reconstruction.
struct StringPool { void* Allocate(u32 bytes); }; // rva 0x9bd6e0
extern StringPool* g_string_pool; // va 0x3715f4c

void RString::operator=(const RString& other)
{
    u32 length = other.size;
    if (length > (capacity & ~1u)) {
        if (capacity & 1)
            Pool_Free((void*)data);
        u32 allocated = (length + 1) & ~1u;
        if (!g_string_pool_ready)
            StringPool_Init();
        data = (const char*)g_string_pool->Allocate(allocated + 1);
        capacity = allocated | 1;
    } else if (data == "") {
        return;
    }
    const char* p = other.data;
    const char* end = p + length;
    char* out = (char*)data;
    while (p < end)
        *out++ = *p++;
    *out = 0;
    size = length;
}
