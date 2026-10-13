// The element and storage of the packet field vectors, named from their measured layout. The element's
// destructor occupies slot 3; the other slots and its fields still need their own reconstruction.
#pragma once
#include "types.h"
#include <new>
#include "RString.h"

#pragma pack(push, 1)
template <unsigned Size> struct PacketVectorElement {
    virtual void Slot0();
    virtual void Slot1();
    virtual void Slot2();
    virtual ~PacketVectorElement();
    u8 fields[Size - 4];
};
#pragma pack(pop)

template <unsigned Size> struct PacketVectorStorage {
    PacketVectorElement<Size>* data = nullptr;
    u32 count = 0;
    u32 capacity = 0;
    constexpr PacketVectorStorage() {}
    PacketVectorStorage& operator=(const PacketVectorStorage& other);
    ~PacketVectorStorage() {
        for (auto p = data, end = data + count; p < end; ++p) p->~PacketVectorElement<Size>();
        if ((int)capacity >= 0) ::operator delete(data);
    }
};

// Some fields call an out-of-line destructor. Its body is supplied by VectorDestructors.cpp;
// keeping it outside the readers also preserves the client's short atexit callback.
template <unsigned Size> struct PacketVectorExternal {
    PacketVectorElement<Size>* data = nullptr;
    u32 count = 0;
    u32 capacity = 0;
    constexpr PacketVectorExternal() {}
    PacketVectorExternal& operator=(const PacketVectorExternal& other);
    ~PacketVectorExternal();
};

// A vector of trivially destructible values has the same ownership flag, but only releases its storage.
struct PacketTrivialVectorStorage {
    void* data = nullptr;
    u32 count = 0;
    u32 capacity = 0;
    ~PacketTrivialVectorStorage() { if ((int)capacity >= 0) ::operator delete(data); }
};
