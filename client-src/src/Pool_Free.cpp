// rva 0x9d42e0  Pool_Free: gives a block back. A block that lies inside one of the pool's chunks goes to the bucket of
// its page (under the pool's lock when the pool has one); any other block goes to the C runtime's free.
// Layout offsets are the ones the code uses; the names are ours.
// match: 9d42e0 Pool_Free
#include "types.h"
#include <initializer_list>
#include <stdlib.h>

extern "C" unsigned char _BitScanReverse(unsigned long* index, unsigned long mask);
#pragma intrinsic(_BitScanReverse)

struct CRITICAL_SECTION;
extern "C" __declspec(dllimport) void __stdcall EnterCriticalSection(CRITICAL_SECTION*);
extern "C" __declspec(dllimport) void __stdcall LeaveCriticalSection(CRITICAL_SECTION*);


struct PoolChunk
{
    u32 unknown00;
    PoolChunk* next;        // +0x04
    u8 unknown08[0x10];
    u8 pages[1];            // +0x18
};

struct PoolPage
{
    u8 unknown00[0x14];
    u32 blockSize;          // +0x14
};

struct PoolBucket           // 0x2c bytes
{
    u8 unknown00[0x2c];
    void Free(void* block, PoolPage* page);     // rva 0x9c89f0
};

struct PoolLayout
{
    u32 unknown00;
    PoolChunk* chunks04;    // +0x04
    u32 unknown08;
    PoolChunk* chunks0c;    // +0x0c
    u8 unknown10[8];
    u32 pagesPerChunk;      // +0x18
    u32 pageSize;           // +0x1c

    bool Holds(PoolChunk* chunk, void* block)
    {
        u8* pages = chunk->pages;
        return block >= pages && block < pages + pageSize * pagesPerChunk;
    }

    PoolChunk* Find(void* block)
    {
        for (PoolChunk* chunk : { chunks04, chunks0c })
        {
            for (; chunk; chunk = chunk->next)
            {
                if (Holds(chunk, block))
                    return chunk;
            }
        }
        return 0;
    }
};

struct Pool
{
    PoolLayout* layout;             // +0x00
    PoolBucket* buckets;            // +0x04
    u8 unknown08[0x10];
    u32 flags;                      // +0x18  0x1000: the pool has a lock
    CRITICAL_SECTION* LockStorage() { return (CRITICAL_SECTION*)(this + 1); }   // +0x1c

    // The layout pointer read from memory again. After the search the client's code reloads it instead of reusing the
    // value the search loaded; the same compiler does that only when this second read is one it may not merge with
    // the first (a volatile read here; what Riot wrote, a volatile or an atomic load, is not known). With both reads
    // plain it reuses the register (219 bytes); with both volatile two bytes differ.
    PoolLayout* LayoutNow() { return *(PoolLayout* volatile*)&layout; }
};

struct PoolOwner
{
    u8 unknown00[0xc];
    Pool* pool;             // +0x0c
};

extern PoolOwner* g_poolOwner;      // rva 0x3195f4c

struct PoolLock
{
    CRITICAL_SECTION* section;
    explicit PoolLock(CRITICAL_SECTION* s) : section(s) { if (section) EnterCriticalSection(section); }
    ~PoolLock() { if (section) LeaveCriticalSection(section); }
};

void Pool_Free(void* block)
{
    if (!block)
        return;
    Pool* pool = g_poolOwner->pool;
    PoolLayout* layout = pool->layout;
    if (layout->Find(block))
    {
        PoolPage* page = *(PoolPage**)((u32)block & -(int)pool->LayoutNow()->pageSize);
        unsigned long top;
        _BitScanReverse(&top, page->blockSize);
        PoolBucket* bucket = &pool->buckets[top - 2];
        PoolLock lock((pool->flags & 0x1000) ? pool->LockStorage() : 0);
        bucket->Free(block, page);
        return;
    }
    free(block);
}
