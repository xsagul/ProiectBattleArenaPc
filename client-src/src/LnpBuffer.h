// The byte buffer the transport builds datagrams in (rva 0x2ee3a0 grows it): a shared block with its reference count
// in the four bytes before the data. The names are ours.
#pragma once
#include <atomic>
#include <stdlib.h>
#include <string.h>
#include "types.h"

void* Crt_Alloc(u32 size);      // rva 0xf6a27b

struct LnpBuffer
{
    u8* data;       // +0x00  the reference count is at data - 4
    u16 capacity;   // +0x04
    u16 size;       // +0x06
    u16 position;   // +0x08  how far it has been read

    LnpBuffer() : data(nullptr), capacity(0), size(0), position(0) {}

    // A copy shares the block and counts itself in; the last owner to go frees it.
    LnpBuffer(const LnpBuffer& other)
        : data(other.data), capacity(other.capacity), size(other.size), position(other.position)
    {
        if (data)
            Count(data).fetch_add(1);
    }

    // Moving takes the other buffer's block and leaves that one empty.
    LnpBuffer& operator=(LnpBuffer&& other)
    {
        Drop();
        data = other.data;
        capacity = other.capacity;
        size = other.size;
        position = other.position;
        other.data = nullptr;
        other.capacity = 0;
        other.size = 0;
        other.position = 0;
        return *this;
    }

    ~LnpBuffer()
    {
        Drop();
    }

    // Gives up this owner's share of the block. The count's address is formed by stepping a tested pointer back, not
    // as "data - 4": only this spelling gives the client's "sub ecx, 4" in the move assignment and in the standard
    // library's destroy loop (written "data - 4", the compiler adds -4 or uses lea).
    void Drop()
    {
        if (std::atomic<u32>* count = (std::atomic<u32>*)data)
        {
            --count;
            if (count->fetch_sub(1) == 1)
                free(count);
        }
    }

    // One owner less; the last one frees the block.
    static void Release(u8* data)
    {
        if (Count(data).fetch_sub(1) == 1)
            free(data - 4);
    }

    static std::atomic<u32>& Count(u8* data) { return *(std::atomic<u32>*)(data - 4); }

    void Reserve(u16 newCapacity);

    // Always answers true (the client has it as a function of its own too, rva 0x2d2d60).
    bool Append(const void* bytes, u16 count)
    {
        if (count)
        {
            Reserve(size + count);
            memcpy(data + size, bytes, count);
            size += count;
        }
        return true;
    }

    bool ReadBuffer(LnpBuffer* to, u16 count);  // rva 0x2ed2f0

    template <class T>
    bool Read(T& value)
    {
        if (position + sizeof(T) <= size)
        {
            value = *(T*)(data + position);
            position += sizeof(T);
            return true;
        }
        return false;
    }

    void AppendByte(u8 value)
    {
        Reserve(size + 1);
        data[size] = value;
        size += 1;
    }

    // One value at the end, as the message writer (rva 0x2efcc0) does it.
    template <class T>
    void Put(const T& value)
    {
        Reserve(size + sizeof(T));
        *(T*)(data + size) = value;
        size += sizeof(T);
    }

    template <class T>
    void Append(const T& value)
    {
        Append(&value, sizeof(T));
    }
};
