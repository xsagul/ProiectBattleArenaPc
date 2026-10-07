// rva 0x2ee3a0  LnpBuffer::Reserve: makes the buffer hold at least newCapacity bytes and belong to this owner alone.
// Nothing happens when it is big enough and not shared; otherwise a new block is taken, the bytes in use are copied
// and the old block is released.
// match: 2ee3a0 Reserve@LnpBuffer
#include <string.h>
#include "LnpBuffer.h"

void LnpBuffer::Reserve(u16 newCapacity)
{
    if (newCapacity <= capacity && (!data || Count(data) <= 1))
        return;
    u8* old = data;
    u32* block = (u32*)Crt_Alloc(newCapacity + 4);
    *block = 1;
    data = (u8*)(block + 1);
    capacity = newCapacity;
    if (old)
    {
        memcpy(data, old, size);
        Release(old);
    }
}
